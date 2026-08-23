#pragma once
#include <Arduino_GFX_Library.h>
#include <lvgl.h>

extern Arduino_GFX *gGfx;

void display_init();
void display_wire_begin();
void display_poll();
void display_set_backlight(uint8_t pct);
void display_blank();
void display_apply_presence();
void display_user_wake();
void display_swallow_until_release();
void display_clear_touch_swallow();
void lvgl_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p);
void touch_read(lv_indev_drv_t *indev, lv_indev_data_t *data);
void battery_update();
void board_power_hold();
void board_power_off();
