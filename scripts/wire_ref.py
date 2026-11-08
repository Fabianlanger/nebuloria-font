"""Render a letter pair from the font in light grey on a known grid (for wire-only drawing).

The image model then adds ONLY a black wire; thresholding the black pixels isolates
the wire, and the known grid maps it back to font units exactly.

Usage: python scripts/wire_ref.py <font.otf> <pair> <out.svg>
Writes <out.svg> and <out>.json with the px <-> font-unit mapping.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

CANVAS = (1536, 1024)
SCALE = 0.9          # px per font unit
ORIGIN_X = 260       # px, left edge of the first glyph's origin
BASELINE_Y = 760     # px
GREY = "#b8b8b8"


def render(font_path: Path, pair: str, out: Path) -> dict:
    font = TTFont(str(font_path))
    cmap, gs, hmtx = font.getBestCmap(), font.getGlyphSet(), font["hmtx"]
    paths, x = [], 0
    for ch in pair:
        name = cmap.get(ord(ch))
        if name is None:
            raise ValueError(f"'{ch}' is not in the font")
        pen = SVGPathPen(gs)
        gs[name].draw(pen)
        tx = ORIGIN_X + x * SCALE
        paths.append(f'<path transform="translate({tx:.1f},{BASELINE_Y}) scale({SCALE},{-SCALE})" d="{pen.getCommands()}"/>')
        x += hmtx[name][0]
    w, h = CANVAS
    out.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<rect width="{w}" height="{h}" fill="#fbf9f4"/><g fill="{GREY}">{"".join(paths)}</g></svg>\n',
        encoding="utf-8",
    )
    meta = {"pair": pair, "canvas": CANVAS, "scale": SCALE, "origin_x": ORIGIN_X, "baseline_y": BASELINE_Y}
    out.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        raise SystemExit(2)
    try:
        render(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]))
    except (OSError, ValueError, KeyError) as exc:
        print(f"wire_ref failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(f"wrote {sys.argv[3]}")
