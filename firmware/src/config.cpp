#include "config.h"
#include "status.h"
#include "board.h"
#include <cstring>

DeskConfig gCfg;
Preferences gPrefs;

void config_load() {
    gPrefs.begin("desk154", true);
    gPrefs.getString("ssid0", gCfg.wifi_ssid[0], sizeof(gCfg.wifi_ssid[0]));
    gPrefs.getString("pass0", gCfg.wifi_pass[0], sizeof(gCfg.wifi_pass[0]));
    gPrefs.getString("ssid1", gCfg.wifi_ssid[1], sizeof(gCfg.wifi_ssid[1]));
    gPrefs.getString("pass1", gCfg.wifi_pass[1], sizeof(gCfg.wifi_pass[1]));
    gPrefs.getString("ssid2", gCfg.wifi_ssid[2], sizeof(gCfg.wifi_ssid[2]));
    gPrefs.getString("pass2", gCfg.wifi_pass[2], sizeof(gCfg.wifi_pass[2]));
    gPrefs.getString("host", gCfg.host_url, sizeof(gCfg.host_url));
    gPrefs.getString("key", gCfg.host_key, sizeof(gCfg.host_key));
    gCfg.poll_quota_sec = gPrefs.getUShort("pq", 60);
    gCfg.poll_agent_sec = gPrefs.getUShort("pa", 3);
    gCfg.warn_threshold = gPrefs.getInt("warn", WARN_THRESHOLD_DEFAULT);
    gCfg.alert_threshold = gPrefs.getInt("alert", ALERT_THRESHOLD_DEFAULT);
    gPrefs.getString("vmode", gCfg.voice_mode, sizeof(gCfg.voice_mode));
    gPrefs.getString("vtarget", gCfg.voice_target, sizeof(gCfg.voice_target));
    gCfg.wall_id = gPrefs.getUChar("wall", 0);
    if (gCfg.wall_id >= 6) gCfg.wall_id = 0;
    gCfg.idle_sec = gPrefs.getUShort("idle", 300);
    if (gCfg.idle_sec == 180) gCfg.idle_sec = 300; /* old clock-idle default → 5 min blank */
    gCfg.beep_vol = gPrefs.getUChar("bvol", 80);
    if (gCfg.beep_vol > 100) gCfg.beep_vol = 80;
    if (!gCfg.voice_mode[0]) strncpy(gCfg.voice_mode, "device", sizeof(gCfg.voice_mode) - 1);
    if (!gCfg.voice_target[0]) strncpy(gCfg.voice_target, "cursor", sizeof(gCfg.voice_target) - 1);
    gPrefs.end();
    gWarnThreshold = gCfg.warn_threshold;
    gAlertThreshold = gCfg.alert_threshold;
}

void config_save() {
    gPrefs.begin("desk154", false);
    gPrefs.putString("ssid0", gCfg.wifi_ssid[0]);
    gPrefs.putString("pass0", gCfg.wifi_pass[0]);
    gPrefs.putString("ssid1", gCfg.wifi_ssid[1]);
    gPrefs.putString("pass1", gCfg.wifi_pass[1]);
    gPrefs.putString("ssid2", gCfg.wifi_ssid[2]);
    gPrefs.putString("pass2", gCfg.wifi_pass[2]);
    gPrefs.putString("host", gCfg.host_url);
    gPrefs.putString("key", gCfg.host_key);
    gPrefs.putUShort("pq", gCfg.poll_quota_sec);
    gPrefs.putUShort("pa", gCfg.poll_agent_sec);
    gPrefs.putInt("warn", gCfg.warn_threshold);
    gPrefs.putInt("alert", gCfg.alert_threshold);
    gPrefs.putString("vmode", gCfg.voice_mode);
    gPrefs.putString("vtarget", gCfg.voice_target);
    gPrefs.putUChar("wall", gCfg.wall_id);
    gPrefs.putUShort("idle", gCfg.idle_sec);
    gPrefs.putUChar("bvol", gCfg.beep_vol);
    gPrefs.end();
    gWarnThreshold = gCfg.warn_threshold;
    gAlertThreshold = gCfg.alert_threshold;
}

