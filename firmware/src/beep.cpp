#include "beep.h"
#include "board.h"
#include "voice.h"
#include "status.h"
#include "config.h"
#include "wood_pcm.h"
#include <Wire.h>
#include <Arduino.h>
#include <driver/i2s.h>
#include <math.h>
#include <cstring>

#define ES8311_ADDR0 0x18
#define ES8311_ADDR1 0x19
#define BEEP_SR 16000

static uint8_t sAddr = 0;
static BeepKind sPending = BEEP_NONE;
static bool sReady = false;
static bool sI2s = false;

static void es_write(uint8_t reg, uint8_t val) {
    if (!sAddr) return;
    Wire.beginTransmission(sAddr);
    Wire.write(reg);
    Wire.write(val);
    Wire.endTransmission();
}

static uint8_t es_read(uint8_t addr, uint8_t reg) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return 0xFF;
    if (Wire.requestFrom((int)addr, 1) != 1) return 0xFF;
    return (uint8_t)Wire.read();
}

static bool es8311_probe() {
    const uint8_t addrs[] = {ES8311_ADDR0, ES8311_ADDR1};
    for (uint8_t a : addrs) {
        uint8_t id = es_read(a, 0x00);
        if (id != 0xFF) {
            sAddr = a;
            return true;
        }
    }
    return false;
}

static void es8311_init() {
    if (!es8311_probe()) {
        Serial.println("[BEEP] no ES8311");
        sReady = false;
        return;
    }
    // Official Waveshare/esp-codec-dev start: 16-bit I2S, MCLK from pin, PA active-HIGH.
    es_write(0x00, 0x1F);
    delay(10);
    es_write(0x44, 0x08);
    es_write(0x44, 0x08);
    es_write(0x01, 0x30);
    es_write(0x02, 0x00);
    es_write(0x03, 0x10);
    es_write(0x16, 0x24);
    es_write(0x04, 0x10);
    es_write(0x05, 0x00);
    es_write(0x0B, 0x00);
    es_write(0x0C, 0x00);
    es_write(0x10, 0x1F);
    es_write(0x11, 0x7F);
    es_write(0x00, 0x80);
    es_write(0x01, 0x3F);
    es_write(0x09, 0x0C);
    es_write(0x0A, 0x0C);
    es_write(0x0D, 0x01);
    es_write(0x14, 0x1A);
    es_write(0x12, 0x00);
    es_write(0x13, 0x10);
    es_write(0x0E, 0x02);
    es_write(0x15, 0x40);
    es_write(0x1B, 0x0A);
    es_write(0x1C, 0x6A);
    es_write(0x17, 0xBF);
    es_write(0x37, 0x08);
    es_write(0x45, 0x00);
    es_write(0x32, 0xD0);
    es_write(0x31, 0x00);
    sReady = true;
    Serial.printf("[BEEP] es8311 0x%02X id=0x%02X dac=0x%02X mute=0x%02X\n",
                  sAddr, es_read(sAddr, 0x00), es_read(sAddr, 0x32), es_read(sAddr, 0x31));
}

static void pa_set(bool on) {
    digitalWrite(SND_PA_PIN, on ? HIGH : LOW);
}

void beep_pa(bool on) {
    pa_set(on);
}

void beep_codec_wake() {
    es8311_init();
}

static bool i2s_beep_open() {
    if (sI2s) return true;
    i2s_driver_uninstall(I2S_NUM_0);
    i2s_config_t cfg = {};
    cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
    cfg.sample_rate = BEEP_SR;
    cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
    cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
    cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    cfg.dma_buf_count = 4;
    cfg.dma_buf_len = 256;
    cfg.use_apll = false;
    cfg.tx_desc_auto_clear = true;
    if (i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr) != ESP_OK) {
        Serial.println("[BEEP] i2s install fail");
        return false;
    }
    i2s_pin_config_t pins = {};
    pins.mck_io_num = SND_I2S_MCLK;
    pins.bck_io_num = SND_I2S_BCLK;
    pins.ws_io_num = SND_I2S_WS;
    pins.data_out_num = SND_I2S_DOUT;
    pins.data_in_num = I2S_PIN_NO_CHANGE;
    if (i2s_set_pin(I2S_NUM_0, &pins) != ESP_OK) {
        Serial.println("[BEEP] i2s pin fail");
        i2s_driver_uninstall(I2S_NUM_0);
        return false;
    }
    i2s_zero_dma_buffer(I2S_NUM_0);
    sI2s = true;
    return true;
}

static void i2s_beep_close() {
    if (sI2s) delay((4000 * 256) / BEEP_SR + 80);
    pa_set(false);
    if (!sI2s) return;
    delay(12);
    i2s_driver_uninstall(I2S_NUM_0);
    sI2s = false;
}

static bool beep_begin() {
    if (voice_is_recording()) return false;
    if (!i2s_beep_open()) return false;
    es8311_init();
    if (!sReady) {
        i2s_beep_close();
        return false;
    }
    pa_set(true);
    delay(80);
    return true;
}

