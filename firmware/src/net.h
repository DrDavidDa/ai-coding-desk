#pragma once
void net_init();
void net_loop();
void net_poll_now(bool fresh = false);
void net_kick_fresh();
bool net_wifi_ok();
bool parse_status_json(const char *json);
