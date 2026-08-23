# -*- coding: utf-8 -*-
"""Rebuild idle 12/16 with UI + 100-lot oracle glyphs."""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(r"E:\ai-coding-desk")
FONTS = ROOT / "firmware" / "src" / "fonts"
SRC = ROOT / "firmware" / "src"

UI = (
    "周一二三四五六日家有晴少云阴雾毛雨雪阵雷多天气…节省词元语音输入发送取消讲话°"
    "上上中平下下上吉中吉中下庙签第十七卅二四八九百宜开新忌空口复读额度假尚余灵感半醒"
    "小步一次塞十事幻觉将至空烧停手读连夜加需求再晃重抽点空白收起清明一问即对抽签·"
    "发到音量电脑设置壁纸连接同步息屏警告"
)


def cjk_from(text: str) -> str:
    chars = []
    seen = set()
    for ch in text:
        o = ord(ch)
        if o < 0x80:
            continue
        if ch in seen:
            continue
        seen.add(ch)
        chars.append(ch)
    return "".join(chars)


def collect() -> str:
    blob = UI
    for p in SRC.glob("*.{cpp,h,c}"):
        blob += p.read_text(encoding="utf-8", errors="replace")
    # keep order: UI first, then extras
    extra = []
    have = set(UI)
    for ch in blob:
        if ord(ch) >= 0x80 and ch not in have:
            have.add(ch)
            extra.append(ch)
    return UI + "".join(extra)


def conv(size: int, name: str, out: pathlib.Path, symbols: str) -> int:
    cmd = [
        "npx", "--yes", "lv_font_conv@1.5.2",
        "--size", str(size), "--bpp", "4", "--format", "lvgl", "--no-compress",
        "--lv-include", "lvgl.h",
        "--font", r"C:\Windows\Fonts\bahnschrift.ttf", "-r", "0x20-0x7E",
        "--font", r"C:\Windows\Fonts\simhei.ttf", "--symbols", symbols,
        "--font", r"C:\Windows\Fonts\seguisym.ttf", "--symbols", "✦",
        "-o", str(out),
    ]
    print("font", name, "glyphs", len(symbols), "...")
    r = subprocess.run(cmd, cwd=str(FONTS), shell=True)
    print("exit", r.returncode)
    return r.returncode


def main() -> int:
    symbols = collect()
    print("unique CJK+", len(symbols))
    print(symbols)
    rc = conv(12, "font_idle_12", FONTS / "font_idle_12.c", symbols)
    if rc:
        return rc
    rc = conv(16, "font_idle_16", FONTS / "font_idle_16.c", symbols)
    if rc:
        return rc
    t = (FONTS / "font_idle_12.c").read_text(encoding="utf-8", errors="replace")
    for ch in "百吉上中下平庙签":
        ok = ("U+%04X" % ord(ch)) in t
        print(ch, "OK" if ok else "MISSING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
