# -*- coding: utf-8 -*-
"""First-run pairing wizard (dev CLI). Phase 2 will wrap this in Desk154Setup.exe."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desk_pair import (  # noqa: E402
    DEFAULT_HOST_KEY,
    DESK154_MAC,
    find_desk_port,
    local_host_url,
    probe_status,
    push_config,
)


def load_wifi_extra(path: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not path.is_file():
        return out
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or "=" not in ln:
            continue
        es, ep = ln.split("=", 1)
        out.append((es.strip(), ep.strip()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Desk154 USB pairing wizard")
    ap.add_argument("--port", help="COM port (auto-detect Desk154 MAC if omitted)")
    ap.add_argument("--mac", default=DESK154_MAC, help="Expected device MAC (no colons)")
    ap.add_argument("--host-url", help="Override host URL (default: LAN IP :8787)")
    ap.add_argument("--host-key", default=os.environ.get("DESK_HOST_KEY", DEFAULT_HOST_KEY))
    ap.add_argument("--ssid", default="")
    ap.add_argument("--pass", dest="password", default="")
    ap.add_argument("--no-push", action="store_true", help="Detect only, do not push config")
    ap.add_argument("--probe", action="store_true", help="Send #STATUS after push")
    args = ap.parse_args()

    port = args.port or find_desk_port(args.mac, env_port=os.environ.get("DESK_SERIAL"))
    if not port:
        print("[FAIL] Desk154 not found (MAC %s). Plug USB and retry." % args.mac)
        print("       Known ports:")
        try:
            from serial.tools import list_ports

            for p in list_ports.comports():
                print("         %s  %s" % (p.device, p.hwid or p.description))
        except Exception:
            pass
        return 1

    host_url = args.host_url or local_host_url()
    print("[OK] port=%s  host_url=%s" % (port, host_url))

    if args.no_push:
        return 0

    extra = load_wifi_extra(ROOT / "wifi_extra.txt")
    try:
        push_config(
            port,
            host_url,
            args.host_key,
            ssid=args.ssid,
            password=args.password,
            extra_wifi=extra,
            require_ready=False,
        )
    except Exception as exc:
        print("[FAIL] push:", exc)
        return 1

    print("[OK] config pushed (#CFGDONE)")

    if args.probe:
        raw = probe_status(port)
        if "host_url=" in raw or "wifi=" in raw or "Desk154" in raw:
            print("[OK] probe response (%d bytes)" % len(raw))
        else:
            print("[WARN] probe empty or unexpected:", raw[:200])

    print("")
    print("Next: start host  py -3 desk_host.py")
    print("       Settings PC row should show OK after poll.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
