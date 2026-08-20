#pragma once
#include <Arduino.h>

struct ProviderQuota {
    int h5 = 0;
    int d7 = 0;
    int mcp = 0;
    int auto_pct = 0;
    int api_pct = 0;
    int total_pct = 0;
    bool has_h5 = false;
    bool has_d7 = false;
    bool has_mcp = false;
    bool has_auto = false;
    bool has_api = false;
    bool has_total = false;
    uint32_t reset_h5 = 0;
    uint32_t reset_d7 = 0;
    uint32_t reset_mcp = 0;
    uint32_t cycle_end = 0;
    long daily_tokens = 0;
    long tool_search = 0;
    long tool_webread = 0;
    int left = -1;
    int cap = -1;
    bool has_qty = false;
    bool ok = false;
    char err[24] = {0};
};

struct DeskStatus {
    uint32_t ts = 0;
    char agent_state[16] = "idle";
    char agent_name[16] = "";
    ProviderQuota claude;
    ProviderQuota deepseek;
    ProviderQuota codex;
    ProviderQuota cursor;
    ProviderQuota glm;
    ProviderQuota kimi;
    ProviderQuota trae;
    ProviderQuota coze;
    int battery_pct = -1;
    bool charging = false;
    bool wifi_ok = false;
    bool host_ok = false;
    bool ptt = false;
    bool key_busy = false;
    bool prone = false;
    bool screen_off = false;
    char last_text[96] = {0};
    char wx_text[24] = {0};
    int wx_temp = 28;
};

extern DeskStatus gStatus;
extern volatile bool gPollingNow;
extern uint32_t gLastPollAt;
extern int gWarnThreshold;
extern int gAlertThreshold;
extern bool gAlertAck;
extern bool gWarnAck;

void status_reset_alert_if_recovered();
int status_max_quota_percent();
