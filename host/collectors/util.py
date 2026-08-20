"""Shared quota parsing. Never logs secrets."""
from __future__ import annotations

import os
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


def pct(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n <= 1.5:
        n = n * 100.0
    n = int(round(n))
    if n < 0:
        return 0
    if n > 100:
        return 100
    return n


def used_from_remaining(v: Any) -> int | None:
    left = pct(v)
    if left is None:
        return None
    return 100 - left


def unix_ts(v: Any) -> int:
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        n = int(v)
        if n > 10_000_000_000:
            n //= 1000
        return n if n > 0 else 0
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return 0
        try:
            if s.isdigit():
                return unix_ts(int(s))
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            return 0
    return 0


def normalize_win_proxy(server: str | None) -> str | None:
    """Turn IE/WinINET ProxyServer into an httpx URL."""
    raw = (server or "").strip()
    if not raw:
        return None
    if "=" in raw:
        parts: dict[str, str] = {}
        for chunk in raw.split(";"):
            if "=" not in chunk:
                continue
            key, val = chunk.split("=", 1)
            parts[key.strip().lower()] = val.strip()
        raw = parts.get("https") or parts.get("http") or ""
    raw = raw.strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "http://" + raw
    return raw


def parse_clash_mixed_port(text: str) -> int | None:
    """Read Clash Verge mixed-port from a yaml snippet."""
    if not text:
        return None
    for pat in (r"(?m)^verge_mixed_port:\s*(\d+)", r"(?m)^mixed-port:\s*(\d+)"):
        m = re.search(pat, text)
        if not m:
            continue
        n = int(m.group(1))
        if 1 <= n <= 65535:
            return n
    return None


def _tcp_open(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def clash_config_paths() -> list[Path]:
    home = Path.home()
    roots = [
        home / "AppData" / "Roaming" / "io.github.clash-verge-rev.clash-verge-rev",
        home / ".config" / "clash-verge",
        home / ".config" / "clash",
    ]
    names = ("verge.yaml", "config.yaml", "clash-verge.yaml")
    out: list[Path] = []
    for root in roots:
        for name in names:
            out.append(root / name)
    return out


def clash_mixed_proxy() -> str | None:
    """Use Clash mixed-port even when system proxy / TUN are off."""
    port: int | None = None
    found_cfg = False
    for path in clash_config_paths():
        if not path.is_file():
            continue
        found_cfg = True
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        port = parse_clash_mixed_port(text)
        if port:
            break
    if port is None and found_cfg:
        port = 7897
    if port is None:
        return None
    if not _tcp_open("127.0.0.1", port):
        return None
    return f"http://127.0.0.1:{port}"


def win_ie_proxy() -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not int(enable):
                return None
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except OSError:
        return None
    return normalize_win_proxy(str(server) if server else None)


def system_proxy() -> str | None:
    """Env, Windows system proxy, then Clash Verge mixed-port if it is listening."""
    for key in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    ie = win_ie_proxy()
    if ie:
        return ie
    return clash_mixed_proxy()


def _is_transport_error(exc: BaseException) -> bool:
    kinds: tuple[type[BaseException], ...] = (httpx.TimeoutException, httpx.NetworkError)
    proxy_err = getattr(httpx, "ProxyError", None)
    if isinstance(proxy_err, type):
        kinds = kinds + (proxy_err,)
    return isinstance(exc, kinds)


def http_request(method: str, url: str, *, timeout: float = 20.0, **kwargs: Any) -> httpx.Response:
    """HTTP call that uses the local Clash/system proxy when ChatGPT.com is blocked."""
    proxy = system_proxy()
    attempts: list[str | None] = [proxy, None] if proxy else [None]
    last: BaseException | None = None
    for item in attempts:
        kw = dict(kwargs)
        kw["timeout"] = timeout
        if item:
            kw["proxy"] = item
        try:
            return httpx.request(method, url, **kw)
        except TypeError:
            if item and "proxy" in kw:
                kw.pop("proxy", None)
                kw["proxies"] = {"all://": item}
                try:
                    return httpx.request(method, url, **kw)
                except Exception as exc:
                    if _is_transport_error(exc):
                        last = exc
                        continue
                    raise
            raise
        except Exception as exc:
            if item is not None and _is_transport_error(exc):
                last = exc
                continue
            raise
    if last:
        raise last
    raise RuntimeError("http_request failed")
