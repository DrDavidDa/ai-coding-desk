#include "status.h"

DeskStatus gStatus;
volatile bool gPollingNow = false;
uint32_t gLastPollAt = 0;
int gWarnThreshold = 70;
int gAlertThreshold = 90;
bool gAlertAck = false;
bool gWarnAck = false;

void status_reset_alert_if_recovered() {
    int used = status_max_quota_percent();
    if (used < gAlertThreshold) gAlertAck = false;
    if (used < gWarnThreshold) gWarnAck = false;
}

int status_max_quota_percent() {
    // Alert on *used* percent. Cursor/Claude/Codex APIs are utilization.
    // GLM Coding Plan `percentage` is remaining, so invert.
    int m = 0;
    auto bump_used = [&](const ProviderQuota& p) {
        if (!p.ok) return;
        if (p.h5 > m) m = p.h5;
        if (p.d7 > m) m = p.d7;
        if (p.mcp > m) m = p.mcp;
        if (p.auto_pct > m) m = p.auto_pct;
        if (p.api_pct > m) m = p.api_pct;
        if (p.total_pct > m) m = p.total_pct;
    };
    auto bump_remaining = [&](const ProviderQuota& p) {
        if (!p.ok) return;
        auto inv = [&](int left) {
            if (left < 0) left = 0;
            if (left > 100) left = 100;
            int used = 100 - left;
            if (used > m) m = used;
        };
        inv(p.h5);
        inv(p.d7);
        inv(p.mcp);
    };
    bump_used(gStatus.claude);
    bump_used(gStatus.codex);
    bump_used(gStatus.cursor);
    bump_used(gStatus.kimi);
    bump_used(gStatus.trae);
    bump_used(gStatus.coze);
    bump_remaining(gStatus.glm);
    /* deepseek balance is yuan, not a percent window — skip bump */
    return m;
}
