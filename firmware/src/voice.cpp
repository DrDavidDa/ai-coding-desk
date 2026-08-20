#include "voice.h"
#include "board.h"
#include "config.h"
#include "status.h"
#include "serial_cmd.h"
#include "hid_keys.h"
#include "ble_audio.h"
#include "beep.h"
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <driver/i2s.h>
#include <esp_heap_caps.h>
#include <cstring>

#define ES7210_ADDR 0x40
#define VOICE_SR 16000
#define VOICE_MAX_SEC 12
#define VOICE_MAX_BYTES (VOICE_SR * 2 * VOICE_MAX_SEC)
#define VOICE_MEAN_ABS_MIN 80
#define VOICE_SKIP_BLOCKS 3

static uint8_t *sPcm = nullptr;
static size_t sBytes = 0;
static size_t sSendBytes = 0;
static bool sRec = false;
static bool sI2s = false;
static volatile bool sBusy = false;
static int sSkipBlocks = 0;
static VoiceSource sSrc = VOICE_SRC_NONE;
static uint32_t sRecT0 = 0;
static size_t sSilentBytes = 0;
static bool sHeardSpeech = false;

#define VOICE_SILENCE_BYTES (VOICE_SR * 2 * 12 / 10)  /* 1.2 s */
#define VOICE_MIN_SPEECH_BYTES (VOICE_SR * 2 * 8 / 10) /* 0.8 s */

static void es7210_write(uint8_t addr, uint8_t reg, uint8_t val) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write(val);
    Wire.endTransmission();
}

static uint8_t sEsAddr = ES7210_ADDR;
static bool sLoggedSlots = false;
static int sMixA = 0;
static int sMixB = -1;

static uint8_t es7210_read(uint8_t addr, uint8_t reg) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return 0xFF;
    if (Wire.requestFrom((int)addr, 1) < 1) return 0xFF;
    return (uint8_t)Wire.read();
}

static void es7210_probe() {
    Wire.beginTransmission(0x40);
    if (Wire.endTransmission() == 0) sEsAddr = 0x40;
    else {
        Wire.beginTransmission(0x41);
        if (Wire.endTransmission() == 0) sEsAddr = 0x41;
    }
    Serial.printf("[VOICE] es7210 addr 0x%02X id=0x%02X\n", sEsAddr, es7210_read(sEsAddr, 0x3D));
}

static void es7210_init() {
    es7210_probe();
    // Official esp-bsp ES7210: 16 kHz, MCLK×256, I2S 16-bit, 1xFS TDM (4 slots).
    // 0x02/0x04/0x05 are the 16 kHz @ 4.096 MHz MCLK coefficients.
    static const uint8_t seq[][2] = {
        {0x00, 0xFF}, {0x00, 0x32},
        {0x09, 0x30}, {0x0A, 0x30},
        {0x23, 0x2A}, {0x22, 0x0A}, {0x21, 0x2A}, {0x20, 0x0A},
        {0x11, 0x60}, {0x12, 0x02},
        {0x07, 0x20}, {0x02, 0xC1}, {0x04, 0x01}, {0x05, 0x00},
        {0x40, 0xC3}, {0x41, 0x70}, {0x42, 0x70},
        {0x43, 0x1E}, {0x44, 0x1E}, {0x45, 0x1E}, {0x46, 0x1E},
        {0x47, 0x08}, {0x48, 0x08}, {0x49, 0x08}, {0x4A, 0x08},
        {0x06, 0x04}, {0x4B, 0x0F}, {0x4C, 0x0F},
        {0x00, 0x71}, {0x00, 0x41},
    };
    for (size_t i = 0; i < sizeof(seq) / sizeof(seq[0]); i++) {
        es7210_write(sEsAddr, seq[i][0], seq[i][1]);
        delay(2);
    }
    Serial.printf("[VOICE] es7210 0x11=0x%02X 0x12=0x%02X 0x02=0x%02X\n",
                  es7210_read(sEsAddr, 0x11), es7210_read(sEsAddr, 0x12), es7210_read(sEsAddr, 0x02));
}

static void i2s_start() {
    if (sI2s) return;
    i2s_config_t cfg = {};
    cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
    cfg.sample_rate = VOICE_SR;
    cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
    cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
    cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    cfg.dma_buf_count = 8;
    cfg.dma_buf_len = 512;
    cfg.use_apll = false;
    cfg.tx_desc_auto_clear = false;
    cfg.fixed_mclk = 256 * VOICE_SR;
    i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr);
    i2s_pin_config_t pins = {};
    pins.mck_io_num = SND_I2S_MCLK;
    pins.bck_io_num = SND_I2S_BCLK;
    pins.ws_io_num = SND_I2S_WS;
    pins.data_out_num = I2S_PIN_NO_CHANGE;
    pins.data_in_num = SND_I2S_DIN;
    i2s_set_pin(I2S_NUM_0, &pins);
    i2s_zero_dma_buffer(I2S_NUM_0);
    sI2s = true;
}

