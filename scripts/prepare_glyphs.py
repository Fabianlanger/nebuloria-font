"""Recreate build/glyphs and build/wires from the drawings in assets/ (reproducible build).

Usage: python scripts/prepare_glyphs.py [--out build]
Order matters: later sheets (fix-*, lig-*) replace earlier drawings of the same letter.
Manual metrics are used where a sheet has no reliable reference letters or where
pointed letters (v, w) fooled the automatic baseline.
"""
from __future__ import annotations

import argparse
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
]
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
