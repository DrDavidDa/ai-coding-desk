"""Build 功德+1 LVGL image and wooden-fish knock PCM from Ares-Chang assets."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "assets"
PCM = ASSETS / "wood.pcm"
FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
BG = (0x12, 0x0C, 0x08)


def rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def write_img_c(path: Path, name: str, im: Image.Image, comment: str) -> None:
    w, h = im.size
    rows = [
        f"/* {comment} */",
        f'#include "{name}.h"',
        "",
        f"const LV_ATTRIBUTE_MEM_ALIGN uint8_t {name}_map[{w * h * 3}] = {{",
    ]
    chunk: list[str] = []
    for r, g, b, a in im.getdata():
        v = rgb565(r, g, b)
        chunk += [f"0x{v & 0xFF:02x}", f"0x{v >> 8:02x}", f"0x{a:02x}"]
        if len(chunk) >= 12:
            rows.append("  " + ", ".join(chunk) + ",")
            chunk = []
    if chunk:
        rows.append("  " + ", ".join(chunk) + ",")
    rows += [
        "};",
        "",
        f"const lv_img_dsc_t {name} = {{",
        "  .header.always_zero = 0,",
        f"  .header.w = {w},",
        f"  .header.h = {h},",
        "  .header.cf = LV_IMG_CF_TRUE_COLOR_ALPHA,",
        f"  .data_size = sizeof({name}_map),",
        f"  .data = {name}_map,",
        "};",
        "",
    ]
    (ROOT / "src" / f"{name}.c").write_text("\n".join(rows), encoding="utf-8")
    (ROOT / "src" / f"{name}.h").write_text(
        f"#pragma once\n#include <lvgl.h>\nextern const lv_img_dsc_t {name};\n",
        encoding="utf-8",
    )
    print(f"{name} {w}x{h}")


def make_merit() -> None:
    font = ImageFont.truetype(str(FONT), 28, index=0)
    gold = (0xF0, 0xC1, 0x4A, 255)
    hot = (0xF0, 0x5A, 0x38, 255)
    tmp = Image.new("RGBA", (240, 52), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)
    x, y = 8, 4
    draw.text((x, y), "功德", font=font, fill=gold)
    box = draw.textbbox((x, y), "功德", font=font)
    draw.text((box[2] + 2, y), "+1", font=font, fill=hot)
    bbox = tmp.getbbox()
    assert bbox
    pad = 2
    im = tmp.crop((max(bbox[0] - pad, 0), max(bbox[1] - pad, 0), bbox[2] + pad, bbox[3] + pad))
    im.save(ASSETS / "merit_plus.png")
    write_img_c(ROOT / "src" / "merit_plus.c", "merit_plus", im, "功德+1 gold/vermillion, Microsoft YaHei")


def make_pcm() -> None:
    raw = PCM.read_bytes()
    samples = []
    peak = 1
    for i in range(0, len(raw) - 1, 2):
        v = int.from_bytes(raw[i : i + 2], "little", signed=True)
        samples.append(v)
        peak = max(peak, abs(v))
    gain = min(2.4, 28000.0 / peak)
    scaled = [max(-32767, min(32767, int(v * gain))) for v in samples]
    rows = [
        "/* sound_1.mp3 from https://github.com/Ares-Chang/wooden-fish (MIT). */",
        '#include "wood_pcm.h"',
        "",
        f"const int16_t wood_pcm[{len(scaled)}] = {{",
    ]
    chunk: list[str] = []
    for v in scaled:
        chunk.append(str(v))
        if len(chunk) == 16:
            rows.append("  " + ", ".join(chunk) + ",")
            chunk = []
    if chunk:
        rows.append("  " + ", ".join(chunk) + ",")
    rows += [ "};", "", f"const unsigned wood_pcm_len = {len(scaled)};", ""]
    (ROOT / "src" / "wood_pcm.c").write_text("\n".join(rows), encoding="utf-8")
    (ROOT / "src" / "wood_pcm.h").write_text(
        "#pragma once\n#include <stdint.h>\nextern const int16_t wood_pcm[];\nextern const unsigned wood_pcm_len;\n",
        encoding="utf-8",
    )
    print(f"pcm n={len(scaled)} peak={peak} gain={gain:.2f} ms={len(scaled) * 1000 / 16000:.0f}")


if __name__ == "__main__":
    make_merit()
    make_pcm()
