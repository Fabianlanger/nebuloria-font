"""Mark one button on a screenshot in Nebuloria style (README how-tos).

Box   = a Nebuloria "window": 45-degree chamfered frame, hairline inner frame, three glare lines.
Arrow = a hanging liana: starts in a small teardrop, swells, tapers to a needle point.
Label = set in Nebuloria itself.

Usage: python scripts/annotate_download.py <screenshot.png> <out.png> x0 y0 x1 y1 "Label" --label-at x y
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COLOR = (249, 200, 82)       # Nebuloria yellow
FONT = str(Path(__file__).resolve().parents[2] / "dist" / "nebuloria-regular.otf")   # our own typeface
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
    sag = 110 * s
    c1 = (ax + (bx - ax) * 0.3, max(ay, by) + sag)
    c2 = (bx - (bx - ax) * 0.15, by + sag * 0.6)
    n = 260
    for i in range(int(n * 0.9) + 1):     # stop before the head so the tip stays sharp
        t = i / n
        m = 1 - t
        x = m ** 3 * ax + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t ** 3 * bx
        y = m ** 3 * ay + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t ** 3 * by
        w = (2.0 + 5.0 * math.sin(math.pi * min(t, 0.85) / 0.85 * 0.5)) * s
        d.ellipse((x - w, y - w, x + w, y + w), fill=COLOR)
    r = 9 * s                                                # teardrop at the start
    d.ellipse((ax - r, ay - r, ax + r, ay + r), fill=COLOR)
    t = 0.93
    m = 1 - t
    px = m ** 3 * ax + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t ** 3 * bx
    py = m ** 3 * ay + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t ** 3 * by
    leaf_head(d, (bx, by), math.atan2(by - py, bx - px), s)


def leaf_head(d: ImageDraw.ImageDraw, tip, ang, s: float) -> None:
    """Arrowhead in Nebuloria style: a leaf with a needle tip, curved flanks and a 45-degree cut back."""
    L, W = 88 * s, 24 * s
    ux, uy = math.cos(ang), math.sin(ang)          # forward
    nx, ny = -uy, ux                               # side

    def p(f, g):                                   # f along (0 = back, 1 = tip), g across
        return (tip[0] - L * (1 - f) * ux + g * nx, tip[1] - L * (1 - f) * uy + g * ny)

    pts = []
    for i in range(41):                            # upper flank: back corner -> tip, convex
        f = 0.12 + 0.88 * i / 40
        pts.append(p(f, W * math.sin(math.pi * (1 - f) / 0.88 * 0.5) ** 1.1))
    for i in range(41):                            # lower flank: tip -> back corner
        f = 1 - 0.88 * i / 40
        pts.append(p(f, -W * math.sin(math.pi * (1 - f) / 0.88 * 0.5) ** 1.1))
    pts.append(p(0.0, -W * 0.35))                  # 45-degree chamfered back cut, notch to the stem
    pts.append(p(0.22, 0))
    pts.append(p(0.0, W * 0.35))
    d.polygon(pts, fill=COLOR)


def annotate(src: Path, dst: Path, box, label: str, label_at) -> Path:
    base = Image.open(src).convert("RGB")
    big = base.resize((base.width * SS, base.height * SS), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    window_box(d, box, SS)
    font = ImageFont.truetype(FONT, 104 * SS)
    lx, ly = label_at
    d.text((lx * SS, ly * SS), label, font=font, fill=COLOR)
    tw = d.textlength(label, font=font) / SS
    start = (lx + tw + 30, ly + 72)
    end = (box[0] - 24, box[3] + 26)
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