void config_clear() {
    gPrefs.begin("desk154", false);
    gPrefs.clear();
    gPrefs.end();
    gCfg = DeskConfig{};
}

static void set_kv(const char* k, const char* v) {
    if (!strcmp(k, "wifi_ssid") || !strcmp(k, "wifi_ssid1")) strncpy(gCfg.wifi_ssid[0], v, 32);
    else if (!strcmp(k, "wifi_pass") || !strcmp(k, "wifi_pass1")) strncpy(gCfg.wifi_pass[0], v, 64);
    else if (!strcmp(k, "wifi_ssid2")) strncpy(gCfg.wifi_ssid[1], v, 32);
    else if (!strcmp(k, "wifi_pass2")) strncpy(gCfg.wifi_pass[1], v, 64);
    else if (!strcmp(k, "wifi_ssid3")) strncpy(gCfg.wifi_ssid[2], v, 32);
    else if (!strcmp(k, "wifi_pass3")) strncpy(gCfg.wifi_pass[2], v, 64);
    else if (!strcmp(k, "host_url")) strncpy(gCfg.host_url, v, sizeof(gCfg.host_url) - 1);
    else if (!strcmp(k, "host_key")) strncpy(gCfg.host_key, v, sizeof(gCfg.host_key) - 1);
    else if (!strcmp(k, "poll_interval_sec") || !strcmp(k, "poll")) {
        int n = atoi(v);
        if (n < 15) n = 15;
        if (n > 600) n = 600;
        gCfg.poll_quota_sec = (uint16_t)n;
    }
    else if (!strcmp(k, "warn_threshold")) gCfg.warn_threshold = atoi(v);
    else if (!strcmp(k, "alert_threshold")) gCfg.alert_threshold = atoi(v);
    else if (!strcmp(k, "voice_mode")) strncpy(gCfg.voice_mode, v, sizeof(gCfg.voice_mode) - 1);
    else if (!strcmp(k, "voice_target")) strncpy(gCfg.voice_target, v, sizeof(gCfg.voice_target) - 1);
    else if (!strcmp(k, "wall_id")) {
        int n = atoi(v);
        if (n < 0) n = 0;
        if (n > 5) n = 5;
        gCfg.wall_id = (uint8_t)n;
    } else if (!strcmp(k, "idle_sec")) {
        int n = atoi(v);
        if (n < 0) n = 0;
        if (n > 3600) n = 3600;
        gCfg.idle_sec = (uint16_t)n;
    } else if (!strcmp(k, "beep_vol")) {
        int n = atoi(v);
        if (n < 0) n = 0;
        if (n > 100) n = 100;
        gCfg.beep_vol = (uint8_t)n;
    }
}

void config_apply_line(const char* line) {
    const char* eq = strchr(line, '=');
    if (!eq) return;
    char k[32];
    size_t kn = (size_t)(eq - line);
    if (kn >= sizeof(k)) kn = sizeof(k) - 1;
    memcpy(k, line, kn);
    k[kn] = 0;
    set_kv(k, eq + 1);
}

void config_dump_serial() {
    Serial.printf("wifi_ssid=%s\n", gCfg.wifi_ssid[0]);
    Serial.printf("host_url=%s\n", gCfg.host_url);
    Serial.printf("host_key_len=%u\n", (unsigned)strlen(gCfg.host_key));
    Serial.printf("warn=%d alert=%d poll=%u voice=%s target=%s wall=%u idle=%u beep_vol=%u\n",
                  gCfg.warn_threshold, gCfg.alert_threshold, gCfg.poll_quota_sec,
                  gCfg.voice_mode, gCfg.voice_target, gCfg.wall_id, gCfg.idle_sec, gCfg.beep_vol);
}
