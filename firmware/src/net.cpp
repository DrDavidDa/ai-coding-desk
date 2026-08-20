#include "net.h"
#include "config.h"
#include "status.h"
#include "board.h"
#include "voice.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <cstring>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static uint32_t sLastQuota = 0;
static uint32_t sLastAgent = 0;
static volatile bool sWantFresh = false;
static TaskHandle_t sPollTask = nullptr;
static void poll_task(void *);

static void apply_provider(ProviderQuota &dst, JsonObjectConst o) {
    if (o.isNull()) return;
    dst.has_h5 = !o["h5"].isNull();
    if (dst.has_h5) dst.h5 = o["h5"].as<int>();
    dst.has_d7 = !o["d7"].isNull();
    if (dst.has_d7) dst.d7 = o["d7"].as<int>();
    dst.has_mcp = !o["mcp"].isNull();
    if (dst.has_mcp) dst.mcp = o["mcp"].as<int>();
    dst.has_auto = !o["auto_pct"].isNull();
    if (dst.has_auto) dst.auto_pct = o["auto_pct"].as<int>();
    dst.has_api = !o["api_pct"].isNull();
    if (dst.has_api) dst.api_pct = o["api_pct"].as<int>();
    dst.has_total = !o["total_pct"].isNull();
    if (dst.has_total) dst.total_pct = o["total_pct"].as<int>();
    if (!o["reset_h5"].isNull()) dst.reset_h5 = o["reset_h5"].as<uint32_t>();
    if (!o["reset_d7"].isNull()) dst.reset_d7 = o["reset_d7"].as<uint32_t>();
    if (!o["reset_mcp"].isNull()) dst.reset_mcp = o["reset_mcp"].as<uint32_t>();
    if (!o["cycle_end"].isNull()) dst.cycle_end = o["cycle_end"].as<uint32_t>();
    if (!o["daily_tokens"].isNull()) dst.daily_tokens = (long)o["daily_tokens"].as<int>();
    if (!o["tool_search"].isNull()) dst.tool_search = (long)o["tool_search"].as<int>();
    if (!o["tool_webread"].isNull()) dst.tool_webread = (long)o["tool_webread"].as<int>();
    dst.has_qty = !o["left"].isNull() && !o["cap"].isNull();
    if (dst.has_qty) {
        dst.left = o["left"].as<int>();
        dst.cap = o["cap"].as<int>();
    }
    if (!o["ok"].isNull()) dst.ok = o["ok"].as<bool>();
    const char *err = o["err"] | "";
    strncpy(dst.err, err, sizeof(dst.err) - 1);
}

bool parse_status_json(const char *json) {
    JsonDocument doc;
    if (deserializeJson(doc, json)) return false;
    gStatus.ts = doc["ts"] | (uint32_t)(millis() / 1000);
    const char *st = doc["agent"]["state"] | "idle";
    const char *nm = doc["agent"]["name"] | "";
    strncpy(gStatus.agent_state, st, sizeof(gStatus.agent_state) - 1);
    strncpy(gStatus.agent_name, nm, sizeof(gStatus.agent_name) - 1);
    JsonObjectConst prov = doc["providers"];
    apply_provider(gStatus.claude, prov["claude"]);
    apply_provider(gStatus.deepseek, prov["deepseek"]);
    apply_provider(gStatus.codex, prov["codex"]);
    apply_provider(gStatus.cursor, prov["cursor"]);
    apply_provider(gStatus.glm, prov["glm"]);
    apply_provider(gStatus.kimi, prov["kimi"]);
    apply_provider(gStatus.trae, prov["trae"]);
    apply_provider(gStatus.coze, prov["coze"]);
    const char *vt = doc["voice"]["last_text"] | "";
    if (vt[0]) {
        strncpy(gStatus.last_text, vt, sizeof(gStatus.last_text) - 1);
        gStatus.last_text[sizeof(gStatus.last_text) - 1] = 0;
    }
    gStatus.host_ok = true;
    status_reset_alert_if_recovered();
    return true;
}

