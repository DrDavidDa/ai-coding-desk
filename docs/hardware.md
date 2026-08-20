# Waveshare ESP32-S3-Touch-LCD-1.54 pinout and RGB BOM

Board: SKU 33869. Pin map is the union of Clawdmeter `waveshare_lcd_154/board.h`,
xiaozhi-esp32 `esp32-s3-touch-lcd-1.54/config.h`, and the official schematic
(`ESP32-S3-LCD-1.54-Schematic.pdf`). USB serial uses native USB-JTAG/CDC, so
the UART pads are free for WS2812.

## Assigned GPIOs (do not reuse)

| Function | GPIO | Notes |
|---|---|---|
| LCD CS | 21 | ST7789 SPI |
| LCD SCLK | 38 | shared with TF CLK on some revs — do not bit-bang |
| LCD MOSI | 39 | |
| LCD DC | 45 | strapping; already used by panel |
| LCD RST | 40 | |
| LCD BL | 46 | LEDC PWM backlight |
| I2C SDA | 42 | touch + ES8311 + ES7210 + QMI8658 |
| I2C SCL | 41 | same bus |
| Touch INT | 48 | CST816 0x15 |
| Touch RST | 47 | |
| BAT_EN | 2 | must be HIGH early or battery browns out |
| BAT_ADC | 1 | VBAT divider 3.0x |
| CHG_STAT | 3 | charging flag |
| I2S MCLK | 8 | ES8311 / ES7210 |
| I2S BCLK | 9 | |
| I2S WS/LRCK | 10 | |
| I2S DIN (mic) | 11 | ES7210 → ESP32 |
| I2S DOUT (spk) | 12 | ESP32 → ES8311 |
| PA enable | 7 | NS4150B, HIGH = on |
| BOOT / confirm | 0 | KEY_MINUS, active-LOW |
| PLUS / PTT | 4 | KEY_PLUS, active-LOW |
| PWR / page | 5 | KEY_PWR, active-LOW |
| USB D- / D+ | 19 / 20 | native USB |

## WS2812 DIN (chosen)

**GPIO 43 (`ESP_TXD` UART pad)** — primary.

- Schematic brings `ESP_TXD` / `ESP_RXD` out as solder pads.
- Firmware uses USB CDC (`ARDUINO_USB_CDC_ON_BOOT=1`), so UART0 is unused.
- GPIO 43 is RMT-capable (FastLED).
- Do **not** hang WS2812 on the I2C pads (42/41): that bus already carries
  CST816 + codecs + IMU.

Fallback if 43 is noisy or needed for debug UART: **GPIO 44 (`ESP_RXD`)**.
Change `WS2812_PIN` in `firmware/src/board.h`.

## Wiring

```
ESP32 3V3  -- not used for 5V strip power
ESP32 GND  -- strip GND
GPIO43     -- 74AHCT125 or SN74HCT125 OE-enabled buffer DIN
5V from USB VBUS or a 5V pad -- strip VCC and buffer VCC
```

Level shift 3.3 V → 5 V is required for >5 LEDs or long wires. For a short
8-LED stick on the desk, a 330 Ω series resistor on DIN often works; still
prefer a HCT buffer.

## BOM

- WS2812B or SK6812 stick, 8–30 LEDs, 5 V
- 74AHCT125 / SN74HCT125 (or a ready-made 3.3→5 V WS2812 adapter)
- 330 Ω resistor on DIN
- 100–470 µF electrolytic across strip 5 V / GND
- 3-pin JST-SH or Dupont to the UART pad + GND + 5 V

## Power

Drive `BAT_EN` (GPIO 2) HIGH in `board_init()` before anything else. PWR
long-press 3 s releases it and deep-sleeps.
