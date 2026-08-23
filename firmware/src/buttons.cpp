#include "buttons.h"
#include "board.h"
#include "status.h"
#include "config.h"
#include "ui.h"
#include "hid_keys.h"
#include "display.h"
#include "voice.h"
#include "beep.h"
#include "imu.h"
#include <cstring>

struct Btn {
    int pin;
    bool down;
    bool long_fired;
    uint32_t t0;
    Btn(int p) : pin(p), down(false), long_fired(false), t0(0) {}
};

static Btn sBoot{BTN_BOOT_GPIO};
static Btn sPlus{BTN_PLUS_GPIO};
static Btn sPwr{BTN_PWR_GPIO};
static uint32_t sLastKeyAt = 0;
static bool sPlusWake = false;
static bool sBootWake = false;
static bool sPwrWake = false;
static bool sPwrBlanked = false;

uint32_t buttons_last_at() { return sLastKeyAt; }

static bool read_btn(int pin) { return digitalRead(pin) == LOW; }

void buttons_init() {
    pinMode(BTN_BOOT_GPIO, INPUT_PULLUP);
    pinMode(BTN_PLUS_GPIO, INPUT_PULLUP);
    pinMode(BTN_PWR_GPIO, INPUT_PULLUP);
}

void buttons_loop() {
    uint32_t now = millis();
    gStatus.key_busy = false;

    bool plus = read_btn(BTN_PLUS_GPIO);
    if (plus && !sPlus.down) {
        sPlus.down = true;
        sPlus.t0 = now;
        sLastKeyAt = now;
        gStatus.key_busy = true;
        bool asleep = gStatus.screen_off || ui_is_idle();
        ui_note_activity();
        if (asleep) {
            ui_force_wake();
            sPlusWake = true;
            if (gStatus.prone) imu_clear_prone();
            Serial.println("[KEY] plus wake");
        } else {
            sPlusWake = false;
            Serial.println("[KEY] plus down");
            beep_click();
            if (gStatus.prone) {
                imu_clear_prone();
                Serial.println("[KEY] plus unmute");
            }
            if (!strcmp(gCfg.voice_mode, "hid")) {
                gStatus.ptt = true;
                hid_ptt_down();
            } else if (voice_is_busy() && !voice_is_recording()) {
                Serial.println("[KEY] plus busy");
                ui_toast("WAIT");
            } else if (!voice_is_recording()) {
                voice_start(VOICE_SRC_HOLD);
            }
        }
        /* already recording (tap mic): hold PLUS to keep, release sends below */
    }
    if (plus && sPlus.down) gStatus.key_busy = true;
    if (!plus && sPlus.down) {
        uint32_t dt = now - sPlus.t0;
        sPlus.down = false;
        if (sPlusWake) {
            sPlusWake = false;
        } else if (!strcmp(gCfg.voice_mode, "hid")) {
            if (gStatus.ptt) {
                hid_ptt_up();
                gStatus.ptt = false;
            } else if (dt < 180) {
                hid_ptt_down();
                delay(40);
                hid_ptt_up();
            }
        } else if (voice_is_recording()) {
            if (dt < 280 && voice_source() == VOICE_SRC_HOLD) {
                voice_cancel();
                Serial.printf("[KEY] plus tap ignore dt=%u\n", (unsigned)dt);
            } else {
                Serial.printf("[KEY] plus send dt=%u src=%d\n", (unsigned)dt, (int)voice_source());
                voice_stop_and_send();
            }
        } else {
            Serial.printf("[KEY] plus up idle dt=%u\n", (unsigned)dt);
        }
    }

    // BOOT: Enter on press (not release). Always #ENTER host — BLE HID
    // isConnected() is a lie while the link flaps.
    bool boot = read_btn(BTN_BOOT_GPIO);
    if (boot && !sBoot.down) {
        sBoot.down = true;
        sBoot.long_fired = true;
        sBoot.t0 = now;
        sLastKeyAt = now;
        gStatus.key_busy = true;
        bool asleep = gStatus.screen_off || ui_is_idle();
        ui_note_activity();
        if (asleep) {
            ui_force_wake();
            sBootWake = true;
            if (gStatus.prone) imu_clear_prone();
            Serial.println("[KEY] boot wake");
        } else {
            sBootWake = false;
            if (gStatus.prone) imu_clear_prone();
            Serial.println("[KEY] boot down");
            if (!voice_is_recording()) {
                Serial.printf("[KEY] boot enter hid=%d\n", hid_connected() ? 1 : 0);
                strncpy(gStatus.agent_state, "working", sizeof(gStatus.agent_state) - 1);
                hid_tap_enter();
            }
        }
    }
    if (boot && sBoot.down) gStatus.key_busy = true;
    if (!boot && sBoot.down) {
        sBoot.down = false;
        sBoot.long_fired = false;
    }

    // PWR: rec = cancel. Running agent = Stop. Idle = refresh the four meters.
    bool pwr = read_btn(BTN_PWR_GPIO);
    if (pwr && !sPwr.down) {
        sPwr.down = true;
        sPwr.t0 = now;
        sLastKeyAt = now;
        gStatus.key_busy = true;
        bool asleep = gStatus.screen_off || ui_is_idle();
        ui_note_activity();
        sPwrWake = asleep;
        sPwrBlanked = false;
        if (asleep) ui_force_wake();
        if (gStatus.prone) imu_clear_prone();
        Serial.println(asleep ? "[KEY] pwr wake" : "[KEY] pwr down");
    }
    if (pwr && sPwr.down) gStatus.key_busy = true;
    /* Long-press blanks the panel. Deep-sleep while PWR is still held
       immediately wakes (ext0 = LOW), which is why the screen flashed. */
    if (pwr && sPwr.down && !sPwrBlanked && now - sPwr.t0 > 3000) {
        if (!voice_is_recording()) {
            sPwrBlanked = true;
            sPwrWake = true;
            display_blank();
            Serial.println("[KEY] pwr blank");
        }
    }
    if (!pwr && sPwr.down) {
        uint32_t dt = now - sPwr.t0;
        if (dt >= 25 && dt < 3000) {
            if (sPwrWake) {
                sPwrWake = false;
            } else if (voice_is_recording()) {
                Serial.printf("[KEY] pwr cancel dt=%u\n", (unsigned)dt);
                voice_cancel();
                ui_toast("canceled");
                beep_click();
            } else {
                beep_click();
                Serial.printf("[KEY] pwr dt=%u\n", (unsigned)dt);
                Serial.println("#PWR");
                strncpy(gStatus.agent_state, "idle", sizeof(gStatus.agent_state) - 1);
            }
        }
        sPwr.down = false;
    }
}
