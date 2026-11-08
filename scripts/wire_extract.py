"""Extract a black wire drawn over a grey wire_ref image and store it in font units.

Usage: python scripts/wire_extract.py <drawn.png> <ref.json> <out.svg> [--dark 90]
The grey letters are ignored (only pixels darker than --dark count as wire).
<out.svg> holds one path in font units (y up, origin = first glyph origin).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import label
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

sys.path.insert(0, str(Path(__file__).parent))
from clean_svg import read_paths  # noqa: E402
from vectorize import trace  # noqa: E402

TRACE_SCALE = 3
MIN_SPECK = 40  # px: drop isolated dark specks


def extract(drawn: Path, ref: Path, out: Path, dark: int) -> Path:
    meta = json.loads(ref.read_text(encoding="utf-8"))
    img = Image.open(drawn).convert("L")
    if tuple(img.size) != tuple(meta["canvas"]):
        raise ValueError(f"drawn image is {img.size}, reference grid is {meta['canvas']}")
    wire = np.asarray(img) < dark
    labels, n = label(wire, structure=np.ones((3, 3), bool))
    for comp in range(1, n + 1):
        if np.count_nonzero(labels == comp) < MIN_SPECK:
            wire[labels == comp] = False
    if not wire.any():
        raise ValueError("no dark wire pixels found")
    with tempfile.TemporaryDirectory() as tmp:
        bw = Path(tmp) / "wire.png"
        Image.fromarray(np.where(wire, 0, 255).astype("uint8"), mode="L").save(bw)
        svg = trace(bw, Path(tmp) / "wire.svg", scale=TRACE_SCALE)
        rec = read_paths(svg)
    s, ox, by = meta["scale"], meta["origin_x"], meta["baseline_y"]
    k = 1 / (TRACE_SCALE * s)
    units = RecordingPen()
    rec.replay(TransformPen(units, (k, 0, 0, -k, -ox / s, by / s)))
    sp = SVGPathPen(None)
    units.replay(sp)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg"><path d="{sp.getCommands()}"/></svg>\n', encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("drawn", type=Path)
    ap.add_argument("ref", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--dark", type=int, default=90)
    a = ap.parse_args(argv)
    try:
        extract(a.drawn, a.ref, a.out, a.dark)
    except (OSError, ValueError) as exc:
        print(f"wire_extract failed: {exc}", file=sys.stderr)
        return 1
    print(f"wire -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
