"""Clean a vtracer SVG into a handover-compliant outline SVG.

Handover §4.1: outlined paths (fills, no strokes), tight viewBox, no transforms,
no embedded fonts, fill="currentColor".

Usage: python scripts/clean_svg.py <traced.svg> <out.svg> [--margin 8] [--height 0]
  --height  if > 0, scale the result so the drawing is this many units tall.
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path

SVG_NS = "{http://www.w3.org/2000/svg}"
NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def _fmt(v: float) -> str:
    """Round to 1 decimal, drop trailing zeros (keeps SVG small)."""
    t = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if t in ("-0", "") else t


TRANSLATE = re.compile(r"translate\(\s*([-\d.eE]+)[ ,]+([-\d.eE]+)\s*\)")


def read_paths(src: Path) -> RecordingPen:
    """Parse all black paths, applying their translate() transforms."""
    root = ET.parse(src).getroot()
    rec = RecordingPen()
    found = 0
    for node in root.iter(f"{SVG_NS}path"):
        fill = (node.get("fill") or "#000000").lower()
        if fill not in ("#000000", "#000", "black"):
            continue  # skip background / white shapes
        dx = dy = 0.0
        tf = node.get("transform")
        if tf:
            m = TRANSLATE.fullmatch(tf.strip())
            if not m:
                raise ValueError(f"unsupported transform: {tf}")
            dx, dy = float(m.group(1)), float(m.group(2))
        parse_path(node.get("d", ""), TransformPen(rec, (1, 0, 0, 1, dx, dy)))
        found += 1
    if not found:
        raise ValueError(f"no black paths in {src}")
    return rec


def bounds(rec: RecordingPen) -> tuple[float, float, float, float]:
    bp = BoundsPen(None)
    rec.replay(bp)
    if bp.bounds is None:
        raise ValueError("drawing is empty")
    return bp.bounds


def clean(src: Path, dst: Path, margin: float = 8, height: float = 0) -> Path:
    rec = read_paths(src)
    x0, y0, x1, y1 = bounds(rec)
    s = height / (y1 - y0) if height > 0 else 1.0
    out = RecordingPen()
    rec.replay(TransformPen(out, (s, 0, 0, s, (margin - x0 * s), (margin - y0 * s))))
    w = (x1 - x0) * s + 2 * margin
    h = (y1 - y0) * s + 2 * margin
    sp = SVGPathPen(None)
    out.replay(sp)
    d = NUMBER.sub(lambda m: _fmt(float(m.group(0))), sp.getCommands())
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
        f'width="{w:.0f}" height="{h:.0f}">'
        f'<path fill="currentColor" fill-rule="evenodd" d="{d}"/></svg>\n'
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(svg, encoding="utf-8")
    return dst


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--margin", type=float, default=8)
    ap.add_argument("--height", type=float, default=0)
    a = ap.parse_args(argv)
    try:
        out = clean(a.src, a.dst, a.margin, a.height)
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"clean failed: {exc}", file=sys.stderr)
        return 1
    print(f"cleaned {a.src} -> {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
