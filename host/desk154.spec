# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hidden = []
for pkg in ("uvicorn", "fastapi", "starlette", "anyio", "pydantic", "serial", "pystray"):
    try:
        hidden += collect_submodules(pkg)
    except Exception:
        pass

hidden += [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "pystray._win32",
    "PIL._tkinter_finder",
    "serial.tools.list_ports",
    "setup_gui",
    "desk_pair",
    "paths",
    "asr",
    "inject",
    "collectors.claude",
    "collectors.codex",
    "collectors.cursor",
    "collectors.glm",
    "collectors.kimi",
    "collectors.trae",
    "collectors.coze",
    "collectors.agent",
    "collectors.util",
]

a = Analysis(
    ["desk_host.py"],
    pathex=["."],
    binaries=[],
    datas=[("packaging/使用说明.txt", ".")],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Desk154",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Desk154",
)
