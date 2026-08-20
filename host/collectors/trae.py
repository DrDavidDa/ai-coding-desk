"""Trae CN credits / fast-request quota from the local IDE session."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from collectors.util import http_request, unix_ts

USAGE_PATH = "/trae/api/v2/pay/ide_user_ent_usage"
AUTH_KEY = "iCubeAuthInfo://icube.cloudide"
HDR = bytes([0x74, 0x63, 0x05, 0x10, 0x00, 0x00])
# AES key material used by Trae / VS Code CloudIDE storage (cockpit-tools #894).
_IJ = bytes(
    [
        82, 9, 106, 213, 48, 54, 165, 56, 191, 64, 163, 158, 129, 243, 215, 251,
        124, 227, 57, 130, 155, 47, 255, 135, 52, 142, 67, 68, 196, 222, 233, 203,
        84, 123, 148, 50, 166, 194, 35, 61, 238, 76, 149, 11, 66, 250, 195, 78,
        8, 46, 161, 102, 40, 217, 36, 178, 118, 91, 162, 73, 109, 139, 209, 37,
    ]
)
_RJ = bytes(
    [
        31, 221, 168, 51, 136, 7, 199, 49, 177, 18, 16, 89, 39, 128, 236, 95,
        96, 81, 127, 169, 25, 181, 74, 13, 45, 229, 122, 159, 147, 201, 156, 239,
        160, 224, 59, 77, 174, 42, 245, 176, 200, 235, 187, 60, 131, 83, 153, 97,
        23, 43, 4, 126, 186, 119, 214, 38, 225, 105, 20, 99, 85, 33, 12, 125,
    ]
)
FIXED_A = bytes(a ^ b for a, b in zip(_IJ, _RJ))


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


def _used_pct(used: float, limit: float) -> int:
    if limit <= 0:
        return 0
    n = int(round(100.0 * used / limit))
    if n < 0:
        return 0
    if n > 100:
        return 100
    return n


def parse_trae_usage(payload: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    """Credits (preferred) or premium fast requests. Skip packs with no usage numbers."""
    out = dict(prev or {})
    packs = payload.get("user_entitlement_pack_list")
    if not isinstance(packs, list):
        return _fail(prev, "parse")

    cred_used = 0.0
    cred_limit = 0.0
    fast_used = 0.0
    fast_limit = 0.0
    reset = 0
    for pack in packs:
        if not isinstance(pack, dict):
            continue
        base = pack.get("entitlement_base_info") if isinstance(pack.get("entitlement_base_info"), dict) else {}
        quota = base.get("quota") if isinstance(base.get("quota"), dict) else {}
        usage = pack.get("usage") if isinstance(pack.get("usage"), dict) else {}
        end = unix_ts(base.get("end_time") or pack.get("expire_time"))
        c_lim = _num(quota.get("credits_limit"))
        c_used = _num(usage.get("credits_amount"))
        if c_lim is not None and c_lim > 0 and c_used is not None:
            cred_limit += c_lim
            cred_used += max(0.0, c_used)
            if end and (not reset or end < reset):
                reset = end
        f_lim = _num(quota.get("premium_model_fast_request_limit"))
        f_used = _num(usage.get("premium_model_fast_request_usage"))
        if f_lim is not None and f_lim > 0 and f_used is not None:
            fast_limit += f_lim
            fast_used += max(0.0, f_used)
            if end and (not reset or end < reset):
                reset = end

    out.pop("h5", None)
    out.pop("reset_h5", None)
    out.pop("left", None)
    out.pop("cap", None)
    if cred_limit > 0:
        out["h5"] = _used_pct(cred_used, cred_limit)
        out["left"] = max(0, int(round(cred_limit - cred_used)))
        out["cap"] = max(0, int(round(cred_limit)))
        if reset:
            out["reset_h5"] = reset
    elif fast_limit > 0:
        out["h5"] = _used_pct(fast_used, fast_limit)
        out["left"] = max(0, int(round(fast_limit - fast_used)))
        out["cap"] = max(0, int(round(fast_limit)))
        if reset:
            out["reset_h5"] = reset
    out["ok"] = True
    out["err"] = ""
    return out


def _storage_paths() -> list[Path]:
    app = os.environ.get("APPDATA") or ""
    names = ("Trae CN", "Trae")
    out: list[Path] = []
    if app:
        root = Path(app)
        for name in names:
            out.append(root / name / "User" / "globalStorage" / "storage.json")
    return out


def _decrypt_auth(blob_b64: str) -> dict[str, Any]:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    raw = base64.b64decode(blob_b64)
    if len(raw) < 40 or raw[:6] != HDR:
        raise ValueError("bad blob")
    enc_key, ct = raw[6:38], raw[38:]
    h2 = hashlib.sha512(hashlib.sha512(enc_key).digest() + FIXED_A).digest()
    dec = Cipher(algorithms.AES(h2[:16]), modes.CBC(h2[16:32])).decryptor()
    pt = dec.update(ct) + dec.finalize()
    pad = pt[-1]
    if 1 <= pad <= 16:
        pt = pt[:-pad]
    if len(pt) < 64:
        raise ValueError("short")
    data = json.loads(pt[64:].decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("json")
    return data


def _load_session() -> tuple[str, str] | None:
    for path in _storage_paths():
        if not path.is_file():
            continue
        try:
            store = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        blob = store.get(AUTH_KEY)
        if not isinstance(blob, str) or not blob:
            continue
        try:
            auth = _decrypt_auth(blob)
        except Exception:
            continue
        tok = auth.get("token") or auth.get("accessToken") or ""
        if not tok:
            continue
        host = str(auth.get("host") or "https://api.trae.cn").rstrip("/")
        return str(tok), host
    return None


def fetch_trae(prev: dict[str, Any] | None = None) -> dict[str, Any]:
    sess = _load_session()
    if not sess:
        return _fail(prev, "login")
    tok, host = sess
    url = host + USAGE_PATH
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Cloud-IDE-JWT " + tok,
        "User-Agent": "Trae/1.0.0",
    }
    try:
        r = http_request("POST", url, headers=headers, json={"require_usage": True}, timeout=20.0)
        if r.status_code == 401:
            return _fail(prev, "login")
        if r.status_code >= 400:
            return _fail(prev, "http")
        body = r.json()
        if not isinstance(body, dict):
            return _fail(prev, "parse")
        if body.get("code") not in (None, 0, 200):
            return _fail(prev, "http")
        return parse_trae_usage(body, prev)
    except Exception:
        return _fail(prev, "net")
