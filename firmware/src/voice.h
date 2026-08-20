#pragma once
#include <stdint.h>

enum VoiceSource : uint8_t {
    VOICE_SRC_NONE = 0,
    VOICE_SRC_TAP = 1,
    VOICE_SRC_HOLD = 2,
};

void voice_init();
void voice_start(VoiceSource src);
void voice_stop_and_send(bool force = true);
void voice_cancel();
bool voice_is_recording();
bool voice_is_busy();
VoiceSource voice_source();
uint32_t voice_rec_ms();
bool voice_wants_overlay();
void voice_loop();
