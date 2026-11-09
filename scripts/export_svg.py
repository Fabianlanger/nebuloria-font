"""Export a sequence of glyphs from the font as one handover-ready SVG.

Usage: python scripts/export_svg.py <font.otf> "<glyph names>" <out.svg> [--height 200]
  glyph names are space separated; use "|" for a word space.
  e.g. "F_a.dlig window b i a n | L_a.dlig window n_g.dlig e_r.dlig"

Output: filled outlines, tight viewBox, no transforms,
no embedded fonts, fill="currentColor".
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).parent))
from clean_svg import NUMBER, _fmt  # noqa: E402


def export(font_path: Path, names: str, out: Path, height: float, margin: float = 6) -> Path:
    font = TTFont(str(font_path))
    gs, hmtx = font.getGlyphSet(), font["hmtx"]
    space = hmtx["space"][0]
    rec, x = RecordingPen(), 0
    for name in names.split():
        if name == "|":
            x += space
            continue
        if name not in gs:
            raise ValueError(f"glyph '{name}' not in font")
        gs[name].draw(TransformPen(rec, (1, 0, 0, 1, x, 0)))
        x += hmtx[name][0]
    bp = BoundsPen(None)
    rec.replay(bp)
    x0, y0, x1, y1 = bp.bounds
    s = height / (y1 - y0)
    flipped = RecordingPen()   # font units (y up) -> SVG (y down), tight to the drawing
    rec.replay(TransformPen(flipped, (s, 0, 0, -s, margin - x0 * s, margin + y1 * s)))
    sp = SVGPathPen(None)
    flipped.replay(sp)
    d = NUMBER.sub(lambda m: _fmt(float(m.group(0))), sp.getCommands())
    w, h = (x1 - x0) * s + 2 * margin, (y1 - y0) * s + 2 * margin
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">'
        f'<path fill="currentColor" d="{d}"/></svg>\n', encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("font", type=Path)
    ap.add_argument("names")
    ap.add_argument("out", type=Path)
    ap.add_argument("--height", type=float, default=200)
    a = ap.parse_args(argv)
    try:
        export(a.font, a.names, a.out, a.height)
    except (OSError, ValueError, KeyError) as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 1
    print(f"exported {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
