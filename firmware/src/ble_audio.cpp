#include "ble_audio.h"
#include "hid_keys.h"
#include "status.h"
#include <NimBLEDevice.h>
#include <Arduino.h>
#include <cstring>
#include <string>

static const char *kSvc = "d5a10001-1540-4b45-9c01-6465736b3135";
static const char *kData = "d5a10002-1540-4b45-9c01-6465736b3135";
static const char *kStat = "d5a10003-1540-4b45-9c01-6465736b3135";

static NimBLECharacteristic *sData = nullptr;
static NimBLECharacteristic *sStat = nullptr;

class StatCb : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic *c) override {
        if (!c) return;
        std::string v = c->getValue();
        if (v.size() < 3 || v.size() > 15) return;
        for (char ch : v) {
            if (ch < 32 || ch > 126) return;
        }
        if (v != "idle" && v != "working" && v != "waiting" && v != "done" && v != "error") return;
        strncpy(gStatus.agent_state, v.c_str(), sizeof(gStatus.agent_state) - 1);
        gStatus.agent_state[sizeof(gStatus.agent_state) - 1] = 0;
    }
};

static StatCb sStatCb;

static const int16_t kStep[89] = {
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107,
    118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,
    1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894,
    6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794,
    32767};
static const int kIdxAdj[8] = {-1, -1, -1, -1, 2, 4, 6, 8};

struct ImaState {
    int pred;
    int idx;
};

static uint8_t ima_nibble(ImaState *st, int16_t sample) {
    int step = kStep[st->idx];
    int diff = (int)sample - st->pred;
    uint8_t n = 0;
    if (diff < 0) {
        n = 8;
        diff = -diff;
    }
    int delta = step >> 3;
    if (diff >= step) {
        n |= 4;
        diff -= step;
        delta += step;
    }
    step >>= 1;
    if (diff >= step) {
        n |= 2;
        diff -= step;
        delta += step;
    }
    step >>= 1;
    if (diff >= step) {
        n |= 1;
        delta += step;
    }
    if (n & 8) st->pred -= delta;
    else st->pred += delta;
    if (st->pred > 32767) st->pred = 32767;
    if (st->pred < -32768) st->pred = -32768;
    st->idx += kIdxAdj[n & 7];
    if (st->idx < 0) st->idx = 0;
    if (st->idx > 88) st->idx = 88;
    return (uint8_t)(n & 0x0F);
}

static bool notify_raw(NimBLECharacteristic *ch, const uint8_t *p, size_t n) {
    if (!ch || !hid_connected()) return false;
    ch->setValue(p, n);
    ch->notify();
    delay(6);
    return true;
}

void ble_audio_init() {
    NimBLEDevice::setMTU(517);
    NimBLEServer *srv = NimBLEDevice::getServer();
    if (!srv) {
        Serial.println("[AUDIO] no BLE server");
        return;
    }
    NimBLEService *svc = srv->createService(kSvc);
    sData = svc->createCharacteristic(kData, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
    sStat = svc->createCharacteristic(
        kStat, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR | NIMBLE_PROPERTY::NOTIFY);
    if (sStat) sStat->setCallbacks(&sStatCb);
    uint8_t idle = 0;
    sStat->setValue(&idle, 1);
    bool ok = svc->start();
    NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
    if (adv) {
        adv->addServiceUUID(kSvc);
    }
    Serial.printf("[AUDIO] gatt start=%d data_h=%u stat_h=%u\n",
                  ok ? 1 : 0,
                  sData ? sData->getHandle() : 0,
                  sStat ? sStat->getHandle() : 0);
}

bool ble_audio_can_send() {
    return sData && hid_connected() && sData->getSubscribedCount() > 0;
}

bool ble_audio_send_pcm(const uint8_t *pcm, size_t nbytes) {
    if (!ble_audio_can_send() || !pcm || nbytes < 2000) return false;
    size_t ns = nbytes / 2;
    if (ns & 1) ns--;
    uint32_t payload = (uint32_t)(ns / 2);
    uint32_t sr = 16000;
    uint32_t pcm_bytes = (uint32_t)(ns * 2);
    uint8_t head[20];
    memcpy(head, "DAUD", 4);
    head[4] = 1;
    head[5] = 2;
    head[6] = 1;
    head[7] = 0;
    memcpy(head + 8, &sr, 4);
    memcpy(head + 12, &pcm_bytes, 4);
    memcpy(head + 16, &payload, 4);
    uint8_t st = 2;
    if (sStat) {
        sStat->setValue(&st, 1);
        sStat->notify();
    }
    if (!notify_raw(sData, head, sizeof(head))) return false;

    ImaState ima = {0, 0};
    const int16_t *s = (const int16_t *)pcm;
    uint8_t chunk[180];
    size_t off = 0;
    size_t i = 0;
    while (i + 1 < ns) {
        uint8_t lo = ima_nibble(&ima, s[i++]);
        uint8_t hi = ima_nibble(&ima, s[i++]);
        chunk[off++] = (uint8_t)(lo | (hi << 4));
        if (off >= sizeof(chunk)) {
            if (!notify_raw(sData, chunk, off)) return false;
            off = 0;
        }
    }
    if (off && !notify_raw(sData, chunk, off)) return false;
    if (!notify_raw(sData, (const uint8_t *)"DEND", 4)) return false;
    st = 3;
    if (sStat) {
        sStat->setValue(&st, 1);
        sStat->notify();
    }
    Serial.printf("[AUDIO] sent pcm=%u ima=%u\n", (unsigned)pcm_bytes, (unsigned)payload);
    st = 0;
    if (sStat) sStat->setValue(&st, 1);
    return true;
}

bool ble_audio_send_stop() {
    return notify_raw(sData, (const uint8_t *)"STOP", 4);
}
