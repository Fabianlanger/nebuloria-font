"""Mark one button on a screenshot in Nebuloria style (README how-tos).

Box   = a Nebuloria "window": 45-degree chamfered frame, hairline inner frame, three glare lines.
Arrow = a hanging liana: starts in a small teardrop, swells, tapers to a needle point.
Label = plain regular text.

Usage: python scripts/annotate_download.py <screenshot.png> <out.png> x0 y0 x1 y1 "Label" --label-at x y
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COLOR = (249, 200, 82)       # Nebuloria yellow
FONT = r"C:\Windows\Fonts\segoeui.ttf"   # regular weight
SS = 4                       # supersampling for smooth hairlines


def octagon(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def window_box(d: ImageDraw.ImageDraw, box, s: float) -> None:
    x0, y0, x1, y1 = (v * s for v in box)
    pad, c = 15 * s, 11 * s
    outer = octagon(x0 - pad, y0 - pad, x1 + pad, y1 + pad, c)
    d.line(outer + [outer[0]], fill=COLOR, width=int(3.5 * s), joint="curve")
    inner = octagon(x0 - pad + 5 * s, y0 - pad + 5 * s, x1 + pad - 5 * s, y1 + pad - 5 * s, c * 0.7)
    d.line(inner + [inner[0]], fill=COLOR, width=max(1, int(1.1 * s)))
    gx, gy = x0 - pad + 8 * s, y0 - pad + 8 * s            # glare lines, top-left, 45 degrees
    for k in (4, 6.5, 9):
        d.line([(gx, gy + k * s), (gx + k * s, gy)], fill=COLOR, width=max(1, int(1.1 * s)))


def liana(d: ImageDraw.ImageDraw, a, b, s: float) -> None:
    """Hanging curve from a to b: teardrop start, swelling stroke, needle point at b."""
    ax, ay, bx, by = a[0] * s, a[1] * s, b[0] * s, b[1] * s
    sag = 70 * s
    c1 = (ax + (bx - ax) * 0.3, max(ay, by) + sag)
    c2 = (bx - (bx - ax) * 0.15, by + sag * 0.6)
    n = 260
    for i in range(n + 1):
        t = i / n
        m = 1 - t
        x = m ** 3 * ax + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t ** 3 * bx
        y = m ** 3 * ay + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t ** 3 * by
        w = (1.2 + 3.0 * math.sin(math.pi * min(t, 0.85) / 0.85 * 0.5) * (1 - max(0, t - 0.7) / 0.3)) * s
        d.ellipse((x - w, y - w, x + w, y + w), fill=COLOR)
    r = 4.5 * s                                              # teardrop at the start
    d.ellipse((ax - r, ay - r, ax + r, ay + r), fill=COLOR)
    # needle-point arrowhead along the final direction
    t = 0.97
    m = 1 - t
    px = m ** 3 * ax + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t ** 3 * bx
    py = m ** 3 * ay + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t ** 3 * by
    ang = math.atan2(by - py, bx - px)
    L, W = 22 * s, 7 * s
    base = (bx - L * math.cos(ang), by - L * math.sin(ang))
    nx, ny = -math.sin(ang) * W, math.cos(ang) * W
    d.polygon([(bx, by), (base[0] + nx, base[1] + ny), (base[0] + L * 0.25 * math.cos(ang), base[1] + L * 0.25 * math.sin(ang)),
               (base[0] - nx, base[1] - ny)], fill=COLOR)


def annotate(src: Path, dst: Path, box, label: str, label_at) -> Path:
    base = Image.open(src).convert("RGB")
    big = base.resize((base.width * SS, base.height * SS), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    window_box(d, box, SS)
    font = ImageFont.truetype(FONT, 26 * SS)
    lx, ly = label_at
    d.text((lx * SS, ly * SS), label, font=font, fill=COLOR)
    tw = d.textlength(label, font=font) / SS
    start = (lx + tw + 16, ly + 18)
    end = (box[0] - 19, (box[1] + box[3]) / 2 + 10)
    liana(d, start, end, SS)
    out = big.resize(base.size, Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, optimize=True)
    return dst


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("box", type=int, nargs=4)
    ap.add_argument("label")
    ap.add_argument("--label-at", type=int, nargs=2, required=True)
    a = ap.parse_args(argv)
    try:
        print(f"wrote {annotate(a.src, a.dst, tuple(a.box), a.label, tuple(a.label_at))}")
    except OSError as exc:
        print(f"annotate failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
