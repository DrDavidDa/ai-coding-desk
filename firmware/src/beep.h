#pragma once
enum BeepKind : int {
    BEEP_NONE = 0,
    BEEP_OK = 1,
    BEEP_STOP = 2,
    BEEP_ALERT = 3,
    BEEP_WARN = 4,
    BEEP_WOOD = 5,
};

void beep_init();
void beep_request(BeepKind kind);
void beep_click();
void beep_loop();
void beep_codec_wake();
void beep_pa(bool on);
