#include "imu.h"
#include "board.h"
#include "voice.h"
#include "ui.h"
#include "status.h"
#include "beep.h"
#include "buttons.h"
#include "display.h"
#include <Wire.h>
#include <Arduino.h>
#include <cstring>

#define QMI_WHOAMI 0x00
#define QMI_CTRL1 0x02
#define QMI_CTRL2 0x03
#define QMI_CTRL7 0x08
#define QMI_AX_L 0x35
#define QMI_WHOAMI_VAL 0x05

static uint8_t sAddr = 0;
static bool sOk = false;
static int16_t sPx = 0, sPy = 0, sPz = 0;
static bool sHavePrev = false;
static uint32_t sLockUntil = 0;
static uint32_t sBootIgnore = 0;
static int sFaceAx = -1;
static int sFaceSign = 1;
static uint32_t sProneMs = 0;
static uint32_t sFaceUpMs = 0;
static uint32_t sKnockAt = 0;

static void qmi_write(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(sAddr);
    Wire.write(reg);
    Wire.write(val);
    Wire.endTransmission();
}

static uint8_t qmi_read(uint8_t addr, uint8_t reg) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    if (Wire.endTransmission() != 0) return 0xFF;
    if (Wire.requestFrom((int)addr, 1) != 1) return 0xFF;
    return (uint8_t)Wire.read();
}

static bool qmi_read_accel(int16_t *x, int16_t *y, int16_t *z) {
    Wire.beginTransmission(sAddr);
    Wire.write(QMI_AX_L);
    if (Wire.endTransmission() != 0) return false;
    if (Wire.requestFrom((int)sAddr, 6) != 6) return false;
    uint8_t b[6];
    for (int i = 0; i < 6; i++) b[i] = (uint8_t)Wire.read();
    *x = (int16_t)(b[0] | (b[1] << 8));
    *y = (int16_t)(b[2] | (b[3] << 8));
    *z = (int16_t)(b[4] | (b[5] << 8));
    return true;
}

void imu_init() {
    sBootIgnore = millis() + 2500;
    const uint8_t addrs[] = {0x6A, 0x6B};
    for (uint8_t a : addrs) {
        if (qmi_read(a, QMI_WHOAMI) == QMI_WHOAMI_VAL) {
            sAddr = a;
            break;
        }
    }
    if (!sAddr) {
        Serial.println("[IMU] not found");
        return;
    }
    qmi_write(QMI_CTRL1, 0x40);  // auto increment
    qmi_write(QMI_CTRL2, 0x05);  // accel 2g, ~100 Hz
    qmi_write(QMI_CTRL7, 0x01);  // enable accel
    sOk = true;
    Serial.printf("[IMU] qmi8658 0x%02X\n", sAddr);
}

bool imu_ok() { return sOk; }

static int16_t axis_at(int ax, int16_t x, int16_t y, int16_t z) {
    if (ax == 0) return x;
    if (ax == 1) return y;
    return z;
}

static void learn_face(int16_t x, int16_t y, int16_t z) {
    if (sFaceAx >= 0) return;
    int16_t v[3] = {x, y, z};
    int best = 0;
    int32_t a = abs((int32_t)v[0]);
    for (int i = 1; i < 3; i++) {
        int32_t b = abs((int32_t)v[i]);
        if (b > a) {
            a = b;
            best = i;
        }
    }
    if (a < 12000) return;
    sFaceAx = best;
    sFaceSign = v[best] >= 0 ? 1 : -1;
    Serial.printf("[IMU] face axis=%d sign=%d g=%d\n", sFaceAx, sFaceSign, (int)v[best]);
}

