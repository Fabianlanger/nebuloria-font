"""Recreate build/glyphs and build/wires from the drawings in assets/ (reproducible build).

Usage: python scripts/prepare_glyphs.py [--out build]
Order matters: later sheets (fix-*, lig-*) replace earlier drawings of the same letter.
Manual metrics are used where a sheet has no reliable reference letters or where
pointed letters (v, w) fooled the automatic baseline.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from segment import segment  # noqa: E402
from wire_extract import extract  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "assets/sheets"

# (sheet, letters, kind, baseline override px, top override px)
SHEETS = [
    ("lc-1-abcdefg.png", "abcdefg", "lower", None, None),
    ("lc-2-hijklmn.png", "hijklmn", "lower", None, None),
    ("lc-3-opqrstu.png", "opqrstu", "lower", None, None),
    ("lc-4-vwxyz.png", "vwxyz", "lower", 585, 380),           # v/w points fooled the auto baseline
    ("uc-1-ABCDEFG.png", "ABCDEFG", "upper", None, None),
    ("uc-2-HIJKLMN.png", "HIJKLMN", "upper", None, None),
    ("uc-3-OPQRSTU.png", "OPQRSTU", "upper", None, None),
    ("uc-4-VWXYZ.png", "VWXYZ", "upper", None, None),
    ("fix-t.png", "t", "lower", 680, 402),
    ("fix-q.png", "q", "lower", 647, 356),
    ("fix-I.png", "I", "upper", 681, 238),
    ("fix-2-CGKMV.png", "CGKMV", "upper", None, None),
    ("fix-3-WXY.png", "WXY", "upper", None, None),
    ("fix-4-mnux.png", "mnux", "lower", None, None),
    ("fix-5-bmn.png", "bmn", "lower", None, None),
    ("fix-6-C.png", "C", "upper", None, None),
    ("fix-7-b.png", "b", "lower", 1005, 527),
    ("lig-1-La-ng-er-Fa.png", "La ng er Fa", "lower", None, None),
    ("lig-2-re-ce-ge.png", "re ce ge", "lower", None, None),
    # v1.6: figures, punctuation, symbols, accents. The first letter of each sheet (H or n)
    # is only a size reference: it gives baseline and cap/x-height, then it is dropped.
    ("fig-1-01234.png", "H 0 1 2 3 4", "upper", None, None),
    ("fig-2-56789.png", "H 5 6 7 8 9", "upper", None, None),
    ("punct-1-stops.png", "n . , : ; ! ? - ( )", "lower", None, None),
    ("punct-2-quotes.png", "n ' \" \u2018 \u2019 \u201c \u201d & /", "lower", None, None),
    ("punct-3-symbols.png", "H + % # @ \u20ac", "upper", None, None),
    ("accents-1-marks.png", "n \u00b4 ` \u02c6 \u00a8 \u02dc \u00b8", "lower", None, None),
]
# reference letters on these sheets: measured, never built
REFERENCE_ONLY = {"fig-1-01234.png": "H", "fig-2-56789.png": "H", "punct-1-stops.png": "n",
                  "punct-2-quotes.png": "n", "punct-3-symbols.png": "H", "accents-1-marks.png": "n"}
# (drawn wire image, reference grid, pair)
WIRES = [("wire-Fa-drawn.png", "../refs/wire-Fa.json", "Fa")]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "build")
    a = ap.parse_args(argv)
    glyphs, wires = a.out / "glyphs", a.out / "wires"
    for d in (glyphs, wires):
        shutil.rmtree(d, ignore_errors=True)
    try:
        for sheet, letters, kind, base, top in SHEETS:
            m = segment(S / sheet, letters, glyphs, kind, base, top)
            drop = REFERENCE_ONLY.get(sheet)
            if drop:
                m["chars"] = [c for c in m["chars"] if c != drop]
                (glyphs / m["glyphs"].pop(drop)["crop"]).unlink(missing_ok=True)
                (glyphs / f"{Path(sheet).stem}.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
            print(f"  {sheet}: {len(m['chars'])} glyphs")
        for drawn, ref, pair in WIRES:
            extract(S / drawn, (S / ref).resolve(), wires / f"{pair}.svg", dark=90)
            print(f"  wire {pair}")
    except (OSError, ValueError) as exc:
        print(f"prepare failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
