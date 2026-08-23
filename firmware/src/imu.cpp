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

#define ORACLE_SHAKES 3
#define ORACLE_SHAKE_WIN_MS 3500

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
static uint8_t sOracleShakes = 0;
static uint32_t sOracleShakeAt = 0;

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
    int16_t v[3] = {x, y, z};
    int32_t ax[3] = {abs((int32_t)x), abs((int32_t)y), abs((int32_t)z)};
    int best = 0;
    if (ax[1] > ax[best]) best = 1;
    if (ax[2] > ax[best]) best = 2;
    if (ax[best] < 14000) return;
    int32_t others = ax[0] + ax[1] + ax[2] - ax[best];
    if (others > 8000) return; /* still tilted — don't lock a wrong axis */
    int sign = v[best] >= 0 ? 1 : -1;
    if (sFaceAx == best && sFaceSign == sign) return;
    sFaceAx = best;
    sFaceSign = sign;
    Serial.printf("[IMU] face axis=%d sign=%d g=%d\n", sFaceAx, sFaceSign, (int)v[best]);
}

void imu_clear_prone() {
    sProneMs = 0;
    sFaceUpMs = 0;
    if (!gStatus.prone) return;
    gStatus.prone = false;
    gStatus.screen_off = false;
    display_apply_presence();
    Serial.println("[IMU] prone cleared");
}

static void update_prone(int16_t x, int16_t y, int16_t z, uint32_t now) {
    if (sFaceAx < 0) return;
    int32_t face = (int32_t)axis_at(sFaceAx, x, y, z) * sFaceSign;
    static uint32_t last = 0;
    uint32_t dt = last ? now - last : 25;
    last = now;
    if (dt > 80) dt = 80;

    if (face < -12000) {
        sProneMs += dt;
        sFaceUpMs = 0;
    } else if (face > 8000) {
        sFaceUpMs += dt;
        sProneMs = 0;
    } else {
        sProneMs = 0;
        sFaceUpMs = 0;
    }

    if (!gStatus.prone && sProneMs >= 1500) {
        gStatus.prone = true;
        gStatus.screen_off = false;
        sProneMs = 0;
        if (voice_is_recording()) voice_cancel();
        display_apply_presence();
        ui_toast("MUTE");
        Serial.println("[IMU] prone mute");
    } else if (gStatus.prone && sFaceUpMs >= 400) {
        gStatus.prone = false;
        gStatus.screen_off = false;
        sFaceUpMs = 0;
        display_apply_presence();
        ui_toast("ON");
        Serial.println("[IMU] face up");
    }
}

static void on_shake() {
    uint32_t now = millis();
    if (gStatus.screen_off) return;
    /* Oracle only on the quota page — pocket shakes on DESK/idle must not
       beep or draw lots. Overlay redraw is allowed while a lot is showing. */
    if (!ui_is_usage() && !ui_oracle_visible()) return;
    if (gStatus.prone) imu_clear_prone();
    if (ui_is_idle()) ui_force_wake();
    if (voice_is_recording()) {
        voice_cancel();
        ui_toast("CANCEL");
        Serial.println("[IMU] cancel rec");
        return;
    }
    if (ui_is_pack()) return;
    /* 3 shakes always draw a lot. #STOP used to run on the first shake after
       发送 left agent_state=working, so oracle never opened. */
    if (ui_oracle_visible()) {
        ui_pack_oracle();
        return;
    }
    if (now - sOracleShakeAt > ORACLE_SHAKE_WIN_MS) {
        if (sOracleShakes == 1) {
            Serial.println("#UNDO");
            ui_toast("UNDO");
        }
        sOracleShakes = 0;
    }
    sOracleShakeAt = now;
    sOracleShakes++;
    Serial.printf("[IMU] shake %u/%u\n", (unsigned)sOracleShakes, (unsigned)ORACLE_SHAKES);
    if (sOracleShakes >= ORACLE_SHAKES) {
        sOracleShakes = 0;
        ui_pack_oracle();
        Serial.println("[IMU] oracle");
    }
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
    static uint8_t sImuFail = 0;
    if (!qmi_read_accel(&x, &y, &z)) {
        if (++sImuFail >= 20) {
            sImuFail = 0;
            Wire.end();
            display_wire_begin();
            Serial.println("[IMU] wire reset");
        }
        return;
    }
    sImuFail = 0;
    learn_face(x, y, z);

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
    if (abs(dx) + abs(dy) + abs(dz) < 4000) update_prone(x, y, z, now);
    if (now < sLockUntil) return;

    int32_t dmax = dx;
    if (abs(dy) > abs(dmax)) dmax = dy;
    if (abs(dz) > abs(dmax)) dmax = dz;

    static int sCross = 0;
    static int32_t sLastD = 0;
    static uint32_t sWin = 0;
    const int32_t kShake = 4500;
    const int32_t kKnock = 4000;

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
    sLockUntil = now + 700;
    on_shake();
}
