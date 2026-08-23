"""Coze / 扣子 OpenAPI benefit quota from the local CLI session."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from collectors.util import http_request, unix_ts

BENEFIT_URL = "https://api.coze.cn/v1/commerce/benefit/benefits/get"
from paths import secrets_dir

SECRET = secrets_dir() / "coze_token.txt"
SECRET_FALLBACK = Path(__file__).resolve().parent.parent / "secrets" / "coze_token.txt"


def _fail(prev: dict[str, Any] | None, err: str) -> dict[str, Any]:
    out = dict(prev or {})
    out["ok"] = False
    out["err"] = err
    return out


def _num(v: Any) -> float | None:
    if v is None or v is False or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _counter(item: dict[str, Any]) -> dict[str, Any]:
    for key in ("effective", "basic"):
        block = item.get(key)
        if isinstance(block, dict) and isinstance(block.get("item_info"), dict):
            return block["item_info"]
    return {}


def parse_coze_benefits(payload: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    """call_tool_limit used/total. Plan-only responses stay ok with no fake windows."""
    out = dict(prev or {})
    if payload.get("code") not in (None, 0):
        return _fail(prev, "http")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    level = ""
    basic = data.get("basic_info") if isinstance(data.get("basic_info"), dict) else {}
    if basic.get("user_level"):
        level = str(basic["user_level"])
        out["plan"] = level

    out.pop("h5", None)
    out.pop("reset_h5", None)
    out.pop("left", None)
    out.pop("cap", None)
    found_quota = False
    for item in data.get("benefit_info") or []:
        if not isinstance(item, dict):
            continue
        if item.get("benefit_type") != "call_tool_limit":
            continue
        info = _counter(item)
        strategy = str(info.get("strategy") or "").lower()
        if strategy in ("unlimit", "unlimited"):
            continue
        total = _num(info.get("total"))
        used = _num(info.get("used"))
        if total is None or total <= 0 or used is None:
            continue
        n = int(round(100.0 * used / total))
        out["h5"] = 0 if n < 0 else 100 if n > 100 else n
        out["left"] = max(0, int(round(total - used)))
        out["cap"] = max(0, int(round(total)))
        rst = unix_ts(info.get("end_at"))
        if rst:
            out["reset_h5"] = rst
        found_quota = True
        break

    if not found_quota and not level:
        return _fail(prev, "parse")
    out["ok"] = True
    out["err"] = ""
    return out


def _token_candidates() -> list[str]:
    out: list[str] = []
    pat_file = Path.home() / ".coze" / "bridge" / "pat-token"
    if pat_file.is_file():
        t = pat_file.read_text(encoding="utf-8").strip()
        if t:
            out.append(t)
    cfg = Path.home() / ".coze" / "config.json"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        t = (data.get("accessToken") or data.get("token") or "").strip()
        if t and t not in out:
            out.append(t)
    for sec in (SECRET, SECRET_FALLBACK):
        if sec.is_file():
            t = sec.read_text(encoding="utf-8").strip()
            if t and t not in out:
                out.append(t)
    return out


def fetch_coze(prev: dict[str, Any] | None = None) -> dict[str, Any]:
    tokens = _token_candidates()
    if not tokens:
        return _fail(prev, "login")
    last_err = "login"
    for tok in tokens:
        headers = {
            "Authorization": "Bearer " + tok,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            r = http_request(
                "GET",
                BENEFIT_URL,
                params={"benefit_type_list": "call_tool_limit"},
                headers=headers,
                timeout=20.0,
            )
            if r.status_code == 401:
                last_err = "login"
                continue
            if r.status_code >= 400:
                last_err = "http"
                continue
            body = r.json()
            if not isinstance(body, dict):
                last_err = "parse"
                continue
            if body.get("code") not in (None, 0):
                last_err = "login" if body.get("code") == 4100 else "http"
                continue
            return parse_coze_benefits(body, prev)
        except Exception:
            last_err = "net"
            continue
    return _fail(prev, last_err)
