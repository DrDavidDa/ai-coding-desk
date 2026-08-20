"""Rasterize desk154-live.html logos the same way Chrome paints them.

Uses Chromium headless so currentColor / CSS filters match the HTML prototype.
Stores LVGL TRUE_COLOR_ALPHA (RGB565 + A8) so quota gray/color layers tint
the icon, not a solid background square.
"""
from __future__ import annotations

import struct
import subprocess
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT.parent / "docs"
HTML = DOCS / "raster-logos.html"
SHOT = ROOT / "src" / "assets" / "logos" / "chrome_strip.png"
PREVIEW = ROOT / "src" / "assets" / "logos" / "preview.png"
OUT_BIN = ROOT / "src" / "assets" / "logos" / "frames.rgb565"
OUT_H = ROOT / "src" / "logos_img.h"
OUT_C = ROOT / "src" / "logos_img.c"
SIZE = 56
COUNT = 35
# Official 扣子 desktop mark. Magenta key would eat its pink circle.
# Inset so it is not a full-bleed sticker (LVGL zoom+alpha glitches on dense frames).
OVERRIDES = {
    7: DOCS / "logos" / "coze-app-256.png",
}
OVERRIDE_PAD = {7: 8}
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def de_magenta(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    px = list(im.getdata())
    out = []
    for r, g, b, _a in px:
        # Magenta key used by raster-logos.html. Keep anti-aliased edges.
        mag = min(r, b)
        if g < 48 and mag > 200:
            out.append((r, g, b, 0))
            continue
        # Magenta bleed: drop pixels whose strongest channel pair is magenta.
        magenta = (r + b) / 2 - g
        if magenta > 90 and g < 90:
            a = int(max(0, 255 - magenta * 1.4))
            out.append((r, g, b, a))
            continue
        out.append((r, g, b, 255))
    im.putdata(out)
    return im


def find_strip(im: Image.Image) -> Image.Image:
    """Crop the 35x56 row. Chrome often adds a few pixels of padding."""
    im = im.convert("RGB")
    w, h = im.size
    want_w = SIZE * COUNT
    x0 = max(0, (w - want_w) // 2)
    y0 = max(0, (h - SIZE) // 2)
    crop = im.crop((x0, y0, x0 + want_w, y0 + SIZE))
    if crop.size != (want_w, SIZE):
        crop = im.resize((want_w, SIZE), Image.Resampling.NEAREST)
    return crop


def chrome_shot() -> Image.Image:
    browser = CHROME if CHROME.exists() else EDGE
    SHOT.parent.mkdir(parents=True, exist_ok=True)
    if SHOT.exists():
        SHOT.unlink()
    uri = HTML.resolve().as_uri()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--disk-cache-size=1",
        "--disable-application-cache",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--default-background-color=00FF00FF",
        f"--window-size={SIZE * COUNT},{SIZE + 8}",
        "--allow-file-access-from-files",
        "--virtual-time-budget=8000",
        f"--screenshot={SHOT}",
        uri,
    ]
    print("run", browser.name)
    subprocess.run(cmd, check=True, timeout=60)
    # Chromium sometimes returns before the file is flushed.
    for _ in range(20):
        if SHOT.exists() and SHOT.stat().st_size > 1000:
            break
        time.sleep(0.1)
    im = Image.open(SHOT)
    print("shot", im.size)
    return find_strip(im)


def load_override(path: Path, pad: int = 0) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    inner = SIZE - pad * 2
    if inner < 8:
        inner = SIZE
        pad = 0
    im = src.resize((inner, inner), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(im, (pad, pad), im)
    px = []
    for r, g, b, a in canvas.getdata():
        if a < 16 or (r < 18 and g < 18 and b < 18):
            px.append((0, 0, 0, 0))
        else:
            px.append((r, g, b, a))
    canvas.putdata(px)
    return canvas


def main() -> None:
    strip = chrome_shot()
    strip.save(PREVIEW)
    blob = bytearray()
    preview_cells = Image.new("RGBA", (SIZE * COUNT, SIZE), (0x10, 0x0E, 0x0C, 255))
    for i in range(COUNT):
        if i in OVERRIDES and OVERRIDES[i].is_file():
            cell = load_override(OVERRIDES[i], OVERRIDE_PAD.get(i, 0))
        else:
            cell = de_magenta(strip.crop((i * SIZE, 0, (i + 1) * SIZE, SIZE)))
        preview_cells.paste(cell, (i * SIZE, 0), cell)
        opaque = 0
        for r, g, b, a in cell.getdata():
            v = rgb565(r, g, b)
            blob.extend(struct.pack("<H", v))
            blob.append(a)
            if a > 32:
                opaque += 1
        print(f"{i:02d} opaque={opaque}")
    preview_cells.save(PREVIEW)
    OUT_BIN.write_bytes(blob)
    n = COUNT
    hdr = [
        "#pragma once",
        "#include <lvgl.h>",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        f"#define LOGO_COUNT {n}",
        f"#define LOGO_SIZE {SIZE}",
        "extern const lv_img_dsc_t logo_img[LOGO_COUNT];",
        "#ifdef __cplusplus",
        "}",
        "#endif",
        "",
    ]
    OUT_H.write_text("\n".join(hdr), encoding="utf-8")
    rows = [
        '#include "logos_img.h"',
        "",
        "extern const uint8_t logo_frames_map[];",
        "",
        f"#define LOGO_FRAME_BYTES ({SIZE} * {SIZE} * 3)",
        "",
        "const lv_img_dsc_t logo_img[LOGO_COUNT] = {",
    ]
    for i in range(n):
        rows += [
            "    {",
            "        .header.always_zero = 0,",
            f"        .header.w = {SIZE},",
            f"        .header.h = {SIZE},",
            "        .header.cf = LV_IMG_CF_TRUE_COLOR_ALPHA,",
            "        .data_size = LOGO_FRAME_BYTES,",
            f"        .data = logo_frames_map + LOGO_FRAME_BYTES * {i},",
            "    },",
        ]
    rows += ["};", ""]
    OUT_C.write_text("\n".join(rows), encoding="utf-8")
    print("bin", OUT_BIN, "bytes", len(blob), "n", n)


if __name__ == "__main__":
    main()
