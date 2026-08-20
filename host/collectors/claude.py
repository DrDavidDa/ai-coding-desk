"""Claude Code OAuth usage (5h / 7d)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from collectors.util import http_request, pct, unix_ts

CRED = Path.home() / ".claude" / ".credentials.json"
SETTINGS = Path.home() / ".claude" / "settings.json"
SETTINGS_LOCAL = Path.home() / ".claude" / "settings.local.json"
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
DEEPSEEK_BALANCE_URL = "https://api.deepseek.com/user/balance"
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
BETA = "oauth-2025-04-20"


def _claude_ua() -> str:
    candidates = [
        Path.home() / "AppData" / "Roaming" / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "package.json",
        Path.home() / ".npm-global" / "lib" / "node_modules" / "@anthropic-ai" / "claude-code" / "package.json",
    ]
    for path in candidates:
        try:
            ver = json.loads(path.read_text(encoding="utf-8")).get("version")
        except Exception:
            continue
        if ver:
            return f"claude-code/{ver}"
    return "claude-code/2.1.227"


def _load_cred() -> dict[str, Any]:
    if not CRED.is_file():
        return {}
    try:
        data = json.loads(CRED.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _oauth(data: dict[str, Any] | None = None) -> dict[str, Any]:
    blob = data if data is not None else _load_cred()
    oauth = blob.get("claudeAiOauth") or blob.get("oauth") or {}
    return oauth if isinstance(oauth, dict) else {}


def _token(data: dict[str, Any] | None = None) -> str | None:
    oauth = _oauth(data)
    tok = oauth.get("accessToken") or (data or {}).get("accessToken")
    return str(tok) if tok else None


def _expires_unix(oauth: dict[str, Any]) -> int:
    raw = oauth.get("expiresAt") or 0
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 0
    if n > 10_000_000_000:
        n //= 1000
    return n if n > 0 else 0


def _token_expired(oauth: dict[str, Any], skew: int = 60) -> bool:
    exp = _expires_unix(oauth)
    if not exp:
        return False
    return exp <= int(time.time()) + skew


def _save_oauth_tokens(access: str, refresh: str | None, expires_in: int) -> None:
    data = _load_cred()
    if not data:
        return
    oauth = dict(_oauth(data))
    oauth["accessToken"] = access
    if refresh:
        oauth["refreshToken"] = refresh
    old = oauth.get("expiresAt") or 0
    try:
        old_n = int(old)
    except (TypeError, ValueError):
        old_n = 0
    ttl = int(expires_in) if expires_in else 28800
    if ttl < 60:
        ttl = 28800
    if old_n > 10_000_000_000 or old_n == 0:
        oauth["expiresAt"] = int(time.time() * 1000) + ttl * 1000
    else:
        oauth["expiresAt"] = int(time.time()) + ttl
    data["claudeAiOauth"] = oauth
    tmp = CRED.with_name(".credentials.json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, CRED)


def _refresh() -> str | None:
    data = _load_cred()
    oauth = _oauth(data)
    rt = oauth.get("refreshToken")
    if not rt:
        return None
    try:
        r = http_request(
            "POST",
            TOKEN_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "anthropic-beta": BETA,
                "User-Agent": _claude_ua(),
            },
            json={
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
        _save_oauth_tokens(str(tok), body.get("refresh_token"), int(body.get("expires_in") or 0))
        return str(tok)
    except Exception:
        return None


def _headers(tok: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
        "anthropic-beta": BETA,
        "User-Agent": _claude_ua(),
    }


def _pct_first(*vals: Any) -> int | None:
    for v in vals:
        if v is None or v == "":
            continue
        n = pct(v)
        if n is not None:
            return n
    return None


def _settings_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in (SETTINGS, SETTINGS_LOCAL):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        env = data.get("env") if isinstance(data, dict) else None
        if not isinstance(env, dict):
            continue
        for key, val in env.items():
            if val is None:
                continue
            out[str(key)] = str(val)
    return out


def _deepseek_mode(env: dict[str, str] | None = None) -> bool:
    blob = env if env is not None else _settings_env()
    base = (blob.get("ANTHROPIC_BASE_URL") or "").lower()
    prov = (blob.get("CLAUDE_API_PROVIDER") or "").lower()
    return "deepseek.com" in base or prov.startswith("deepseek")


def parse_deepseek_balance(payload: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(prev or {})
    infos = payload.get("balance_infos") or []
    picked: dict[str, Any] | None = None
    for info in infos:
        if not isinstance(info, dict):
            continue
        if str(info.get("currency") or "").upper() == "CNY":
            picked = info
            break
        if picked is None:
            picked = info
    if not isinstance(picked, dict):
        out["ok"] = False
        out["err"] = "parse"
        return out
    try:
        yuan = float(picked.get("total_balance"))
    except (TypeError, ValueError):
        out["ok"] = False
        out["err"] = "parse"
        return out
    out.pop("h5", None)
    out.pop("d7", None)
    out.pop("reset_h5", None)
    out.pop("reset_d7", None)
    out["daily_tokens"] = int(round(yuan * 100.0))
    out["ok"] = True
    out["err"] = ""
    out["source"] = "deepseek"
    return out


def _fetch_deepseek(prev: dict[str, Any] | None = None) -> dict[str, Any]:
    env = _settings_env()
    if not _deepseek_mode(env):
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "login"
        return out
    key = env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN") or ""
    if not key:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "login"
        return out
    try:
        r = http_request(
            "GET",
            DEEPSEEK_BALANCE_URL,
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            timeout=20.0,
        )
        if r.status_code in (401, 403):
            out = dict(prev or {})
            out["ok"] = False
            out["err"] = "login" if r.status_code == 401 else "forbid"
            return out
        if r.status_code >= 400:
            out = dict(prev or {})
            out["ok"] = False
            out["err"] = "http"
            return out
        body = r.json()
        if not isinstance(body, dict):
            out = dict(prev or {})
            out["ok"] = False
            out["err"] = "parse"
            return out
        return parse_deepseek_balance(body, prev)
    except Exception:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "net"
        return out


def parse_claude_usage(payload: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(prev or {})
    five = payload.get("five_hour")
    if five is None:
        five = payload.get("fiveHour")
    if five is None:
        five = payload.get("five_hour_util")
    seven = payload.get("seven_day")
    if seven is None:
        seven = payload.get("sevenDay")
    if seven is None:
        seven = payload.get("seven_day_util")

    if isinstance(five, (int, float)):
        h5 = pct(five)
        if h5 is not None:
            out["h5"] = h5
    elif isinstance(five, dict):
        h5 = _pct_first(five.get("utilization"), five.get("util"), five.get("pct"), payload.get("five_hour_utilization"))
        if h5 is not None:
            out["h5"] = h5
        rst = unix_ts(five.get("resets_at") or five.get("reset_at") or payload.get("five_hour_reset"))
        if rst:
            out["reset_h5"] = rst
    if isinstance(seven, (int, float)):
        d7 = pct(seven)
        if d7 is not None:
            out["d7"] = d7
    elif isinstance(seven, dict):
        d7 = _pct_first(seven.get("utilization"), seven.get("util"), seven.get("pct"), payload.get("seven_day_utilization"))
        if d7 is not None:
            out["d7"] = d7
        rst = unix_ts(seven.get("resets_at") or seven.get("reset_at"))
        if rst:
            out["reset_d7"] = rst
    for k, dst in (
        ("five_hour_utilization", "h5"),
        ("seven_day_utilization", "d7"),
    ):
        n = pct(payload.get(k))
        if n is not None:
            out[dst] = n
    if "h5" not in out and "d7" not in out:
        out["ok"] = False
        out["err"] = "parse"
        return out
    out["ok"] = True
    out["err"] = ""
    return out


def _pull(tok: str):
    r = http_request("GET", USAGE_URL, headers=_headers(tok), timeout=20.0)
    body: dict[str, Any] = {}
    try:
        parsed = r.json()
        if isinstance(parsed, dict):
            body = parsed
    except Exception:
        body = {}
    headers = {k.lower(): v for k, v in r.headers.items()}
    for hk, dst in (
        ("anthropic-ratelimit-unified-5h-utilization", "five_hour_utilization"),
        ("anthropic-ratelimit-unified-7d-utilization", "seven_day_utilization"),
    ):
        if hk in headers and dst not in body:
            try:
                body[dst] = float(headers[hk])
            except ValueError:
                pass
    return r, body


def _fetch_oauth(prev: dict[str, Any] | None = None) -> dict[str, Any]:
    data = _load_cred()
    oauth = _oauth(data)
    tok = _token(data)
    if not tok:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "login"
        return out
    did_refresh = False
    if _token_expired(oauth):
        fresh = _refresh()
        if fresh:
            tok = fresh
            did_refresh = True
    try:
        r, body = _pull(tok)
        if r.status_code in (401, 403) and not did_refresh:
            fresh = _refresh()
            if fresh:
                r, body = _pull(fresh)
        if r.status_code == 401:
            out = dict(prev or {})
            out["ok"] = False
            out["err"] = "login"
            return out
        if r.status_code == 403:
            out = dict(prev or {})
            out["ok"] = False
            out["err"] = "forbid"
            return out
        if r.status_code >= 400 and "h5" not in body and "five_hour" not in body and "five_hour_utilization" not in body:
            out = dict(prev or {})
            out["ok"] = False
            out["err"] = "http"
            return out
        return parse_claude_usage(body, prev)
    except Exception:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "net"
        return out


def fetch_claude(prev: dict[str, Any] | None = None) -> dict[str, Any]:
    if _deepseek_mode():
        return _fetch_deepseek(prev)
    return _fetch_oauth(prev)
