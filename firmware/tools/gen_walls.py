#!/usr/bin/env python3
"""Generate six 240x240 wallpaper PNGs for Desk154 settings."""
from __future__ import annotations

import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"
W, H = 240, 240


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def blend(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def save(name: str, im: Image.Image) -> None:
    path = ASSETS / name
    im.save(path, optimize=True)
    print("wrote", path)


def gen_wave() -> None:
    src = ASSETS / "wave-bg-240.png"
    dst = ASSETS / "wall-wave-240.png"
    if src.exists():
        shutil.copy2(src, dst)
        print("copied", dst)
    else:
        im = Image.new("RGB", (W, H), (10, 12, 18))
        save("wall-wave-240.png", im)


def gen_ember() -> None:
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            t = y / (H - 1)
            base = blend((26, 12, 8), (18, 6, 4), t)
            # warm blob lower-left
            dx, dy = (x - W * 0.25) / W, (y - H * 0.85) / H
            r = math.exp(-(dx * dx + dy * dy) * 8)
            hot = blend(base, (255, 106, 32), r * 0.55)
            # cool upper-right
            dx2, dy2 = (x - W * 0.82) / W, (y - H * 0.12) / H
            r2 = math.exp(-(dx2 * dx2 + dy2 * dy2) * 10)
            col = blend(hot, (122, 26, 8), r2 * 0.4)
            px[x, y] = col
    save("wall-ember-240.png", im)


def gen_ink() -> None:
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            t = y / (H - 1)
            col = blend((239, 228, 204), (216, 200, 168), t)
            dx, dy = (x - W * 0.3) / W, (y - H * 0.2) / H
            r = math.exp(-(dx * dx + dy * dy) * 6)
            col = blend(col, (255, 248, 234), r * 0.35)
            px[x, y] = col
    save("wall-ink-240.png", im)


def gen_phosphor() -> None:
    im = Image.new("RGB", (W, H), (3, 18, 8))
    draw = ImageDraw.Draw(im)
    step = 16
    for x in range(0, W, step):
        draw.line([(x, 0), (x, H)], fill=(40, 255, 100), width=1)
    for y in range(0, H, step):
        draw.line([(0, y), (W, y)], fill=(40, 255, 100), width=1)
    # vignette via pixel blend
    px = im.load()
    for y in range(H):
        for x in range(W):
            cx, cy = (x - W / 2) / W, (y - H / 2) / H
            v = min(1.0, (cx * cx + cy * cy) * 1.2)
            r, g, b = px[x, y]
            px[x, y] = (int(r * (1 - v * 0.5)), int(g * (1 - v * 0.3)), int(b * (1 - v * 0.5)))
    save("wall-phosphor-240.png", im)


def gen_night() -> None:
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            t = y / (H - 1)
            col = blend((8, 20, 40), (10, 16, 32), t)
            px[x, y] = col
    draw = ImageDraw.Draw(im)
    stars = [
        (44, 52, 2), (72, 38, 1), (180, 44, 2), (210, 70, 1),
        (96, 88, 1), (160, 100, 2), (30, 120, 1), (200, 140, 1),
    ]
    for sx, sy, rad in stars:
        draw.ellipse((sx - rad, sy - rad, sx + rad, sy + rad), fill=(255, 233, 176))
    save("wall-night-240.png", im)


def gen_stone() -> None:
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            t = y / (H - 1)
            base = blend((74, 78, 88), (28, 30, 36), t)
            n = ((x * 13 + y * 7) % 17) / 17.0
            col = blend(base, (90, 94, 102), n * 0.15)
            px[x, y] = col
    save("wall-stone-240.png", im)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    gen_wave()
    gen_ember()
    gen_ink()
    gen_phosphor()
    gen_night()
    gen_stone()


if __name__ == "__main__":
    main()
