#include "hid_keys.h"
#include "ble_audio.h"
#include "beep.h"
#include "config.h"
#include <BleKeyboard.h>
#include <NimBLEDevice.h>

class DeskKeyboard : public BleKeyboard {
public:
    DeskKeyboard() : BleKeyboard("Desk154", "Waveshare", 100) {}
protected:
    void onStarted(BLEServer * /*pServer*/) override {
        // Must register GATT audio before advertising. If Windows reconnects
        // first, NimBLE refuses to reset the attribute table.
        ble_audio_init();
    }
};

static DeskKeyboard sKbd;
static bool sPttHeld = false;

void hid_init() {
    sKbd.begin();
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);
    // Windows HID needs Just Works bonding. BleKeyboard defaults to MITM+SC
    // (PIN wait). The previous override disabled bonding entirely, so Settings
    // sat on "Connecting...".
    NimBLEDevice::setSecurityIOCap(BLE_HS_IO_NO_INPUT_OUTPUT);
    NimBLEDevice::setSecurityAuth(true, false, false);
    NimBLEDevice::setSecurityInitKey(0x03);  // ENC | ID
    NimBLEDevice::setSecurityRespKey(0x03);
    Preferences p;
    p.begin("desk154", false);
    if (p.getUChar("hid_sec", 0) != 2) {
        NimBLEDevice::deleteAllBonds();
        p.putUChar("hid_sec", 2);
        Serial.println("[HID] cleared old bonds");
    }
    p.end();
    NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
    if (adv) {
        adv->stop();
        adv->setName("Desk154");
        adv->setAppearance(0x03C1);
        adv->setScanResponse(true);
        adv->addTxPower();
        adv->setMinInterval(0x20);
        adv->setMaxInterval(0x30);
        bool ok = adv->start();
        Serial.printf("[HID] init=%d adv_start=%d\n", NimBLEDevice::getInitialized(), ok);
    } else {
        Serial.println("[HID] no advertising object");
    }
}

bool hid_advertising() {
    NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
    return adv && adv->isAdvertising();
}

void hid_loop() {
    static uint32_t last = 0;
    if (millis() - last < 5000) return;
    last = millis();
    NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
    bool ad = adv && adv->isAdvertising();
    Serial.printf("[HID] conn=%d adv=%d\n", sKbd.isConnected() ? 1 : 0, ad ? 1 : 0);
    if (!sKbd.isConnected() && adv && !ad) {
        adv->start();
        Serial.println("[HID] restart adv");
    }
}

bool hid_connected() { return sKbd.isConnected(); }

void hid_ptt_down() {
    if (!sKbd.isConnected() || sPttHeld) return;
    sKbd.press(' ');
    sPttHeld = true;
}

void hid_ptt_up() {
    if (!sPttHeld) return;
    sKbd.release(' ');
    sPttHeld = false;
}

void hid_tap_enter() {
    // BLE HID conn flaps; Windows drops those Returns. Host SendInput is the
    // path that actually lands in Cursor (see #ENTER host in serial logs).
    Serial.println("#ENTER host");
}

void hid_tap_esc() {
    static uint32_t last = 0;
    uint32_t now = millis();
    if (now - last < 250) return;
    last = now;
    // USB #STOP only. BLE HID chords hit whichever window Windows
    // is showing, so idle PWR was typing into WeChat/Chrome.
    Serial.println("#STOP");
    ble_audio_send_stop();
    Serial.println("[HID] stop");
}

void hid_tap_n() {
    if (!sKbd.isConnected()) return;
    sKbd.write('n');
}

void hid_shift_tab() {
    if (!sKbd.isConnected()) return;
    sKbd.press(KEY_LEFT_SHIFT);
    sKbd.press(KEY_TAB);
    delay(40);
    sKbd.releaseAll();
}
