#pragma once
#include <stddef.h>
#include <stdint.h>

void serial_init();
void serial_loop();
void serial_send_wav(const uint8_t *data, size_t n);
