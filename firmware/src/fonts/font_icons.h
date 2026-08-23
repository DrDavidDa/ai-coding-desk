#pragma once
#include <lvgl.h>

extern const lv_font_t font_icons;

/* Font Awesome solid: stop (square) / microphone
 * Stop = end recording & send — NOT cancel. Cancel is top chip / PWR. */
#define ICON_STOP "\xEF\x81\x8D"  /* U+F04D */
#define ICON_MIC  "\xEF\x84\xB0"  /* U+F130 */
#define ICON_BAN ICON_STOP        /* legacy alias — do not use for cancel */