static void update_prone(int16_t x, int16_t y, int16_t z, uint32_t now) {
    if (sFaceAx < 0) return;
    int32_t face = (int32_t)axis_at(sFaceAx, x, y, z) * sFaceSign;
    static uint32_t last = 0;
    uint32_t dt = last ? now - last : 25;
    last = now;
    if (dt > 80) dt = 80;

    if (face < -9000) {
        sProneMs += dt;
        sFaceUpMs = 0;
    } else if (face > 8000) {
        sFaceUpMs += dt;
        sProneMs = 0;
    } else {
        sProneMs = 0;
        sFaceUpMs = 0;
    }

    if (!gStatus.prone && sProneMs >= 280) {
        gStatus.prone = true;
        gStatus.screen_off = false;
        sProneMs = 0;
        if (voice_is_recording()) voice_cancel();
        display_apply_presence();
        ui_toast("MUTE");
        Serial.println("[IMU] prone mute");
    } else if (gStatus.prone && sFaceUpMs >= 280) {
        gStatus.prone = false;
        gStatus.screen_off = false;
        sFaceUpMs = 0;
        display_apply_presence();
        ui_toast("ON");
        Serial.println("[IMU] face up");
    }
}

static void on_shake() {
    if (ui_is_idle()) return;
    if (ui_is_pack()) {
        if (gStatus.prone || gStatus.screen_off) return;
        ui_pack_press();
        return;
    }
    if (voice_is_recording()) {
        voice_cancel();
        ui_toast("CANCEL");
        Serial.println("[IMU] cancel rec");
        return;
    }
    if (!strcmp(gStatus.agent_state, "working") || !strcmp(gStatus.agent_state, "waiting")) {
        Serial.println("#STOP");
        strncpy(gStatus.agent_state, "idle", sizeof(gStatus.agent_state) - 1);
        ui_toast("STOP");
        beep_request(BEEP_STOP);
        Serial.println("[IMU] stop");
        return;
    }
    if (gStatus.prone) return;
    Serial.println("#UNDO");
    ui_toast("UNDO");
}

static void on_knock() {
}

void imu_loop() {
    if (!sOk) return;
    uint32_t now = millis();
    if (now < sBootIgnore) return;
    static uint32_t last = 0;
    if (now - last < 25) return;
    last = now;
    int16_t x, y, z;
    if (!qmi_read_accel(&x, &y, &z)) return;
    learn_face(x, y, z);
    update_prone(x, y, z, now);

    if (!sHavePrev) {
        sPx = x;
        sPy = y;
        sPz = z;
        sHavePrev = true;
        return;
    }
    int32_t dx = (int32_t)x - sPx;
    int32_t dy = (int32_t)y - sPy;
    int32_t dz = (int32_t)z - sPz;
    sPx = x;
    sPy = y;
    sPz = z;
    if (ui_is_idle()) return;
    if (now < sLockUntil) return;

    int32_t dmax = dx;
    if (abs(dy) > abs(dmax)) dmax = dy;
    if (abs(dz) > abs(dmax)) dmax = dz;

    static int sCross = 0;
    static int32_t sLastD = 0;
    static uint32_t sWin = 0;
    const int32_t kShake = 7000;
    const int32_t kKnock = 5200;

    if (now - sWin > 800) {
        sKnockAt = 0;
        sCross = 0;
        sWin = now;
        sLastD = 0;
    }

    bool keyish = gStatus.key_busy || (now - buttons_last_at() < 320);

    if (!keyish && abs(dmax) >= kKnock && !sKnockAt && sCross == 0) {
        bool alongFace = true;
        if (sFaceAx >= 0) {
            int32_t df = (sFaceAx == 0) ? dx : (sFaceAx == 1) ? dy : dz;
            alongFace = abs(df) >= (abs(dmax) * 6) / 10;
        }
        if (alongFace) sKnockAt = now;
    }

    if ((dmax > kShake && sLastD < -kShake / 2) || (dmax < -kShake && sLastD > kShake / 2)) {
        sCross++;
        sKnockAt = 0;
    }
    if (dmax > kShake || dmax < -kShake) sLastD = dmax;

    if (sKnockAt && sCross == 0 && now - sKnockAt >= 220 && abs(dmax) < 2200) {
        sKnockAt = 0;
        sLockUntil = now + 450;
        on_knock();
        return;
    }

    if (sCross < 2) return;
    sCross = 0;
    sKnockAt = 0;
    sLockUntil = now + 1200;
    on_shake();
}
