# -*- coding: utf-8 -*-
"""Desk154 USB pairing — find COM by MAC, push #CFG* bundle to device."""
from __future__ import annotations

import socket
import time
from typing import Iterable

import serial

DESK154_MAC = "28848556EEE0"
DEFAULT_HOST_PORT = 8787
DEFAULT_HOST_KEY = "desk-local"
CHUNK = 80
EXCLUDE_PORTS = frozenset({"COM4", "COM6"})


def normalize_mac(mac: str) -> str:
    return (mac or "").upper().replace(":", "").replace("-", "")


def find_desk_port(
    mac: str = DESK154_MAC,
    *,
    exclude: Iterable[str] | None = None,
    env_port: str | None = None,
) -> str | None:
    """Return COM port for Desk154 CDC/JTAG interface, or None."""
    if env_port:
        return env_port.strip() or None
    try:
        from serial.tools import list_ports
    except Exception:
        return None

    want = normalize_mac(mac)
    skip = {p.upper() for p in (exclude or EXCLUDE_PORTS)}
    matches = []
    for p in list_ports.comports():
        dev = (p.device or "").upper()
        if dev in skip:
            continue
        hwid = normalize_mac(p.hwid or "")
        ser = normalize_mac(p.serial_number or "")
        if want and (want in hwid or want in ser):
            matches.append(p)
    if not matches:
        return None
    # App CDC = SER 28848556EEE0. Download/JTAG = SER 28:84:85:56:EE:E0.
    # Prefer app port; if only download port exists, still return it (open with dtr=False).
    app = None
    for p in matches:
        sn = p.serial_number or ""
        if ":" not in sn and "-" not in sn:
            app = p.device
            break
    if app:
        return app
    return matches[0].device


def local_host_url(port: int = DEFAULT_HOST_PORT) -> str:
    """Best-effort LAN URL for the puck's host_url field."""
    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        pass
    return f"http://{ip}:{port}"


def wait_ready(ser: serial.Serial, timeout: float = 12) -> bool:
    t0 = time.time()
    serial_write(ser, b"#STATUS\n")
    buf = ""
    while time.time() - t0 < timeout:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting).decode("utf-8", "replace")
            if "cfg_ok=1" in buf or "Desk154" in buf or "ready" in buf.lower():
                return True
        else:
            time.sleep(0.2)
            serial_write(ser, b"#STATUS\n")
    return False


def send_line(ser: serial.Serial, line: str, expect: str = "[OK]") -> str:
    serial_write(ser, line + "\n")
    t0 = time.time()
    buf = ""
    while time.time() - t0 < 3:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting).decode("utf-8", "replace")
            if expect in buf:
                return buf
        time.sleep(0.05)
    raise RuntimeError("no ACK for %s got %r" % (line[:40], buf[:120]))


def build_config_lines(
    host_url: str,
    host_key: str = DEFAULT_HOST_KEY,
    *,
    ssid: str = "",
    password: str = "",
    extra_wifi: list[tuple[str, str]] | None = None,
) -> list[str]:
    lines = [
        "host_url=%s" % host_url,
        "host_key=%s" % host_key,
        "warn_threshold=70",
        "alert_threshold=90",
        "poll_interval_sec=60",
    ]
    if ssid:
        lines.append("wifi_ssid=%s" % ssid)
        lines.append("wifi_pass=%s" % password)
        lines.append("wifi_ssid=%s" % ssid)
        lines.append("wifi_pass=%s" % password)
    idx = 2
    for es, ep in extra_wifi or []:
        lines.append("wifi_ssid%d=%s" % (idx, es))
        lines.append("wifi_pass%d=%s" % (idx, ep))
        idx += 1
        if idx > 3:
            break
    return lines


def open_serial(port: str, baud: int = 115200) -> serial.Serial:
    """Open Desk154 USB-Serial/JTAG.

    Windows delivers *no RX* unless DTR is asserted. Keep DTR high and RTS
    low for the whole session. Do not pulse them — the esptool DTR/RTS
    dance re-enumerates COM8 and wedges this S3.
    """
    time.sleep(0.5)
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = baud
    ser.timeout = 1
    ser.dtr = True
    ser.rts = False
    ser.open()
    ser.dtr = True
    ser.rts = False
    time.sleep(0.4)
    return ser


def serial_write(ser: serial.Serial, data: bytes | str) -> None:
    """Write USB-Serial/JTAG without touching DTR/RTS."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    ser.write(data)
    ser.flush()


def push_config(
    port: str,
    host_url: str,
    host_key: str = DEFAULT_HOST_KEY,
    *,
    ssid: str = "",
    password: str = "",
    extra_wifi: list[tuple[str, str]] | None = None,
    baud: int = 115200,
    open_delay: float = 2.5,
    require_ready: bool = False,
) -> None:
    """Push full host + optional Wi-Fi bundle over USB CDC."""
    lines = build_config_lines(host_url, host_key, ssid=ssid, password=password, extra_wifi=extra_wifi)
    for ln in lines:
        if len(ln) > 100:
            raise ValueError("config line too long: %s" % ln[:40])

    ser = open_serial(port, baud)
    try:
        if require_ready and not wait_ready(ser):
            raise RuntimeError("device not ready on %s" % port)
        if not require_ready and not wait_ready(ser, timeout=4):
            pass  # best-effort; legacy write_config behaviour
        send_line(ser, "#CFGCLEAR")
        for ln in lines:
            send_line(ser, "#CFGLINE|" + ln)
        send_line(ser, "#CFGDONE")
    finally:
        ser.close()


def probe_status(port: str, baud: int = 115200) -> str:
    """Send #STATUS and return raw response (smoke test after pair)."""
    ser = open_serial(port, baud)
    try:
        time.sleep(0.5)
        serial_write(ser, b"#STATUS\n")
        t0 = time.time()
        buf = ""
        while time.time() - t0 < 3:
            if ser.in_waiting:
                buf += ser.read(ser.in_waiting).decode("utf-8", "replace")
            else:
                time.sleep(0.05)
        return buf
    finally:
        ser.close()


# Names used by the buyer wizard / write_config.py
find_desk_port = find_desk_port
push_config = push_config
probe_status = probe_status