static void write_pcm16(const int16_t *mono, int n) {
    int16_t stereo[128];
    uint8_t vol = gCfg.beep_vol;
    if (vol > 100) vol = 100;
    int i = 0;
    while (i < n) {
        int chunk = n - i > 64 ? 64 : n - i;
        for (int k = 0; k < chunk; k++) {
            int32_t v = ((int32_t)mono[i + k] * (int32_t)vol) / 100;
            if (v > 32767) v = 32767;
            if (v < -32767) v = -32767;
            int16_t s = (int16_t)v;
            stereo[k * 2] = s;
            stereo[k * 2 + 1] = s;
        }
        size_t wrote = 0;
        i2s_write(I2S_NUM_0, stereo, (size_t)chunk * 4, &wrote, portMAX_DELAY);
        i += chunk;
    }
}

static void play_wood() {
    if (!beep_begin()) return;
    Serial.println("[BEEP] wood");
    int16_t mono[64];
    unsigned pcm_i = (wood_pcm_len > 1000) ? 1000u : 0u;
    int n_pcm = (int)(wood_pcm_len - pcm_i);
    const int n_synth = BEEP_SR * 200 / 1000;
    const int total = n_pcm > n_synth ? n_pcm : n_synth;
    float ph = 0.f;
    uint32_t rng = 0xA3C59AC3u;
    for (int i = 0; i < total; ) {
        int chunk = (total - i) > 64 ? 64 : (total - i);
        for (int k = 0; k < chunk; k++) {
            int idx = i + k;
            int32_t acc = 0;
            if (idx < n_pcm) acc += (int32_t)wood_pcm[pcm_i + (unsigned)idx] * 2;
            if (idx < n_synth) {
                float t = (float)idx / (float)BEEP_SR;
                float env = expf(-t * 22.f);
                rng = rng * 1664525u + 1013904223u;
                float noise = ((float)((rng >> 16) & 0xFFFFu) / 32768.f - 1.f) * env;
                float hz = 390.f * expf(-t * 10.f);
                ph += 6.2831853f * hz / (float)BEEP_SR;
                acc += (int32_t)((noise * 0.55f + sinf(ph) * env * 0.9f) * 22000.f);
            }
            acc = (acc * 2) / 3;
            if (acc > 32767) acc = 32767;
            if (acc < -32767) acc = -32767;
            mono[k] = (int16_t)acc;
        }
        write_pcm16(mono, chunk);
        i += chunk;
    }
    i2s_beep_close();
}

void beep_init() {
    pinMode(SND_PA_PIN, OUTPUT);
    pa_set(false);
    es8311_init();
}

void beep_request(BeepKind kind) {
    if (kind != BEEP_NONE) sPending = kind;
}

static void play_click() {
    if (!beep_begin()) return;
    Serial.println("[BEEP] click");
    const int n = BEEP_SR * 40 / 1000;
    int16_t mono[64];
    float ph = 0;
    float step = 2.0f * 3.14159265f * 2093.f / (float)BEEP_SR;
    for (int i = 0; i < n; ) {
        int chunk = (n - i) > 64 ? 64 : (n - i);
        for (int k = 0; k < chunk; k++) {
            float t = (float)(i + k) / (float)BEEP_SR;
            float env = expf(-t * 28.f);
            mono[k] = (int16_t)(sinf(ph) * env * 28000.f);
            ph += step;
        }
        write_pcm16(mono, chunk);
        i += chunk;
    }
    i2s_beep_close();
}

void beep_click() {
    play_click();
}

static void play_ding() {
    if (!beep_begin()) {
        Serial.println("[BEEP] ding skip");
        return;
    }
    Serial.println("[BEEP] drop");
    const int n = BEEP_SR * 90 / 1000;
    int16_t mono[64];
    const float pi2 = 6.2831853f;
    const float sr = (float)BEEP_SR;
    float ph = 0.f;
    for (int i = 0; i < n; ) {
        int chunk = (n - i) > 64 ? 64 : (n - i);
        for (int k = 0; k < chunk; k++) {
            float t = (float)(i + k) / sr;
            float atk = t < 0.002f ? (t / 0.002f) : 1.f;
            float env = atk * expf(-t * 28.f);
            float hz = 2400.f * expf(-t * 22.f) + 380.f;
            ph += pi2 * hz / sr;
            float v = sinf(ph) * env + sinf(ph * 2.1f) * env * 0.16f;
            int32_t s = (int32_t)(v * 24000.f);
            if (s > 32767) s = 32767;
            if (s < -32767) s = -32767;
            mono[k] = (int16_t)s;
        }
        write_pcm16(mono, chunk);
        i += chunk;
    }
    i2s_beep_close();
}

void beep_loop() {
    BeepKind k = sPending;
    if (k == BEEP_NONE) return;
    sPending = BEEP_NONE;
    if (k == BEEP_OK || k == BEEP_STOP) play_click();
    else if (k == BEEP_WARN || k == BEEP_ALERT) play_ding();
    else if (k == BEEP_WOOD) play_wood();
}
