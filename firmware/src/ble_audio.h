#pragma once
#include <stddef.h>
#include <stdint.h>

void ble_audio_init();
bool ble_audio_can_send();
bool ble_audio_send_pcm(const uint8_t *pcm, size_t nbytes);
bool ble_audio_send_stop();
