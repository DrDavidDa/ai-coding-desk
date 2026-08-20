"""Zhipu GLM Coding Plan — port of PaperColor pollZhipuCodingPlan / parseZhipuQuotaJson."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import httpx

BJT = timezone(timedelta(hours=8))
QUOTA_URL = "https://open.bigmodel.cn/api/monitor/usage/quota/limit"
MODEL_URL = "https://open.bigmodel.cn/api/monitor/usage/model-usage"
TOOL_URL = "https://open.bigmodel.cn/api/monitor/usage/tool-usage"

TOKEN_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "secrets" / "zhipu_token.txt",
    Path(__file__).resolve().parent / "secrets" / "zhipu_token.txt",
    Path.home() / "Documents" / "PlatformIO" / "Projects" / "PaperColor_Study" / "zhipu_token.txt",
]


def find_token() -> str | None:
    for p in TOKEN_CANDIDATES:
        if p.is_file():
            t = p.read_text(encoding="utf-8").strip()
            if t:
                return t
    return None


def format_bjt_epoch(ts_ms: int) -> int:
    """PaperColor: ms UTC. We keep unix seconds for the device."""
    if not ts_ms:
        return 0
    return int(ts_ms / 1000)


def parse_quota_json(payload: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    """limits[0]=5h, [1]=7d, [2]=MCP. On parse failure keep prev (never zero the ring)."""
    out = dict(prev or {})
    out.setdefault("h5", 0)
    out.setdefault("d7", 0)
    out.setdefault("mcp", 0)
    out.setdefault("reset_h5", 0)
    out.setdefault("reset_d7", 0)
    out.setdefault("reset_mcp", 0)
    out.setdefault("daily_tokens", 0)
    out.setdefault("tool_search", 0)
    out.setdefault("tool_webread", 0)
    if payload.get("code") != 200:
        out["ok"] = False
        out["err"] = "http"
        return out
    limits = (payload.get("data") or {}).get("limits") or []
    keys = (("h5", "reset_h5"), ("d7", "reset_d7"), ("mcp", "reset_mcp"))
    for i, (pk, rk) in enumerate(keys):
        if i >= len(limits):
            break
        lim = limits[i] or {}
        out[pk] = int(lim.get("percentage") or 0)
        out[rk] = format_bjt_epoch(int(lim.get("nextResetTime") or 0))
    out["ok"] = True
    out["err"] = ""
    return out


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Connection": "close",
    }


def fetch_glm(token: str | None = None, prev: dict[str, Any] | None = None) -> dict[str, Any]:
    token = token or find_token()
    if not token:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = "login"
        return out
    headers = _headers(token)
    try:
        with httpx.Client(timeout=15.0, http2=False) as client:
            r = client.get(QUOTA_URL, headers=headers)
            if r.status_code == 401:
                out = dict(prev or {})
                out["ok"] = False
                out["err"] = "login"
                return out
            r.raise_for_status()
            data = r.json()
            out = parse_quota_json(data, prev)
            now = datetime.now(BJT)
            st = now.strftime("%Y-%m-%d+00:00:00")
            et = now.strftime("%Y-%m-%d+23:59:59")
            try:
                r2 = client.get(MODEL_URL, headers=headers, params={"startTime": st, "endTime": et})
                if r2.status_code == 200:
                    d2 = r2.json()
                    tu = (d2.get("data") or {}).get("totalUsage") or {}
                    out["daily_tokens"] = int(tu.get("totalTokensUsage") or 0)
            except Exception:
                pass
            try:
                r3 = client.get(TOOL_URL, headers=headers, params={"startTime": st, "endTime": et})
                if r3.status_code == 200:
                    d3 = r3.json()
                    tu = (d3.get("data") or {}).get("totalUsage") or {}
                    out["tool_search"] = int(tu.get("totalNetworkSearchCount") or 0)
                    out["tool_webread"] = int(tu.get("totalWebReadMcpCount") or 0)
            except Exception:
                pass
            return out
    except Exception:
        out = dict(prev or {})
        out["ok"] = False
        out["err"] = out.get("err") or "net"
        return out
