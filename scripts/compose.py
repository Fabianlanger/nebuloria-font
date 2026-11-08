"""Compose traced words into one wordmark SVG on a shared baseline and x-height.

Usage:
  python scripts/compose.py <out.svg> --trace-scale 3 --gap 0.45 \
      <traced.svg>:<baseline_px>:<xheight_top_px> [...]

Baseline / x-height are measured in the ORIGINAL image pixels; the traced SVG is
assumed to be `trace-scale` times larger. Words are scaled to the x-height of
the first word and placed left to right with a gap of `gap` x-heights.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

sys.path.insert(0, str(Path(__file__).parent))
from clean_svg import NUMBER, _fmt, read_paths  # noqa: E402


def parse_spec(spec: str) -> tuple[Path, float, float]:
    try:
        path, base, top = spec.rsplit(":", 2)
        return Path(path), float(base), float(top)
    except ValueError as exc:
        raise ValueError(f"bad word spec '{spec}', expected file:baseline:xtop") from exc


def compose(out: Path, specs: list[str], trace_scale: float, gap: float, height: float) -> Path:
    words = [parse_spec(s) for s in specs]
    target_x = None
    cursor = 0.0
    merged = RecordingPen()
    for path, base, top in words:
        rec = read_paths(path)
        xh = (base - top) * trace_scale
        if xh <= 0:
            raise ValueError(f"x-height must be positive for {path}")
        target_x = target_x or xh
        k = target_x / xh
        # baseline -> y = 0, scale to shared x-height
        placed = RecordingPen()
        rec.replay(TransformPen(placed, (k, 0, 0, k, 0, -base * trace_scale * k)))
        bp = BoundsPen(None)
        placed.replay(bp)
        x0, _, x1, _ = bp.bounds
        placed.replay(TransformPen(merged, (1, 0, 0, 1, cursor - x0, 0)))
        cursor += (x1 - x0) + gap * target_x
    # normalise: tight bounds, chosen output height, margin
    bp = BoundsPen(None)
    merged.replay(bp)
    x0, y0, x1, y1 = bp.bounds
    s = height / (y1 - y0)
    m = 8
    final = RecordingPen()
    merged.replay(TransformPen(final, (s, 0, 0, s, m - x0 * s, m - y0 * s)))
    sp = SVGPathPen(None)
    final.replay(sp)
    d = NUMBER.sub(lambda mt: _fmt(float(mt.group(0))), sp.getCommands())
    w, h = (x1 - x0) * s + 2 * m, (y1 - y0) * s + 2 * m
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">'
        f'<path fill="currentColor" fill-rule="evenodd" d="{d}"/></svg>\n',
        encoding="utf-8",
    )
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", type=Path)
    ap.add_argument("words", nargs="+")
    ap.add_argument("--trace-scale", type=float, default=3)
    ap.add_argument("--gap", type=float, default=0.45)
    ap.add_argument("--height", type=float, default=400)
    a = ap.parse_args(argv)
    try:
        out = compose(a.out, a.words, a.trace_scale, a.gap, a.height)
    except (OSError, ValueError) as exc:
        print(f"compose failed: {exc}", file=sys.stderr)
        return 1
    print(f"composed -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
