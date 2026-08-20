"""SenseVoice ASR — same SiliconFlow HTTP path PaperColor already proved."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

from inject import clean_transcript, inject_transcript

ROOT = Path(__file__).resolve().parent
SF_CANDIDATES = [
    ROOT / "secrets" / "sf_api_key.txt",
    Path.home() / "Documents" / "PlatformIO" / "Projects" / "PaperColor_Study" / "sf_api_key.txt",
]
SF_URL = "http://api.siliconflow.cn/v1/audio/transcriptions"
SF_MODEL = "FunAudioLLM/SenseVoiceSmall"


def find_sf_key() -> str | None:
    env = os.environ.get("SF_API_KEY", "").strip()
    if env:
        return env
    for p in SF_CANDIDATES:
        if p.is_file():
            k = p.read_text(encoding="utf-8").strip()
            if k:
                return k
    return None


def parse_asr_json(payload: dict[str, Any]) -> str:
    text = payload.get("text") or payload.get("data") or ""
    if isinstance(text, dict):
        text = text.get("text") or ""
    return clean_transcript(str(text))


def transcribe_wav(wav: bytes) -> str:
    key = find_sf_key()
    if not key:
        raise RuntimeError("no_sf_key")
    files = {"file": ("ptt.wav", wav, "audio/wav")}
    data = {"model": SF_MODEL}
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            SF_URL,
            headers={"Authorization": f"Bearer {key}"},
            files=files,
            data=data,
        )
        r.raise_for_status()
        raw = r.text
        print("[host] asr http", r.status_code, raw[:240])
        return parse_asr_json(r.json())


def paste_text(text: str, target: str = "cursor", press_enter: bool = False, steal_focus: bool = False) -> dict:
    """Name kept for callers; implementation types Unicode into the dialog."""
    return inject_transcript(text, target=target, press_enter=press_enter, steal_focus=steal_focus)
