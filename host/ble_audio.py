"""Receive Desk154 PTT audio over the already-paired BLE GATT connection."""
from __future__ import annotations

import asyncio
import struct
import threading
import time
from uuid import UUID

SVC = UUID("d5a10001-1540-4b45-9c01-6465736b3135")
CHAR_DATA = UUID("d5a10002-1540-4b45-9c01-6465736b3135")
CHAR_STATE = UUID("d5a10003-1540-4b45-9c01-6465736b3135")
DEFAULT_ADDR = 0x28848556EEE1

STEP = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107,
    118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,
    1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894,
    6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794,
    32767,
]
IDX_ADJ = [-1, -1, -1, -1, 2, 4, 6, 8]


def ima_decode(payload: bytes) -> bytes:
    pred = 0
    idx = 0
    out = bytearray()
    for b in payload:
        for nibble in (b & 0x0F, (b >> 4) & 0x0F):
            step = STEP[idx]
            delta = step >> 3
            if nibble & 4:
                delta += step
            if nibble & 2:
                delta += step >> 1
            if nibble & 1:
                delta += step >> 2
            if nibble & 8:
                pred -= delta
            else:
                pred += delta
            if pred > 32767:
                pred = 32767
            if pred < -32768:
                pred = -32768
            idx += IDX_ADJ[nibble & 7]
            if idx < 0:
                idx = 0
            if idx > 88:
                idx = 88
            out += struct.pack("<h", pred)
    return bytes(out)