static void i2s_stop() {
    if (!sI2s) return;
    i2s_driver_uninstall(I2S_NUM_0);
    sI2s = false;
}

static void write_wav_header(uint8_t *h, uint32_t dataBytes) {
    uint32_t sr = VOICE_SR;
    uint16_t ch = 1, bps = 16;
    uint32_t byteRate = sr * ch * bps / 8;
    memcpy(h, "RIFF", 4);
    uint32_t chunk = 36 + dataBytes;
    memcpy(h + 4, &chunk, 4);
    memcpy(h + 8, "WAVEfmt ", 8);
    uint32_t fmtLen = 16;
    memcpy(h + 16, &fmtLen, 4);
    uint16_t audioFmt = 1;
    memcpy(h + 20, &audioFmt, 2);
    memcpy(h + 22, &ch, 2);
    memcpy(h + 24, &sr, 4);
    memcpy(h + 28, &byteRate, 4);
    uint16_t blockAlign = ch * bps / 8;
    memcpy(h + 32, &blockAlign, 2);
    memcpy(h + 34, &bps, 2);
    memcpy(h + 36, "data", 4);
    memcpy(h + 40, &dataBytes, 4);
}

static uint32_t mean_abs_pcm(const uint8_t *pcm, size_t nbytes) {
    size_t n = nbytes / 2;
    if (!n) return 0;
    const int16_t *s = (const int16_t *)pcm;
    uint64_t acc = 0;
    for (size_t i = 0; i < n; i++) {
        int32_t v = s[i];
        acc += (uint32_t)(v < 0 ? -v : v);
    }
    return (uint32_t)(acc / n);
}

static void extract_json_text(const String &body, char *out, size_t n) {
    out[0] = 0;
    int k = body.indexOf("\"text\"");
    if (k < 0) return;
    int colon = body.indexOf(':', k);
    if (colon < 0) return;
    int a = body.indexOf('"', colon + 1);
    if (a < 0) return;
    int b = body.indexOf('"', a + 1);
    if (b < 0 || b <= a) return;
    String t = body.substring(a + 1, b);
    t.replace("\\n", " ");
    t.replace("\\\"", "\"");
    strncpy(out, t.c_str(), n - 1);
    out[n - 1] = 0;
}

static bool do_upload() {
    write_wav_header(sPcm, (uint32_t)sSendBytes);
    bool ok = false;
    if (hid_connected() && ble_audio_can_send() && ble_audio_send_pcm(sPcm + 44, sSendBytes)) {
        Serial.println("[VOICE] ble audio ok");
        strncpy(gStatus.agent_state, "done", sizeof(gStatus.agent_state) - 1);
        ok = true;
    }
    if (!ok && WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        char url[192];
        snprintf(url, sizeof(url), "%s/v1/audio?key=%s&target=%s",
                 gCfg.host_url, gCfg.host_key, gCfg.voice_target);
        http.setTimeout(30000);
        if (http.begin(url)) {
            http.addHeader("Content-Type", "audio/wav");
            int code = http.POST(sPcm, 44 + sSendBytes);
            if (code == 200) {
                String body = http.getString();
                extract_json_text(body, gStatus.last_text, sizeof(gStatus.last_text));
                Serial.printf("[VOICE] asr %d %s\n", code, body.substring(0, 120).c_str());
                strncpy(gStatus.agent_state, "done", sizeof(gStatus.agent_state) - 1);
                ok = true;
            } else {
                Serial.printf("[VOICE] POST %d\n", code);
            }
            http.end();
        }
    }
    if (!ok) {
        Serial.println("[VOICE] fallback serial wav");
        serial_send_wav(sPcm, 44 + sSendBytes);
        strncpy(gStatus.agent_state, "done", sizeof(gStatus.agent_state) - 1);
        ok = true;
    }
    return ok;
}

void voice_init() {
    beep_pa(false);
    es7210_init();
    sPcm = (uint8_t *)heap_caps_malloc(44 + VOICE_MAX_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!sPcm) sPcm = (uint8_t *)heap_caps_malloc(44 + VOICE_MAX_BYTES, MALLOC_CAP_INTERNAL);
}

bool voice_is_recording() { return sRec; }
bool voice_is_busy() { return sRec || sBusy; }
VoiceSource voice_source() { return sSrc; }
uint32_t voice_rec_ms() { return sRec ? (millis() - sRecT0) : 0; }
bool voice_wants_overlay() {
    return (sRec || sBusy) && sSrc == VOICE_SRC_TAP;
}

