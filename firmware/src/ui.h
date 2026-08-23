#pragma once
void ui_init();
void ui_loop();
void ui_next_page();
void ui_prev_page();
void ui_refresh_from_status();
void ui_toast(const char *msg);
void ui_pack_press();
void ui_pack_oracle();
void ui_note_activity();
void ui_wake_from_idle();
void ui_force_wake();
int ui_page();
bool ui_is_idle();
bool ui_is_usage();
bool ui_is_pack();
bool ui_oracle_visible();
bool ui_nav_blocked();
