"""Mark one button on a screenshot with a box, an arrow and an instruction (README how-tos).

Usage: python scripts/annotate_download.py <screenshot.png> <out.png> x0 y0 x1 y1 "Label" [--label-at x y]
  x0 y0 x1 y1   the box around the button (pixels in the screenshot)
  --label-at    top-left of the label; default: below-left of the box
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COLOR = (249, 200, 82)       # Nebuloria yellow
DARK = (23, 23, 23)
FONT = r"C:\Windows\Fonts\segoeuib.ttf"


def arrow(d: ImageDraw.ImageDraw, a, b, w=4) -> None:
    d.line([a, b], fill=COLOR, width=w)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-0.45, 0.45):
        d.line([b, (b[0] - 20 * math.cos(ang + s), b[1] - 20 * math.sin(ang + s))], fill=COLOR, width=w)


def annotate(src: Path, dst: Path, box: tuple[int, int, int, int], label: str, label_at=None) -> Path:
    img = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 26)
    pad = 6
    bx = (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)
    d.rounded_rectangle(bx, radius=8, outline=COLOR, width=4)
    tw = d.textlength(label, font=font)
    lx, ly = label_at if label_at else (bx[0] - tw - 120, bx[3] + 60)
    lx = max(10, min(lx, img.width - tw - 26))
    d.rounded_rectangle((lx - 12, ly - 6, lx + tw + 12, ly + 38), radius=8, fill=DARK, outline=COLOR, width=3)
    d.text((lx, ly), label, font=font, fill=COLOR)
    start = (lx + tw + 14, ly + 16)
    end = (bx[0] - 6, (bx[1] + bx[3]) / 2 + 6)
    arrow(d, start, end)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, optimize=True)
    return dst


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("box", type=int, nargs=4)
    ap.add_argument("label")
    ap.add_argument("--label-at", type=int, nargs=2)
    a = ap.parse_args(argv)
    try:
        print(f"wrote {annotate(a.src, a.dst, tuple(a.box), a.label, a.label_at)}")
    except OSError as exc:
        print(f"annotate failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
