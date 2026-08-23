#include "serial_cmd.h"
#include "config.h"
#include "status.h"
#include "net.h"
#include "board.h"
#include "hid_keys.h"
#include "beep.h"
#include "imu.h"
#include "display.h"
#include "ui.h"
#include <cstring>
#include <cstdlib>
#include <ctime>
#include <sys/time.h>
#include <esp_system.h>
#include <soc/rtc_cntl_reg.h>

static char sLine[SERIAL_LINE_MAX];
static size_t sLen = 0;
static volatile bool sRaw = false;

static void ack(const char *msg) { Serial.printf("[OK] %s\n", msg); }

static void handle(char *line) {
    if (!strcmp(line, "#STATUS")) {
        Serial.printf("use_wifi=%d ssid=%s cookie_len=0 pollnow=%d cfg_ok=1 host_ok=%d wifi=%d bat=%d ptt=%d voice=%s hid=%d adv=%d\n",
                      gCfg.wifi_ssid[0][0] ? 1 : 0, gCfg.wifi_ssid[0], gPollingNow ? 1 : 0,
                      gStatus.host_ok ? 1 : 0, gStatus.wifi_ok ? 1 : 0, gStatus.battery_pct, gStatus.ptt ? 1 : 0,
                      gCfg.voice_mode, hid_connected() ? 1 : 0, hid_advertising() ? 1 : 0);
        Serial.printf("[CP] 智谱额度: 5h=%d%% 7d=%d%% mcp=%d%%\n", gStatus.glm.h5, gStatus.glm.d7, gStatus.glm.mcp);
        return;
    }
    if (!strcmp(line, "#POLL")) {
        gLastPollAt = 0;
        net_poll_now(true);
        ack("poll");
        return;
    }
    if (!strcmp(line, "#CFGREAD")) {
        config_dump_serial();
        return;
    }
    if (!strcmp(line, "#CFGCLEAR")) {
        config_clear();
        ack("cfg cleared");
        return;
    }
    if (!strncmp(line, "#CFGLINE|", 9)) {
        config_apply_line(line + 9);
        ack("line");
        return;
    }
    if (!strncmp(line, "#CFGTOK|", 8)) {
        // Host-side tokens stay on PC. Ignore device token chunks.
        ack("tok");
        return;
    }
    if (!strcmp(line, "#CFGDONE")) {
        config_save();
        ack("config saved");
        return;
    }
    if (!strcmp(line, "#WAKE")) {
        display_apply_presence();
        ui_force_wake();
        ack("wake");
        return;
    }
    if (!strncmp(line, "#TEXT|", 6)) {
        strncpy(gStatus.last_text, line + 6, sizeof(gStatus.last_text) - 1);
        gStatus.last_text[sizeof(gStatus.last_text) - 1] = 0;
        strncpy(gStatus.agent_state, "done", sizeof(gStatus.agent_state) - 1);
        ui_refresh_from_status();
        ack("text");
        return;
    }
    if (!strcmp(line, "#BEEP")) {
        beep_request(BEEP_OK);
        ack("beep");
        return;
    }
    if (!strcmp(line, "#BEEPSTOP")) {
        beep_request(BEEP_STOP);
        ack("beep stop");
        return;
    }
    if (!strcmp(line, "#BEEPALERT")) {
        beep_request(BEEP_ALERT);
        ack("beep alert");
        return;
    }
    if (!strcmp(line, "#IMU")) {
        Serial.printf("imu=%d\n", imu_ok() ? 1 : 0);
        return;
    }
    if (!strncmp(line, "#TIME ", 6)) {
        unsigned long unix = strtoul(line + 6, nullptr, 10);
        if (unix > 1700000000UL) {
            setenv("TZ", "CST-8", 1);
            tzset();
            struct timeval tv;
            tv.tv_sec = (time_t)unix;
            tv.tv_usec = 0;
            settimeofday(&tv, nullptr);
            ack("time");
        }
        return;
    }
    if (!strcmp(line, "#DOWNLOAD")) {
        Serial.println("[OK] download");
        Serial.flush();
        delay(80);
        REG_WRITE(RTC_CNTL_OPTION1_REG, RTC_CNTL_FORCE_DOWNLOAD_BOOT);
        esp_restart();
        return;
    }
    if (!strncmp(line, "#QJ|", 4)) {
        if (parse_status_json(line + 4)) {
            ui_refresh_from_status();
            Serial.printf("[QJ] glm=%d cursor=%d kimi=%d host_ok=1\n",
                          gStatus.glm.h5, gStatus.cursor.auto_pct, gStatus.kimi.h5);
        } else {
            Serial.println("[ERR] qj");
        }
        return;
    }
    Serial.printf("[ERR] unknown %s\n", line);
}

void serial_send_wav(const uint8_t *data, size_t n) {
    if (!data || n < 44) return;
    sRaw = true;
    delay(20);
    Serial.printf("#WAVBEGIN %u\n", (unsigned)n);
    Serial.flush();
    size_t off = 0;
    while (off < n) {
        size_t chunk = n - off;
        if (chunk > 256) chunk = 256;
        Serial.write(data + off, chunk);
        off += chunk;
        delay(1);
    }
    Serial.flush();
    Serial.print("\n#WAVEND\n");
    Serial.flush();
    sRaw = false;
    Serial.printf("[VOICE] serial wav %u\n", (unsigned)n);
}

void serial_init() {
    Serial.setRxBufferSize(SERIAL_LINE_MAX);
    if (!Serial) {
        Serial.begin(115200);
        delay(200);
    }
    Serial.println("Desk154 ready");
}

void serial_loop() {
    if (sRaw) return;
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\r') continue;
        if (c == '\n') {
            sLine[sLen] = 0;
            if (sLen) handle(sLine);
            sLen = 0;
            continue;
        }
        if (sLen + 1 < sizeof(sLine)) sLine[sLen++] = c;
    }
}
