#include "display.h"
#include "board.h"
#include "status.h"
#include "imu.h"
#include "ui.h"
#include <Arduino.h>
#include <Wire.h>
#include <esp_sleep.h>
#include <esp_heap_caps.h>
#include <driver/gpio.h>
#include <driver/rtc_io.h>

Arduino_GFX *gGfx = nullptr;
static Arduino_DataBus *sBus = nullptr;
static lv_disp_draw_buf_t sDrawBuf;
static lv_color_t *sBuf1 = nullptr;
static lv_disp_drv_t sDispDrv;
static lv_indev_drv_t sIndevDrv;
static uint8_t sBl = 100;
static bool sSwallowTouch = false;
static uint32_t sSwallowAt = 0;

void display_apply_presence() {
    gStatus.screen_off = false;
    sBl = 100;
    if (gGfx) gGfx->displayOn();
    display_set_backlight(100);
}

void display_blank() {
    if (gStatus.screen_off) return;
    gStatus.screen_off = true;
    display_set_backlight(0);
    if (gGfx) gGfx->displayOff();
    display_swallow_until_release();
    Serial.println("[DISP] blank");
}

void display_user_wake() {
    if (!gStatus.screen_off) return;
    gStatus.screen_off = false;
    if (gGfx) gGfx->displayOn();
    sBl = 100;
    display_set_backlight(100);
    display_swallow_until_release();
    Serial.println("[DISP] wake");
}

void display_swallow_until_release() {
    sSwallowTouch = true;
    sSwallowAt = millis();
}

void display_clear_touch_swallow() {
    sSwallowTouch = false;
    sSwallowAt = 0;
}

void board_power_hold() {
    /* Old builds could gpio_hold_en(BAT_EN) LOW — that latches across reset
       until hold is cleared, so digitalWrite alone cannot revive the LCD rail. */
    gpio_deep_sleep_hold_dis();
    gpio_hold_dis((gpio_num_t)BAT_EN);
    pinMode(BAT_EN, OUTPUT);
    digitalWrite(BAT_EN, HIGH);
    gpio_hold_dis((gpio_num_t)LCD_BL);
}

void board_power_off() {
    display_set_backlight(0);
    gpio_hold_dis((gpio_num_t)BAT_EN);
    digitalWrite(BAT_EN, HIGH);
    pinMode(BTN_PWR_GPIO, INPUT_PULLUP);
    rtc_gpio_pulldown_dis((gpio_num_t)BTN_PWR_GPIO);
    rtc_gpio_pullup_en((gpio_num_t)BTN_PWR_GPIO);
    esp_sleep_enable_ext0_wakeup((gpio_num_t)BTN_PWR_GPIO, 0);
    esp_deep_sleep_start();
}

void display_set_backlight(uint8_t pct) {
    ledcSetup(0, 5000, 8);
    ledcAttachPin(LCD_BL, 0);
    ledcWrite(0, (uint32_t)pct * 255 / 100);
}

static uint32_t sTpReadyAt = 0;
static bool sTpNeedRecover = false;

void display_wire_begin() {
    /* 100 kHz: CST816 + QMI8658 on one bus; 400 kHz wedges the ESP32 I2C FSM. */
    Wire.begin(IIC_SDA, IIC_SCL, 100000);
    Wire.setTimeOut(50);
}

static void tp_bus_recover() {
    digitalWrite(TP_RST, LOW);
    delay(8);
    digitalWrite(TP_RST, HIGH);
    delay(20);
    Wire.end();
    display_wire_begin();
    sTpReadyAt = millis() + 200;
    sTpNeedRecover = false;
    Serial.println("[TP] wire reset");
}

void display_poll() {
    if (sTpNeedRecover) tp_bus_recover();
}

