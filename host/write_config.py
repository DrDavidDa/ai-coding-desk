# -*- coding: utf-8 -*-
"""USB CDC config push — PaperColor #CFG* protocol (chunk + ACK). No GLM token on device."""
import argparse
import os
import sys
import time

import serial

CHUNK = 80


def wait_ready(ser, timeout=12):
    t0 = time.time()
    ser.write(b"#STATUS\n")
    buf = ""
    while time.time() - t0 < timeout:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting).decode("utf-8", "replace")
            if "cfg_ok=1" in buf or "Desk154" in buf or "ready" in buf.lower():
                return True
        else:
            time.sleep(0.2)
            ser.write(b"#STATUS\n")
    return False


def send_line(ser, line, expect="[OK]"):
    ser.write((line + "\n").encode("utf-8"))
    t0 = time.time()
    buf = ""
    while time.time() - t0 < 3:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting).decode("utf-8", "replace")
            if expect in buf:
                return buf
        time.sleep(0.05)
    raise RuntimeError("no ACK for %s got %r" % (line[:40], buf[:120]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--host-url", default="http://192.168.1.10:8787")
    ap.add_argument("--host-key", default="desk-local")
    ap.add_argument("--ssid", default="")
    ap.add_argument("--pass", dest="password", default="")
    args = ap.parse_args()

    ser = serial.Serial(args.port, 115200, timeout=1, dsrdtr=True)
    time.sleep(2.5)
    if not wait_ready(ser):
        print("[WARN] device not ready, sending anyway")
    send_line(ser, "#CFGCLEAR")
    lines = [
        "host_url=%s" % args.host_url,
        "host_key=%s" % args.host_key,
        "warn_threshold=70",
        "alert_threshold=90",
        "poll_interval_sec=60",
    ]
    if args.ssid:
        lines.append("wifi_ssid=%s" % args.ssid)
        lines.append("wifi_pass=%s" % args.password)
    extra = os.path.join(os.path.dirname(__file__), "wifi_extra.txt")
    idx = 2
    if os.path.isfile(extra):
        for ln in open(extra, encoding="utf-8"):
            ln = ln.strip()
            if not ln or "=" not in ln:
                continue
            es, ep = ln.split("=", 1)
            lines.append("wifi_ssid%d=%s" % (idx, es.strip()))
            lines.append("wifi_pass%d=%s" % (idx, ep.strip()))
            idx += 1
            if idx > 3:
                break
    for ln in lines:
        if len(ln) > 100:
            print("[FAIL] line too long", ln[:40])
            sys.exit(1)
        send_line(ser, "#CFGLINE|" + ln)
    send_line(ser, "#CFGDONE")
    print("[OK] config pushed")
    ser.close()


if __name__ == "__main__":
    main()
