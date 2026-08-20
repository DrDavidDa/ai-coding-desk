#pragma once

// Waveshare ESP32-S3-Touch-LCD-1.54 — Clawdmeter + xiaozhi + schematic.

#define BOARD_NAME "Waveshare LCD 1.54"

#define LCD_WIDTH 240
#define LCD_HEIGHT 240
#define LCD_CS 21
#define LCD_SCLK 38
#define LCD_MOSI 39
#define LCD_DC 45
#define LCD_RST 40
#define LCD_BL 46

#define IIC_SDA 42
#define IIC_SCL 41

#define TP_INT 48
#define TP_RST 47
#define CST816_ADDR 0x15

#define BAT_EN 2
#define BAT_ADC_PIN 1
#define BAT_VOLT_DIVIDER 3.0f
#define CHG_STAT_PIN 3

#define SND_I2S_MCLK 8
#define SND_I2S_BCLK 9
#define SND_I2S_WS 10
#define SND_I2S_DOUT 12
#define SND_I2S_DIN 11
#define SND_PA_PIN 7

#define BTN_BOOT_GPIO 0   // tap=Enter; hold does nothing (download strap)
#define BTN_PLUS_GPIO 4   // hold-to-talk; release injects text (no Enter)
#define BTN_PWR_GPIO 5    // tap=Stop / cancel rec; 3s=sleep

// UART TX pad. USB CDC is the console, so GPIO43 is free for RMT/WS2812.
#define WS2812_PIN 43
#define WS2812_COUNT 16
#define WS2812_FALLBACK_PIN 44

#define SERIAL_LINE_MAX 1024
#define CFG_TOK_CHUNK 80
#define WARN_THRESHOLD_DEFAULT 70
#define ALERT_THRESHOLD_DEFAULT 90
