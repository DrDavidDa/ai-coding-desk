# -*- coding: utf-8 -*-
"""Writable data vs frozen exe. Dev keeps secrets next to source."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    if frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def data_dir() -> Path:
    override = (os.environ.get("DESK_DATA_DIR") or "").strip()
    if override:
        root = Path(override)
    elif frozen():
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Desk154"
    else:
        root = app_dir()
    (root / "secrets").mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(parents=True, exist_ok=True)
    return root


def secrets_dir() -> Path:
    p = data_dir() / "secrets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def paired_flag() -> Path:
    return data_dir() / "paired.flag"


def autostart_off_flag() -> Path:
    return data_dir() / "autostart.off"


def host_log_path() -> Path:
    return data_dir() / "host.log"


def startup_bat() -> Path:
    return (
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft/Windows/Start Menu/Programs/Startup/desk154-host.bat"
    )


def launch_command() -> tuple[str, str]:
    """cwd, command line used in the Startup .bat."""
    if frozen():
        exe = str(Path(sys.executable).resolve())
        return str(Path(exe).parent), f'start "Desk154" "{exe}"'
    root = app_dir()
    py = sys.executable
    return str(root), f'start "Desk154" /min "{py}" -u desk_host.py'
