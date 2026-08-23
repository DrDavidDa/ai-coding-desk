#include "rgb.h"
#include "board.h"
#include "status.h"
#include <FastLED.h>
#include <cstring>

static CRGB sLeds[WS2812_COUNT];
static uint8_t sHue = 0;

enum RgbPri { PRI_ALERT = 0, PRI_PTT, PRI_AGENT, PRI_IDLE };

static RgbPri pick() {
    if (status_max_quota_percent() >= gAlertThreshold) return PRI_ALERT;
    if (gStatus.ptt) return PRI_PTT;
    if (strcmp(gStatus.agent_state, "idle") != 0) return PRI_AGENT;
    return PRI_IDLE;
}

void rgb_init() {
    FastLED.addLeds<WS2812B, WS2812_PIN, GRB>(sLeds, WS2812_COUNT);
    FastLED.setBrightness(48);
    fill_solid(sLeds, WS2812_COUNT, CRGB::Black);
    FastLED.show();
}

void rgb_loop() {
    if (gStatus.prone || gStatus.screen_off) {
        fill_solid(sLeds, WS2812_COUNT, CRGB::Black);
        FastLED.show();
        return;
    }
    RgbPri p = pick();
    uint32_t t = millis();
    switch (p) {
        case PRI_ALERT: {
            bool on = (t / 200) % 2;
            fill_solid(sLeds, WS2812_COUNT, on ? CRGB::Red : CRGB::Black);
            break;
        }
        case PRI_PTT: {
            sHue++;
            fill_rainbow(sLeds, WS2812_COUNT, sHue, 8);
            break;
        }
        case PRI_AGENT: {
            CRGB c = CRGB::White;
            if (!strcmp(gStatus.agent_state, "working")) c = CRGB(0x3B, 0x82, 0xF6);
            else if (!strcmp(gStatus.agent_state, "waiting")) {
                c = CRGB(0xF5, 0x9E, 0x0B);
                if ((t / 350) % 2) c = CRGB::Black;
            } else if (!strcmp(gStatus.agent_state, "error")) c = CRGB::Red;
            else if (!strcmp(gStatus.agent_state, "done")) c = CRGB(0x22, 0xC5, 0x5E);
            fill_solid(sLeds, WS2812_COUNT, c);
            break;
        }
        default: {
            uint8_t b = beatsin8(12, 20, 90);
            fill_solid(sLeds, WS2812_COUNT, CRGB(b, b, b));
            if (status_max_quota_percent() >= gWarnThreshold) {
                fill_solid(sLeds, WS2812_COUNT, CRGB(b, b / 2, 0));
            }
            break;
        }
    }
    FastLED.show();
}