static bool have_ssid() {
    for (int i = 0; i < 3; i++) {
        if (gCfg.wifi_ssid[i][0]) return true;
    }
    return false;
}

static bool try_wifi() {
    if (!have_ssid()) {
        gStatus.wifi_ok = false;
        return false;
    }
    if (WiFi.status() == WL_CONNECTED) {
        gStatus.wifi_ok = true;
        return true;
    }
    WiFi.mode(WIFI_STA);
    for (int i = 0; i < 3; i++) {
        if (!gCfg.wifi_ssid[i][0]) continue;
        WiFi.begin(gCfg.wifi_ssid[i], gCfg.wifi_pass[i]);
        uint32_t t0 = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - t0 < 8000) delay(200);
        if (WiFi.status() == WL_CONNECTED) {
            gStatus.wifi_ok = true;
            configTime(8 * 3600, 0, "ntp.aliyun.com", "pool.ntp.org");
            Serial.printf("[NET] wifi %s ip %s\n", gCfg.wifi_ssid[i], WiFi.localIP().toString().c_str());
            return true;
        }
    }
    gStatus.wifi_ok = false;
    return false;
}

void net_init() {
    xTaskCreate(poll_task, "netpoll", 16384, nullptr, 1, &sPollTask);
    if (!have_ssid()) {
        Serial.println("[NET] no ssid, wifi untouched so BLE can advertise");
        return;
    }
    if (try_wifi()) return;
    Serial.println("[NET] no wifi — skip portal (serial/BLE audio still works)");
}

static void poll_http(bool fresh) {
    if (gPollingNow || gStatus.ptt || voice_is_busy()) return;
    if (!fresh && gStatus.key_busy) return;
    if (!try_wifi()) {
        Serial.println("#NEEDQ");
        return;
    }
    gPollingNow = true;
    HTTPClient http;
    char url[192];
    snprintf(url, sizeof(url), "%s/v1/status?key=%s%s",
             gCfg.host_url, gCfg.host_key, fresh ? "&fresh=1" : "");
    http.setTimeout(fresh ? 15000 : 8000);
    if (!http.begin(url)) {
        gPollingNow = false;
        return;
    }
    int code = http.GET();
    if (code == 200) {
        String body = http.getString();
        int brace = body.indexOf('{');
        if (brace >= 0) {
            body = body.substring(brace);
            if (parse_status_json(body.c_str())) {
                Serial.printf("[NET] glm 5h=%d 7d=%d mcp=%d ds=%d cl=%d host_ok=1\n",
                              gStatus.glm.h5, gStatus.glm.d7, gStatus.glm.mcp,
                              (int)gStatus.deepseek.ok, (int)gStatus.claude.ok);
            }
        }
    } else {
        Serial.printf("[NET] GET %d\n", code);
    }
    http.end();
    gLastPollAt = millis();
    gPollingNow = false;
}

static void poll_task(void *) {
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        bool fresh = sWantFresh;
        sWantFresh = false;
        poll_http(fresh);
        if (sWantFresh) xTaskNotifyGive(sPollTask);
    }
}

void net_poll_now(bool fresh) {
    if (fresh) sWantFresh = true;
    if (sPollTask) {
        xTaskNotifyGive(sPollTask);
        return;
    }
    poll_http(fresh);
}

void net_kick_fresh() { net_poll_now(true); }

void net_loop() {
    uint32_t now = millis();
    uint32_t interval = (uint32_t)gCfg.poll_quota_sec * 1000UL;
    if (interval < 15000UL) interval = 15000UL;
    if (gLastPollAt == 0 || now - gLastPollAt >= interval) net_poll_now(false);
    (void)sLastQuota;
    (void)sLastAgent;
}

bool net_wifi_ok() { return gStatus.wifi_ok; }
