"""Rasterize Ares-Chang WoodenFish.svg into an LVGL RGB565 image."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "assets" / "WoodenFish.svg"
PNG = ROOT / "src" / "assets" / "muyu.png"
OUT_C = ROOT / "src" / "muyu_img.c"
OUT_H = ROOT / "src" / "muyu_img.h"
TARGET_W = 168


def rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def main() -> None:
    svg = SRC.read_text(encoding="utf-8").replace("fill='#eeeeee'", "fill='#E6B56A'")
    tmp = SRC.with_name("WoodenFish_render.svg")
    tmp.write_text(svg, encoding="utf-8")
    drawing = svg2rlg(str(tmp))
    scale = TARGET_W / float(drawing.width)
    drawing.width *= scale
    drawing.height *= scale
    drawing.scale(scale, scale)
    png_bytes = renderPM.drawToString(drawing, fmt="PNG", bg=0x1A0E08)
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    im.save(PNG)
    w, h = im.size
    pixels = list(im.getdata())
    rows: list[str] = [
        "/* WoodenFish.svg from https://github.com/Ares-Chang/wooden-fish (MIT). */",
        '#include "muyu_img.h"',
        "",
        f"const LV_ATTRIBUTE_MEM_ALIGN uint8_t muyu_map[{w * h * 2}] = {{",
    ]
    chunk: list[str] = []
    for r, g, b in pixels:
        v = rgb565(r, g, b)
        chunk.append(f"0x{v & 0xFF:02x}, 0x{v >> 8:02x}")
        if len(chunk) == 8:
            rows.append("  " + ", ".join(chunk) + ",")
            chunk = []
    if chunk:
        rows.append("  " + ", ".join(chunk) + ",")
    rows += [
        "};",
        "",
        "const lv_img_dsc_t muyu_img = {",
        "  .header.always_zero = 0,",
        f"  .header.w = {w},",
        f"  .header.h = {h},",
        "  .header.cf = LV_IMG_CF_TRUE_COLOR,",
        "  .data_size = sizeof(muyu_map),",
        "  .data = muyu_map,",
        "};",
        "",
    ]
    OUT_C.write_text("\n".join(rows), encoding="utf-8")
    OUT_H.write_text(
        "#pragma once\n#include <lvgl.h>\nextern const lv_img_dsc_t muyu_img;\n",
        encoding="utf-8",
    )
    print(f"png {PNG} {w}x{h}  c {OUT_C.stat().st_size}")


if __name__ == "__main__":
    main()
