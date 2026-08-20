"""Cursor usage from the local IDE session (state.vscdb) plus optional extension POST."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

import httpx

from collectors.util import pct, unix_ts

SUMMARY_URL = "https://cursor.com/api/usage-summary"


def parse_cursor_summary(payload: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(prev or {})
    plan = payload
    iu = payload.get("individualUsage")
    if isinstance(iu, dict) and isinstance(iu.get("plan"), dict):
        plan = iu["plan"]

    auto = (
        plan.get("autoPercentUsed")
        or plan.get("auto_pct")
        or plan.get("autoPercent")
        or payload.get("autoPercentUsed")
        or payload.get("auto_pct")
    )
    api = (
        plan.get("apiPercentUsed")
        or plan.get("api_pct")
        or payload.get("apiPercentUsed")
        or payload.get("api_pct")
    )
    total = plan.get("totalPercentUsed") or payload.get("totalPercentUsed")
    a = pct(auto)
    p = pct(api)
    t = pct(total)
    if a is not None:
        out["auto_pct"] = a
    if p is not None:
        out["api_pct"] = p
    if t is not None:
        out["total_pct"] = t
    elif a is not None:
        out["total_pct"] = a
    cycle = (
        payload.get("billingCycleEnd")
        or payload.get("cycle_end")
        or plan.get("billingCycleEnd")
    )
    ts = unix_ts(cycle)
    if ts:
        out["cycle_end"] = ts
    if a is None and p is None and t is None:
        out["ok"] = False
        out["err"] = "parse"
        return out
    out["ok"] = True
    out["err"] = ""
    return out


def _access_token() -> str | None:
    appdata = os.environ.get("APPDATA") or ""
    db = Path(appdata) / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    if not db.is_file():
        return None
    try:
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        row = con.execute(
            "SELECT value FROM ItemTable WHERE key=?", ("cursorAuth/accessToken",)
        ).fetchone()
        con.close()
    except Exception:
        return None
    if not row or not row[0]:
        return None
    tok = row[0]
    if isinstance(tok, bytes):
        tok = tok.decode("utf-8", "ignore")
    tok = str(tok).strip()
    return tok or None


def fetch_cursor(prev: dict[str, Any] | None = None) -> dict[str, Any]:
    tok = _access_token()
    if not tok:
        out = dict(prev or {})
        if not out.get("ok"):
            out["ok"] = False
            out["err"] = out.get("err") or "login"
        return out
    cookie = tok if "::" in tok else f"user::{tok}"
    try:
        r = httpx.get(
            SUMMARY_URL,
            headers={
                "Accept": "application/json",
                "Cookie": f"WorkosCursorSessionToken={cookie}",
                "User-Agent": "Mozilla/5.0",
            },
            timeout=20.0,
        )
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
        return parse_cursor_summary(r.json(), prev)
    except Exception:
        out = dict(prev or {})
        if not out.get("ok"):
            out["ok"] = False
            out["err"] = "net"
        return out
