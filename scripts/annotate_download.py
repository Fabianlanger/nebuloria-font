"""Annotate a GitHub screenshot with numbered boxes and arrows (download how-to for the README).

Usage: python scripts/annotate_download.py <screenshot.png> <out.png>
Coordinates match a 1891 x 723 screenshot of the dist/Nebuloria-v1.5.zip page.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COLOR = (249, 200, 82)       # Nebuloria yellow
DARK = (23, 23, 23)
FONT = r"C:\Windows\Fonts\segoeuib.ttf"

# (step, box, badge centre, label, label position)
STEPS = [
    (1, (6, 312, 150, 342), (175, 300), "Open dist", (198, 285)),
    (2, (6, 408, 284, 440), (310, 400), "Click the zip file", (333, 385)),
    (3, (1846, 113, 1884, 147), (1790, 85), "Click ···", (1640, 70)),
    (4, (1630, 188, 1876, 220), (1580, 260), "Click Download", (1380, 290)),
]


def arrow(d: ImageDraw.ImageDraw, a, b, w=4):
    d.line([a, b], fill=COLOR, width=w)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-0.45, 0.45):
        d.line([b, (b[0] - 18 * math.cos(ang + s), b[1] - 18 * math.sin(ang + s))], fill=COLOR, width=w)


def annotate(src: Path, dst: Path) -> Path:
    img = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(img)
    num = ImageFont.truetype(FONT, 26)
    lab = ImageFont.truetype(FONT, 22)
    for n, box, badge, label, lpos in STEPS:
        d.rounded_rectangle(box, radius=6, outline=COLOR, width=4)
        cx, cy = badge
        target = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        # arrow from badge edge to box edge
        ang = math.atan2(target[1] - cy, target[0] - cx)
        start = (cx + 22 * math.cos(ang), cy + 22 * math.sin(ang))
        bw, bh = (box[2] - box[0]) / 2, (box[3] - box[1]) / 2
        t = min(bw / max(abs(math.cos(ang)), 1e-6), bh / max(abs(math.sin(ang)), 1e-6))
        end = (target[0] - (t + 8) * math.cos(ang), target[1] - (t + 8) * math.sin(ang))
        arrow(d, start, end)
        d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=COLOR)
        d.text((cx, cy), str(n), font=num, fill=DARK, anchor="mm")
        tw = d.textlength(label, font=lab)
        x, y = lpos
        d.rounded_rectangle((x - 8, y - 4, x + tw + 8, y + 30), radius=6, fill=DARK, outline=COLOR, width=2)
        d.text((x, y), label, font=lab, fill=COLOR)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, optimize=True)
    return dst


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        raise SystemExit(2)
    try:
        print(f"wrote {annotate(Path(sys.argv[1]), Path(sys.argv[2]))}")
    except OSError as exc:
        print(f"annotate failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