def ima_encode(pcm: bytes) -> bytes:
    """IMA ADPCM matching firmware ble_audio.cpp. Two samples → one byte."""
    pred = 0
    idx = 0
    samples = list(struct.unpack("<%dh" % (len(pcm) // 2), pcm[: len(pcm) - (len(pcm) % 2)]))
    if len(samples) & 1:
        samples = samples[:-1]
    out = bytearray()

    def nibble(sample: int) -> int:
        nonlocal pred, idx
        step = STEP[idx]
        diff = int(sample) - pred
        n = 0
        if diff < 0:
            n = 8
            diff = -diff
        delta = step >> 3
        if diff >= step:
            n |= 4
            diff -= step
            delta += step
        step >>= 1
        if diff >= step:
            n |= 2
            diff -= step
            delta += step
        step >>= 1
        if diff >= step:
            n |= 1
            delta += step
        if n & 8:
            pred -= delta
        else:
            pred += delta
        if pred > 32767:
            pred = 32767
        if pred < -32768:
            pred = -32768
        idx += IDX_ADJ[n & 7]
        if idx < 0:
            idx = 0
        if idx > 88:
            idx = 88
        return n & 0x0F

    i = 0
    while i + 1 < len(samples):
        lo = nibble(samples[i])
        hi = nibble(samples[i + 1])
        out.append(lo | (hi << 4))
        i += 2
    return bytes(out)


def classify_notify(data: bytes) -> str:
    if not data:
        return "empty"
    tag = data[:4]
    if tag == b"STOP":
        return "stop"
    if tag == b"DAUD":
        return "daud" if len(data) >= 20 else "daud_short"
    if tag == b"DEND":
        return "dend"
    return "chunk"


def parse_daud(data: bytes) -> dict:
    if len(data) < 20 or data[:4] != b"DAUD":
        raise ValueError("not daud")
    sr, pcm_bytes, payload = struct.unpack_from("<III", data, 8)
    return {
        "ver": data[4],
        "codec": data[5],
        "ch": data[6],
        "flags": data[7],
        "sr": sr,
        "pcm": pcm_bytes,
        "payload": payload,
    }


def make_daud(pcm_bytes: int, payload: int, sr: int = 16000) -> bytes:
    return b"DAUD" + bytes([1, 2, 1, 0]) + struct.pack("<III", sr, pcm_bytes, payload)


_agent_to_write = {"v": "idle"}


def set_agent_state(state: str) -> None:
    s = (state or "idle").strip()[:15]
    if s not in ("idle", "working", "waiting", "done", "error"):
        s = "idle"
    _agent_to_write["v"] = s


def wav_wrap(pcm: bytes, sr: int = 16000) -> bytes:
    ch, bps = 1, 16
    byte_rate = sr * ch * bps // 8
    block = ch * bps // 8
    data_len = len(pcm)
    return b"".join(
        [
            b"RIFF",
            struct.pack("<I", 36 + data_len),
            b"WAVEfmt ",
            struct.pack("<IHHIIHH", 16, 1, ch, sr, byte_rate, block, bps),
            b"data",
            struct.pack("<I", data_len),
            pcm,
        ]
    )


def _ibuf_bytes(ibuf) -> bytes:
    if ibuf is None:
        return b""
    try:
        return bytes(ibuf)
    except Exception:
        pass
    from winrt.windows.storage.streams import DataReader

    reader = DataReader.from_buffer(ibuf)
    n = reader.unconsumed_buffer_length
    if not n:
        return b""
    buf = bytearray(n)
    reader.read_bytes(buf)
    return bytes(buf)


async def _subscribe_once(on_wav, on_stop=None) -> None:
    from winrt.windows.devices.bluetooth import BluetoothCacheMode, BluetoothLEDevice
    from winrt.windows.devices.bluetooth.genericattributeprofile import (
        GattClientCharacteristicConfigurationDescriptorValue,
        GattCommunicationStatus,
    )

    dev = await BluetoothLEDevice.from_bluetooth_address_async(DEFAULT_ADDR)
    if not dev:
        raise RuntimeError("desk154_not_found")
    pairing = dev.device_information.pairing
    if not pairing.is_paired:
        dev.close()
        raise RuntimeError("desk154_not_paired")

    from winrt.windows.devices.bluetooth.genericattributeprofile import GattSharingMode

    # Uncached full discovery throws E_UNEXPECTED while HID owns the link.
    # Open the advertised audio service as a shared session instead.
    result = await dev.get_gatt_services_for_uuid_with_cache_mode_async(SVC, BluetoothCacheMode.CACHED)
    if result.services.size == 0:
        result = await dev.get_gatt_services_for_uuid_with_cache_mode_async(SVC, BluetoothCacheMode.UNCACHED)
    svc = result.services[0] if result.services.size else None
    if svc is None:
        dev.close()
        raise RuntimeError("no_audio_service")
    opened = await svc.open_async(GattSharingMode.SHARED_READ_AND_WRITE)
    print("[ble] open", opened, "session", svc.session.session_status if svc.session else None)
    allc = await svc.get_characteristics_with_cache_mode_async(BluetoothCacheMode.CACHED)
    listed = []
    ch = None
    st_ch = None
    for c in allc.characteristics:
        listed.append(str(c.uuid).lower())
        if str(c.uuid).lower() == str(CHAR_DATA).lower():
            ch = c
        if str(c.uuid).lower() == str(CHAR_STATE).lower():
            st_ch = c
    if ch is None:
        allc = await svc.get_characteristics_with_cache_mode_async(BluetoothCacheMode.UNCACHED)
        for c in allc.characteristics:
            listed.append(str(c.uuid).lower())
            if str(c.uuid).lower() == str(CHAR_DATA).lower():
                ch = c
            if str(c.uuid).lower() == str(CHAR_STATE).lower():
                st_ch = c
    if ch is None:
        dev.close()
        raise RuntimeError("no_audio_char " + ",".join(listed[:12]))

    buf = bytearray()
    collecting = {"on": False, "pcm": 0, "payload": 0, "got": 0}

    def on_value(_sender, args):
        try:
            data = _ibuf_bytes(args.characteristic_value)
        except Exception as exc:
            print("[ble] notify decode", exc)
            return
        if data[:4] == b"STOP":
            print("[ble] STOP")
            if on_stop:
                threading.Thread(target=on_stop, daemon=True).start()
            return
        if data[:4] == b"DAUD" and len(data) >= 20:
            _ver, codec, _ch, _fl = data[4], data[5], data[6], data[7]
            sr, pcm_bytes, payload = struct.unpack_from("<III", data, 8)
            buf.clear()
            collecting.update(on=True, pcm=pcm_bytes, payload=payload, got=0, sr=sr, codec=codec)
            print("[ble] audio start codec=%s pcm=%s payload=%s" % (codec, pcm_bytes, payload))
            return
        if data[:4] == b"DEND":
            if not collecting["on"]:
                return
            collecting["on"] = False
            payload = bytes(buf)
            pcm = ima_decode(payload) if collecting.get("codec") == 2 else payload
            pcm = pcm[: collecting["pcm"] or len(pcm)]
            wav = wav_wrap(pcm, collecting.get("sr") or 16000)
            print("[ble] audio end wav=%s" % len(wav))
            try:
                on_wav(wav)
            except Exception as exc:
                print("[ble] asr fail", exc)
            buf.clear()
            return
        if collecting["on"]:
            buf.extend(data)

    token = ch.add_value_changed(on_value)
    status = await ch.write_client_characteristic_configuration_descriptor_async(
        GattClientCharacteristicConfigurationDescriptorValue.NOTIFY
    )
    if status != GattCommunicationStatus.SUCCESS:
        ch.remove_value_changed(token)
        dev.close()
        raise RuntimeError("notify_cccd %s" % status)
    print("[ble] gatt audio subscribed", dev.name)
    last_agent = ""
    try:
        while True:
            await asyncio.sleep(1)
            if not dev.device_information.pairing.is_paired:
                raise RuntimeError("unpaired")
            want = _agent_to_write.get("v") or ""
            if st_ch is not None and want and want != last_agent:
                try:
                    from winrt.windows.storage.streams import DataWriter

                    w = DataWriter()
                    w.write_bytes(bytearray(want.encode("ascii")))
                    status_w = await st_ch.write_value_async(w.detach_buffer())
                    last_agent = want
                    print("[ble] agent write", want, status_w)
                except Exception as exc:
                    print("[ble] agent write", exc)
    finally:
        try:
            ch.remove_value_changed(token)
        except Exception:
            pass
        try:
            dev.close()
        except Exception:
            pass


def watch_loop(on_wav, on_stop=None) -> None:
    while True:
        try:
            asyncio.run(_subscribe_once(on_wav, on_stop))
        except Exception as exc:
            print("[ble]", exc)
        time.sleep(5)


def start_thread(on_wav, on_stop=None) -> None:
    threading.Thread(target=watch_loop, args=(on_wav, on_stop), daemon=True).start()
