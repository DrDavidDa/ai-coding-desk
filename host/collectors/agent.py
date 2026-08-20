"""Detect Cursor agent busy/idle from local transcript mtimes. No network."""
from __future__ import annotations

import os
import time
from pathlib import Path


WORKING_AGE = 2.5
DONE_AGE = 12.0


def default_transcript_dirs() -> list[Path]:
    roots: list[Path] = []
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or "") / ".cursor" / "projects"
    if not home.is_dir():
        return roots
    try:
        kids = list(home.iterdir())
    except OSError:
        return roots
    for p in kids:
        t = p / "agent-transcripts"
        if t.is_dir():
            roots.append(t)
    return roots


def newest_jsonl_mtime(dirs) -> float | None:
    newest: float | None = None
    for d in dirs:
        try:
            files = Path(d).glob("*.jsonl")
        except OSError:
            continue
        for f in files:
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if newest is None or m > newest:
                newest = m
    return newest


def detect_cursor_agent(
    now: float | None = None,
    paths=None,
    working_age: float = WORKING_AGE,
    done_age: float = DONE_AGE,
) -> dict:
    now = time.time() if now is None else now
    m = newest_jsonl_mtime(paths if paths is not None else default_transcript_dirs())
    if m is None:
        return {"state": "idle", "name": "", "age": None}
    age = now - m
    if age < working_age:
        return {"state": "working", "name": "cursor", "age": age}
    if age < done_age:
        return {"state": "done", "name": "cursor", "age": age}
    return {"state": "idle", "name": "cursor", "age": age}