void voice_start(VoiceSource src) {
    if (gStatus.prone) return;
    if (!sPcm || sRec || sBusy) return;
    if (src == VOICE_SRC_NONE) src = VOICE_SRC_TAP;
    beep_pa(false);
    es7210_init();
    i2s_start();
    sBytes = 0;
    sSilentBytes = 0;
    sHeardSpeech = false;
    sLoggedSlots = false;
    sMixA = 0;
    sMixB = -1;
    sSkipBlocks = VOICE_SKIP_BLOCKS;
    sSrc = src;
    sRecT0 = millis();
    sRec = true;
    gStatus.ptt = true;
    strncpy(gStatus.agent_state, "talk", sizeof(gStatus.agent_state) - 1);
    Serial.printf("[VOICE] start src=%d\n", (int)src);
}

void voice_loop() {
    if (!sRec || !sPcm) return;
    uint8_t tmp[1024];
    for (int spin = 0; spin < 16; spin++) {
        size_t got = 0;
        i2s_read(I2S_NUM_0, tmp, sizeof(tmp), &got, 0);
        if (got < 8) break;
        if (sSkipBlocks > 0) {
            sSkipBlocks--;
            continue;
        }
        int frames = (int)(got / 8);
        size_t need = (size_t)frames * 2;
        if (sBytes + need > VOICE_MAX_BYTES) {
            frames = (int)((VOICE_MAX_BYTES - sBytes) / 2);
            need = (size_t)frames * 2;
        }
        if (frames <= 0) {
            voice_stop_and_send(true);
            return;
        }
        int16_t *dst = (int16_t *)(sPcm + 44 + sBytes);
        const int16_t *slot = (const int16_t *)tmp;
        uint32_t acc0 = 0, acc1 = 0;
        for (int i = 0; i < frames; i++) {
            const int16_t *s = slot + i * 4;
            acc0 += (uint32_t)(s[0] < 0 ? -s[0] : s[0]);
            acc1 += (uint32_t)(s[1] < 0 ? -s[1] : s[1]);
        }
        if (!sLoggedSlots) {
            sLoggedSlots = true;
            sMixA = (acc1 > acc0) ? 1 : 0;
            sMixB = sMixA ? 0 : 1;
            Serial.printf("[VOICE] mic %u %u pick=%d got=%u\n",
                          (unsigned)(acc0 / (uint32_t)frames),
                          (unsigned)(acc1 / (uint32_t)frames),
                          sMixA, (unsigned)got);
        }
        for (int i = 0; i < frames; i++) {
            const int16_t *s = slot + i * 4;
            int32_t v = ((int32_t)s[0] + (int32_t)s[1]) / 2;
            int32_t g = v * 8;
            if (g > 32767) g = 32767;
            if (g < -32768) g = -32768;
            dst[i] = (int16_t)g;
        }
        sBytes += need;
        if (sBytes >= VOICE_MAX_BYTES) {
            voice_stop_and_send(true);
            return;
        }
    }
}

void voice_cancel() {
    if (!sRec) return;
    sRec = false;
    gStatus.ptt = false;
    i2s_stop();
    sSrc = VOICE_SRC_NONE;
    strncpy(gStatus.agent_state, "idle", sizeof(gStatus.agent_state) - 1);
    Serial.println("[VOICE] cancel");
}

static void upload_task(void *) {
    bool ok = do_upload();
    sBusy = false;
    sSrc = VOICE_SRC_NONE;
    if (ok) beep_request(BEEP_OK);
    vTaskDelete(nullptr);
}

void voice_stop_and_send(bool force) {
    if (!sRec) return;
    sRec = false;
    gStatus.ptt = false;
    i2s_stop();
    Serial.printf("[VOICE] stop bytes=%u mag=%u force=%d ms=%u\n",
                  (unsigned)sBytes, (unsigned)mean_abs_pcm(sPcm + 44, sBytes), force ? 1 : 0,
                  (unsigned)(millis() - sRecT0));
    if (sBytes < 8000) {
        Serial.println("[VOICE] too short");
        sSrc = VOICE_SRC_NONE;
        strncpy(gStatus.agent_state, "idle", sizeof(gStatus.agent_state) - 1);
        return;
    }
    if (!force) {
        uint32_t mag = mean_abs_pcm(sPcm + 44, sBytes);
        if (mag < VOICE_MEAN_ABS_MIN) {
            Serial.printf("[VOICE] silence mag=%u\n", (unsigned)mag);
            sSrc = VOICE_SRC_NONE;
            strncpy(gStatus.agent_state, "idle", sizeof(gStatus.agent_state) - 1);
            return;
        }
    }
    sSendBytes = sBytes;
    sBusy = true;
    strncpy(gStatus.agent_state, "waiting", sizeof(gStatus.agent_state) - 1);
    if (xTaskCreate(upload_task, "asr", 12288, nullptr, 1, nullptr) != pdPASS) {
        Serial.println("[VOICE] upload task fail, sync");
        bool ok = do_upload();
        sBusy = false;
        sSrc = VOICE_SRC_NONE;
        if (ok) beep_request(BEEP_OK);
    }
}
