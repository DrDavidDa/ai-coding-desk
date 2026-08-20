"""Rasterize compressor PNGs into one 240x240 RGB565 strip for LVGL."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "docs" / "assets" / "compressor"
OUT_DIR = ROOT / "src" / "assets" / "pack"
OUT_BIN = OUT_DIR / "frames.rgb565"
W = 240
H = 240
FILES = (
    "01-idle.png",
    "03-feeding.png",
    "04-compressing.png",
    "02-reward.png",
)


def rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    blob = bytearray()
    for name in FILES:
        im = Image.open(SRC / name).convert("RGB").resize((W, H), Image.Resampling.NEAREST)
        for r, g, b in im.getdata():
            v = rgb565(r, g, b)
            blob.append(v & 0xFF)
            blob.append(v >> 8)
        print(name, im.size)
    OUT_BIN.write_bytes(blob)
    print("wrote", OUT_BIN, "bytes", len(blob), "frames", len(FILES))


if __name__ == "__main__":
    main()
