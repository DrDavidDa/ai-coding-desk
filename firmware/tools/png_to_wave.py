"""Convert wallpaper PNGs to firmware RGB565 blobs."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT.parent / "docs" / "assets"
OUT_DIR = ROOT / "src" / "assets" / "wave"
W = 240
H = 240

WALLS = [
    ("wave", "wall-wave-240.png"),
    ("ember", "wall-ember-240.png"),
    ("ink", "wall-ink-240.png"),
    ("phosphor", "wall-phosphor-240.png"),
    ("night", "wall-night-240.png"),
    ("stone", "wall-stone-240.png"),
]


def rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def convert_png(src: Path, dst: Path) -> None:
    im = Image.open(src).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    blob = bytearray()
    for r, g, b in im.getdata():
        v = rgb565(r, g, b)
        blob.append(v & 0xFF)
        blob.append(v >> 8)
    dst.write_bytes(blob)
    print("wrote", dst, len(blob), "bytes")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="convert all six wallpapers")
    ap.add_argument("png", nargs="?", help="single PNG path")
    ap.add_argument("-o", "--out", help="output .rgb565 path")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.all:
        for stem, png_name in WALLS:
            src = ASSETS / png_name
            if not src.exists():
                raise SystemExit(f"missing {src} — run gen_walls.py first")
            convert_png(src, OUT_DIR / f"{stem}.rgb565")
        return

    # Legacy single-file mode
    if args.png:
        src = Path(args.png)
    else:
        src = ASSETS / "wave-bg-240.png"
    out = Path(args.out) if args.out else OUT_DIR / "wave.rgb565"
    convert_png(src, out)


if __name__ == "__main__":
    main()
