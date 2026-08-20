"""ChatGPT / Codex CLI usage via chatgpt.com/backend-api/wham/usage."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from collectors.util import http_request, pct, unix_ts

AUTH = Path.home() / ".codex" / "auth.json"
USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
TOKEN_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"


def _auth_data() -> dict[str, Any]:
    if not AUTH.is_file():
        return {}
    try:
        return json.loads(AUTH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _tok_acct(data: dict[str, Any]) -> tuple[str | None, str | None]:
    toks = data.get("tokens") if isinstance(data.get("tokens"), dict) else {}
    tok = data.get("access_token") or toks.get("access_token")
    acct = data.get("account_id") or toks.get("account_id")
    return tok, acct


def _window_secs(block: dict[str, Any]) -> int:
    for key in ("limit_window_seconds", "window_seconds", "duration_seconds"):
        val = block.get(key)
        if val in (None, ""):
            continue
        try:
            return int(val)
        except (TypeError, ValueError):
            continue
    return 0


def _kind(block: dict[str, Any], fallback: str) -> str:
    secs = _window_secs(block)
    if secs <= 0:
        return fallback
    if secs <= 8 * 3600:
        return "h5"
    return "d7"


def parse_codex_usage(payload: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(prev or {})
    rl = payload.get("rate_limits") or payload.get("rateLimits") or payload.get("rate_limit") or {}
    if not isinstance(rl, dict):
        rl = {}

    def util(block: Any) -> int | None:
        if not isinstance(block, dict):
            return None
        n = pct(block.get("used_percent") or block.get("util") or block.get("utilization"))
        if n is not None:
            return n
        used = block.get("used")
        limit = block.get("limit")
        if used is not None and limit:
            try:
                return pct(100.0 * float(used) / float(limit))
            except (TypeError, ValueError, ZeroDivisionError):
                return None
        return None

    windows: list[tuple[str, dict[str, Any]]] = []
    primary = rl.get("primary_window") or rl.get("five_hour") or payload.get("five_hour")
    secondary = rl.get("secondary_window") or rl.get("seven_day") or payload.get("seven_day")
    if isinstance(primary, dict):
        windows.append((_kind(primary, "h5"), primary))
    if isinstance(secondary, dict):
        windows.append((_kind(secondary, "d7"), secondary))
    extra = payload.get("additional_rate_limits") or rl.get("additional_rate_limits")
    if isinstance(extra, list):
        for block in extra:
            if isinstance(block, dict):
                windows.append((_kind(block, "d7"), block))

    found_h5 = False
    found_d7 = False
    for kind, block in windows:
        used = util(block)
        if used is not None:
            out[kind] = used
            if kind == "h5":
                found_h5 = True
            else:
                found_d7 = True
        rst = unix_ts(block.get("reset_at") or block.get("resets_at") or block.get("reset_after"))
        if rst:
            out["reset_h5" if kind == "h5" else "reset_d7"] = rst

    if not found_h5 and not found_d7:
        out["ok"] = False
        out["err"] = "parse"
        return out
    if not found_h5:
        out.pop("h5", None)
        out.pop("reset_h5", None)
    if not found_d7:
        out.pop("d7", None)
        out.pop("reset_d7", None)
    out["ok"] = True
    out["err"] = ""
    return out


def _refresh(data: dict[str, Any]) -> str | None:
    toks = data.get("tokens") if isinstance(data.get("tokens"), dict) else {}
    rt = data.get("refresh_token") or toks.get("refresh_token")
    if not rt:
        return None
    try:
        r = http_request(
            "POST",
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": rt,
                "client_id": CLIENT_ID,
            },
            timeout=20.0,
        )
        if r.status_code >= 400:
            return None
        body = r.json()
        tok = body.get("access_token")
        if not tok:
            return None
        if "tokens" not in data or not isinstance(data["tokens"], dict):
            data["tokens"] = {}
        data["tokens"]["access_token"] = tok
        if body.get("refresh_token"):
            data["tokens"]["refresh_token"] = body["refresh_token"]
        AUTH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return tok
    except Exception:
        return None


def fetch_codex(prev: dict[str, Any] | None = None) -> dict[str, Any]:
    data = _auth_data()
    tok, acct = _tok_acct(data)
    if not tok:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "login"
        return out

    def pull(bearer: str):
        headers = {
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
            "Origin": "https://chatgpt.com",
            "Referer": "https://chatgpt.com/",
            "User-Agent": "Mozilla/5.0",
        }
        if acct:
            headers["ChatGPT-Account-Id"] = str(acct)
        return http_request("GET", USAGE_URL, headers=headers, timeout=25.0)

    try:
        r = pull(tok)
        if r.status_code == 401:
            fresh = _refresh(data)
            if fresh:
                r = pull(fresh)
        if r.status_code == 401:
            out = dict(prev or {})
            out["ok"] = False
            out["err"] = "login"
            return out
        r.raise_for_status()
        return parse_codex_usage(r.json(), prev)
    except Exception:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "net"
        return out
