#include <Arduino.h>
#include "board.h"
#include "status.h"
#include "config.h"
#include "display.h"
#include "ui.h"
#include "rgb.h"
#include "hid_keys.h"
#include "net.h"
#include "voice.h"
#include "beep.h"
#include "imu.h"
#include "serial_cmd.h"
#include "buttons.h"

void setup() {
    /* Clear latched BAT_EN hold; keep battery path on for LCD rail. */
    board_power_hold();
    pinMode(LCD_BL, OUTPUT);
    digitalWrite(LCD_BL, HIGH);
    display_set_backlight(100);

    serial_init();
    Serial.println("[BOOT] 1 serial");
    config_load();
    Serial.println("[BOOT] 2 cfg");
    display_init();
    Serial.println("[BOOT] 3 disp");
    rgb_init();
    buttons_init();
    voice_init();
    beep_init();
    imu_init();
    Serial.println("[BOOT] 4 hw");
    ui_init();
    Serial.println("[BOOT] 5 ui");
    battery_update();
    net_init();
    hid_init();
    Serial.println("[BOOT] waveshare_lcd_154");
}

void loop() {
    serial_loop();
    buttons_loop();
    hid_loop();
    voice_loop();
    imu_loop();
    net_loop();
    battery_update();
    display_poll();
    ui_refresh_from_status();
    ui_loop();
    beep_loop();
    rgb_loop();
    delay(5);
}
