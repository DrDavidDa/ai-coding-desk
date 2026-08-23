# -*- coding: utf-8 -*-
"""USB CDC config push — Desk154 #CFG* protocol (chunk + ACK). No GLM token on device."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desk_pair import find_desk_port, push_config  # noqa: E402


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", help="COM port (auto-detect if omitted)")
    ap.add_argument("--host-url", default="http://192.168.1.10:8787")
    ap.add_argument("--host-key", default="desk-local")
    ap.add_argument("--ssid", default="")
    ap.add_argument("--pass", dest="password", default="")
    args = ap.parse_args()

    port = args.port or find_desk_port(env_port=os.environ.get("DESK_SERIAL"))
    if not port:
        print("[FAIL] no Desk154 COM port found")
        sys.exit(1)

    extra = load_wifi_extra(ROOT / "wifi_extra.txt")
    try:
        push_config(
            port,
            args.host_url,
            args.host_key,
            ssid=args.ssid,
            password=args.password,
            extra_wifi=extra,
        )
    except Exception as exc:
        print("[FAIL]", exc)
        sys.exit(1)
    print("[OK] config pushed on %s" % port)


if __name__ == "__main__":
    main()
