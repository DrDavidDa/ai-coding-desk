#pragma once
#include <Arduino.h>
#include <Preferences.h>

struct DeskConfig {
    char wifi_ssid[3][33] = {{0}};
    char wifi_pass[3][65] = {{0}};
    char host_url[96] = "http://192.168.1.10:8787";
    char host_key[48] = "desk-local";
    uint16_t poll_quota_sec = 60;
    uint16_t poll_agent_sec = 3;
    int warn_threshold = 70;
    int alert_threshold = 90;
    char voice_mode[12] = "device";   // device | hid
    char voice_target[12] = "cursor"; // cursor | claude | codex
    uint8_t wall_id = 0;              // 0..WALL_COUNT-1
    uint16_t idle_sec = 300;          // 0 = never blank; default 5 min full off
    uint8_t beep_vol = 80;            // 0 = mute, 100 = full prompt volume
};

extern DeskConfig gCfg;
extern Preferences gPrefs;

void config_load();
void config_save();
void config_apply_line(const char* line);
void config_clear();
void config_dump_serial();
