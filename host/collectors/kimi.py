"""Kimi Code 5h / 7d remaining → used percent. Refreshes local OAuth file."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from collectors.util import unix_ts, used_from_remaining

CRED = Path.home() / ".kimi-code" / "credentials" / "kimi-code.json"
USAGE_URL = "https://api.kimi.com/coding/v1/usages"
TOKEN_URL = "https://auth.kimi.com/api/oauth/token"
CLIENT_ID = "17e5f671-d194-4dfb-9706-5516cb48c098"


def parse_kimi_usage(payload: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(prev or {})
    weekly = payload.get("usage") or {}
    d7 = used_from_remaining(weekly.get("remaining") if isinstance(weekly, dict) else None)
    if d7 is None and isinstance(weekly, dict):
        d7 = used_from_remaining(weekly.get("remaining"))
    if isinstance(weekly, dict):
        used = weekly.get("used")
        limit = weekly.get("limit")
        if d7 is None and used is not None and limit not in (None, "", "0", 0):
            try:
                d7 = int(round(100.0 * float(used) / float(limit)))
            except (TypeError, ValueError, ZeroDivisionError):
                d7 = None
        rst = unix_ts(weekly.get("resetTime") or weekly.get("reset_time"))
        if rst:
            out["reset_d7"] = rst
    if d7 is not None:
        out["d7"] = max(0, min(100, d7))

    h5 = None
    for block in payload.get("limits") or []:
        if not isinstance(block, dict):
            continue
        win = block.get("window") or {}
        dur = win.get("duration")
        unit = str(win.get("timeUnit") or win.get("time_unit") or "")
        if dur != 300 and "MINUTE" not in unit.upper():
            continue
        if dur != 300:
            continue
        detail = block.get("detail") or block
        h5 = used_from_remaining(detail.get("remaining"))
        rst = unix_ts(detail.get("resetTime") or detail.get("reset_time"))
        if rst:
            out["reset_h5"] = rst
        break
    if h5 is not None:
        out["h5"] = max(0, min(100, h5))
    else:
        out.pop("h5", None)
        out.pop("reset_h5", None)
    if h5 is None and d7 is None:
        out["ok"] = False
        out["err"] = "parse"
        return out
    out["ok"] = True
    out["err"] = ""
    return out


def _load_cred() -> tuple[Path | None, dict[str, Any]]:
    for p in (
        CRED,
        Path.home() / ".kimi" / "credentials" / "kimi-code.json",
        Path(__file__).resolve().parent.parent / "secrets" / "kimi_token.txt",
    ):
        if not p.is_file():
            continue
        raw = p.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        if raw.startswith("{"):
            try:
                return p, json.loads(raw)
            except Exception:
                continue
        return p, {"access_token": raw, "refresh_token": ""}
    return None, {}


def _save_cred(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _refresh(path: Path, data: dict[str, Any]) -> str | None:
    rt = data.get("refresh_token") or ""
    if not rt:
        return None
    r = httpx.post(
        TOKEN_URL,
        data={"client_id": CLIENT_ID, "grant_type": "refresh_token", "refresh_token": rt},
        timeout=20.0,
    )
    if r.status_code >= 400:
        return None
    body = r.json()
    tok = body.get("access_token")
    if not tok:
        return None
    data["access_token"] = tok
    if body.get("refresh_token"):
        data["refresh_token"] = body["refresh_token"]
    data["token_type"] = body.get("token_type") or "Bearer"
    exp = int(body.get("expires_in") or 0)
    if exp:
        data["expires_in"] = exp
        data["expires_at"] = int(time.time()) + exp
    if body.get("scope"):
        data["scope"] = body["scope"]
    _save_cred(path, data)
    return tok


def fetch_kimi(prev: dict[str, Any] | None = None) -> dict[str, Any]:
    path, data = _load_cred()
    tok = data.get("access_token") if data else None
    if not tok:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "login"
        return out

    def pull(bearer: str) -> httpx.Response:
        return httpx.get(
            USAGE_URL,
            headers={"Authorization": f"Bearer {bearer}", "Accept": "application/json"},
            timeout=20.0,
        )

    try:
        r = pull(tok)
        if r.status_code == 401 and path:
            fresh = _refresh(path, data)
            if not fresh:
                out = dict(prev or {})
                out["ok"] = False
                out["err"] = "login"
                return out
            r = pull(fresh)
        if r.status_code == 401:
            out = dict(prev or {})
            out["ok"] = False
            out["err"] = "login"
            return out
        if r.status_code >= 400:
            out = dict(prev or {})
            out["ok"] = False
            out["err"] = "http"
            return out
        return parse_kimi_usage(r.json(), prev)
    except Exception:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "net"
        return out