void display_init() {
    board_power_hold();
    pinMode(LCD_BL, OUTPUT);
    display_set_backlight(100);

    sBus = new Arduino_ESP32SPI(LCD_DC, LCD_CS, LCD_SCLK, LCD_MOSI, GFX_NOT_DEFINED);
    gGfx = new Arduino_ST7789(sBus, LCD_RST, 0 /* rotation */, true /* IPS */,
                              LCD_WIDTH, LCD_HEIGHT);
    gGfx->begin(40000000);
    gGfx->fillScreen(BLACK);

    pinMode(TP_INT, INPUT_PULLUP);
    pinMode(TP_RST, OUTPUT);
    digitalWrite(TP_RST, LOW);
    delay(10);
    digitalWrite(TP_RST, HIGH);
    delay(50);
    display_wire_begin();
    sTpReadyAt = millis() + 1500;

    analogReadResolution(12);
    pinMode(CHG_STAT_PIN, INPUT);

    lv_init();
    const uint32_t px = LCD_WIDTH * 40;
    sBuf1 = (lv_color_t *)heap_caps_malloc(px * sizeof(lv_color_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!sBuf1) sBuf1 = (lv_color_t *)heap_caps_malloc(px * sizeof(lv_color_t), MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    lv_disp_draw_buf_init(&sDrawBuf, sBuf1, nullptr, px);
    lv_disp_drv_init(&sDispDrv);
    sDispDrv.hor_res = LCD_WIDTH;
    sDispDrv.ver_res = LCD_HEIGHT;
    sDispDrv.flush_cb = lvgl_flush;
    sDispDrv.draw_buf = &sDrawBuf;
    lv_disp_drv_register(&sDispDrv);

    lv_indev_drv_init(&sIndevDrv);
    sIndevDrv.type = LV_INDEV_TYPE_POINTER;
    sIndevDrv.read_cb = touch_read;
    sIndevDrv.scroll_limit = 22;   /* CST816 jitter was killing CLICKED */
    sIndevDrv.gesture_limit = 55;
    lv_indev_drv_register(&sIndevDrv);
}

void lvgl_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p) {
    if (gStatus.screen_off) {
        lv_disp_flush_ready(disp);
        return;
    }
    uint32_t w = (area->x2 - area->x1 + 1);
    uint32_t h = (area->y2 - area->y1 + 1);
    gGfx->draw16bitRGBBitmap(area->x1, area->y1, (uint16_t *)&color_p->full, w, h);
    lv_disp_flush_ready(disp);
}

void touch_read(lv_indev_drv_t * /*indev*/, lv_indev_data_t *data) {
    static uint8_t sFail = 0;
    static uint16_t sHoldX = 0, sHoldY = 0;
    static uint32_t sHoldAt = 0;
    if (sTpNeedRecover || millis() < sTpReadyAt) {
        data->state = LV_INDEV_STATE_REL;
        return;
    }
    Wire.beginTransmission(CST816_ADDR);
    Wire.write(0x02);
    /* STOP then read — repeated-start (false) wedges the ESP32 I2C FSM
       when CST816 NACKs, and that froze touch + keys + shake together. */
    if (Wire.endTransmission() != 0) {
        if (++sFail >= 8) {
            sFail = 0;
            sTpNeedRecover = true; /* do not delay() inside LVGL indev */
        }
        sHoldAt = 0;
        data->state = LV_INDEV_STATE_REL;
        return;
    }
    uint8_t buf[6] = {0};
    if (Wire.requestFrom((int)CST816_ADDR, 6) != 6) {
        if (++sFail >= 8) {
            sFail = 0;
            sTpNeedRecover = true;
        }
        sHoldAt = 0;
        data->state = LV_INDEV_STATE_REL;
        return;
    }
    sFail = 0;
    for (int i = 0; i < 6; i++) buf[i] = Wire.read();
    uint8_t points = buf[0] & 0x0F;
    if (gStatus.screen_off) {
        /* Swallow leftover contact from the blanking press (thumb on glass
           while holding PWR). Only a new touch after lift wakes. */
        if (points == 0) {
            sSwallowTouch = false;
            sSwallowAt = 0;
        } else if (!sSwallowTouch) {
            ui_note_activity();
        }
        sHoldAt = 0;
        data->state = LV_INDEV_STATE_REL;
        return;
    }
    if (points == 0) {
        sSwallowTouch = false;
        sSwallowAt = 0;
        sHoldAt = 0;
        data->state = LV_INDEV_STATE_REL;
        return;
    }
    if (sSwallowTouch && sSwallowAt && (millis() - sSwallowAt > 300)) {
        sSwallowTouch = false;
        sSwallowAt = 0;
    }
    if (sSwallowTouch) {
        data->state = LV_INDEV_STATE_REL;
        return;
    }
    uint16_t x = ((buf[1] & 0x0F) << 8) | buf[2];
    uint16_t y = ((buf[3] & 0x0F) << 8) | buf[4];
    if (x >= LCD_WIDTH) x = LCD_WIDTH - 1;
    if (y >= LCD_HEIGHT) y = LCD_HEIGHT - 1;
    if (gStatus.prone) imu_clear_prone();
    if (sHoldAt == 0) {
        sHoldAt = millis();
        sHoldX = x;
        sHoldY = y;
    } else {
        int dx = (int)x - (int)sHoldX;
        int dy = (int)y - (int)sHoldY;
        if (dx < 0) dx = -dx;
        if (dy < 0) dy = -dy;
        if (dx > 8 || dy > 8) {
            sHoldAt = millis();
            sHoldX = x;
            sHoldY = y;
        } else if (millis() - sHoldAt > 2500) {
            /* CST816 ghost contact: LVGL stayed PRESSED and ignored new taps. */
            data->state = LV_INDEV_STATE_REL;
            return;
        }
    }
    data->point.x = x;
    data->point.y = y;
    data->state = LV_INDEV_STATE_PR;
}

void battery_update() {
    int raw = analogRead(BAT_ADC_PIN);
    float v = (raw / 4095.0f) * 3.3f * BAT_VOLT_DIVIDER;
    int pct = (int)((v - 3.3f) / (4.2f - 3.3f) * 100.0f);
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    gStatus.battery_pct = pct;
    gStatus.charging = digitalRead(CHG_STAT_PIN) == LOW;
}
