"""Build Nebuloria (.otf + .woff2) from segmented glyph crops.

Pipeline per glyph: crop PNG -> vtracer -> font units -> fix contour direction -> CFF.
Inputs: build/glyphs/*.json (written by segment.py) next to lc_*.png / uc_*.png crops.

Usage: python scripts/build_font.py [--glyphs build/glyphs] [--out dist]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.svgLib.path import parse_path

sys.path.insert(0, str(Path(__file__).parent))
from clean_svg import read_paths  # noqa: E402
from vectorize import trace  # noqa: E402
from ligatures import build_extras  # noqa: E402
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

FAMILY = "Nebuloria"
STYLE = "Regular"
VERSION = "1.500"
UPM = 1000
X_HEIGHT = 500
CAP_HEIGHT = 700
SIDEBEARING = {"lower": 65, "upper": 85}  # units each side of the spacing body
SPACE_WIDTH = 260
TRACE_SCALE = 3
OPEN_RIGHT = "LK"   # capitals whose open right side would be mistaken for the wire gap


@dataclass(frozen=True)
class Glyph:
    name: str
    char: str
    pen: RecordingPen
    advance: int


# ---------------------------------------------------------------- geometry
def split_contours(rec: RecordingPen) -> list[list[tuple]]:
    contours, cur = [], []
    for op, args in rec.value:
        cur.append((op, args))
        if op in ("closePath", "endPath"):
            contours.append(cur)
            cur = []
    if cur:
        contours.append(cur)
    return contours


def flatten(contour: list[tuple], steps: int = 8) -> list[tuple[float, float]]:
    pts, last = [], None
    for op, args in contour:
        if op == "moveTo" or op == "lineTo":
            last = args[0]
            pts.append(last)
        elif op == "curveTo" and last is not None:
            p0, (p1, p2, p3) = last, args
            for i in range(1, steps + 1):
                t = i / steps
                mt = 1 - t
                pts.append((
                    mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0],
                    mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1],
                ))
            last = p3
        elif op == "qCurveTo" and last is not None:
            last = args[-1]
            pts.append(last)
    return pts


def signed_area(pts: list[tuple[float, float]]) -> float:
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def inside(pt: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    x, y, hit = pt[0], pt[1], False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0:
            hit = not hit
    return hit


def orient_for_cff(rec: RecordingPen) -> RecordingPen:
    """Outer contours counter-clockwise, holes clockwise (by nesting depth)."""
    contours = split_contours(rec)
    polys = [flatten(c) for c in contours]
    out = RecordingPen()
    for i, (c, poly) in enumerate(zip(contours, polys)):
        if len(poly) < 3:
            continue
        depth = sum(1 for j, other in enumerate(polys) if j != i and len(other) > 2 and inside(poly[0], other))
        want_ccw = depth % 2 == 0
        is_ccw = signed_area(poly) > 0
        single = RecordingPen()
        single.value = list(c)
        single.replay(out if want_ccw == is_ccw else ReverseContourPen(out))
    return out


def squeeze_x(rec: RecordingPen, g0: float, g1: float, target: float) -> tuple[RecordingPen, float]:
    """Piecewise-linear x map: [g0, g1] becomes `target` wide, everything right of it shifts left."""
    width = g1 - g0
    if width <= target:
        return rec, 0.0
    removed = width - target

    def fx(x: float) -> float:
        if x <= g0:
            return x
        if x >= g1:
            return x - removed
        return g0 + (x - g0) * target / width

    out = RecordingPen()
    out.value = [(op, tuple((fx(a[0]), a[1]) if isinstance(a, tuple) else a for a in args)) for op, args in rec.value]
    return out, removed


# ---------------------------------------------------------------- glyphs
def glyph_name(ch: str) -> str:
    """a-z, A-Z keep their name; a traced pair 'La' becomes the ligature 'L_a.dlig'."""
    return ch if len(ch) == 1 else "_".join(ch) + ".dlig"


def load_glyph(crop: Path, meta: dict, ch: str, work: Path) -> Glyph:
    svg = trace(crop, work / f"{crop.stem}.svg", scale=TRACE_SCALE)
    rec = read_paths(svg)
    info = meta["glyphs"][ch]
    base, top = meta["baseline_px"], meta["top_px"]
    target = X_HEIGHT if meta["kind"] == "lower" else CAP_HEIGHT
    k = target / (base - top)
    # px (traced, xTRACE_SCALE, y down) -> font units (y up, baseline 0)
    to_units = (k / TRACE_SCALE, 0, 0, -k / TRACE_SCALE, 0, base * k)
    units = RecordingPen()
    rec.replay(TransformPen(units, to_units))
    bp = BoundsPen(None)
    units.replay(bp)
    if bp.bounds is None:
        raise ValueError(f"glyph {ch} is empty")
    # space from the heavy core, so hairline tails and tendrils may overhang (as in Langer)
    core_x0 = (info.get("core_x0", info["x0"]) - info["crop_x"]) * k
    core_x1 = (info.get("core_x1", info["x1"]) - info["crop_x"]) * k
    sb = SIDEBEARING[meta["kind"]]
    placed = RecordingPen()
    units.replay(TransformPen(placed, (1, 0, 0, 1, sb - core_x0, 0)))
    advance = round(core_x1 - core_x0 + 2 * sb)
    if len(ch) == 2 and "gap_x0" in info and ch[0] not in OPEN_RIGHT:  # L: its open counter is not a gap
        # traced pair: squeeze the wire gap back to the font's own spacing between the two letters
        g0 = (info["gap_x0"] - info["crop_x"]) * k + sb - core_x0
        g1 = (info["gap_x1"] - info["crop_x"]) * k + sb - core_x0
        target = SIDEBEARING["upper" if ch[0].isupper() else "lower"] + SIDEBEARING["lower"]
        placed, removed = squeeze_x(placed, g0, g1, target)
        advance = round(advance - removed)
    return Glyph(glyph_name(ch), ch, orient_for_cff(placed), advance)


def collect(glyph_dir: Path) -> list[Glyph]:
    """Load every glyph; sheets named fix-* replace earlier drawings of the same letter."""
    chosen: dict[str, tuple[dict, Path]] = {}
    metas = sorted(glyph_dir.glob("*.json"), key=lambda f: (f.name.startswith("fix-"), f.name))
    for meta_file in metas:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        for ch in meta["chars"]:
            chosen[ch] = (meta, glyph_dir / meta["glyphs"][ch]["crop"])
    glyphs = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for ch in sorted(chosen, key=lambda c: (c.islower(), c)):
            meta, crop = chosen[ch]
            if not crop.is_file():
                print(f"  skip {ch}: no crop {crop.name}", file=sys.stderr)
                continue
            glyphs.append(load_glyph(crop, meta, ch, work))
            print(f"  {ch}: advance {glyphs[-1].advance}  ({meta['sheet']})")
    return glyphs


# ---------------------------------------------------------------- font
def load_overlays(wire_dir: Path) -> dict[str, RecordingPen]:
    """Wires drawn over the font's own letters (scripts/wire_extract.py): build/wires/<pair>.svg."""
    import re
    overlays = {}
    for f in sorted(wire_dir.glob("*.svg")) if wire_dir.is_dir() else []:
        m = re.search(r'd="([^"]+)"', f.read_text(encoding="utf-8"))
        if m:
            rec = RecordingPen()
            parse_path(m.group(1), rec)
            overlays[f.stem] = rec
    return overlays


def build(glyphs: list[Glyph], out_dir: Path, hekwerk: bool = False,
          wire_dir: Path = Path("build/wires")) -> tuple[Path, Path]:
    if not glyphs:
        raise ValueError("no glyphs to build")
    traced_ligs = [g for g in glyphs if len(g.char) > 1]
    glyphs = [g for g in glyphs if len(g.char) == 1]
    extras, fea = build_extras(glyphs, SIDEBEARING["lower"], X_HEIGHT, CAP_HEIGHT, traced_ligs,
                               fence=hekwerk, overlays=load_overlays(wire_dir))
    family = f"{FAMILY} Hekwerk" if hekwerk else FAMILY
    stem = "nebuloria-hekwerk-regular" if hekwerk else "nebuloria-regular"
    order = [".notdef", "space", "nbspace"] + [g.name for g in glyphs] + [e.name for e in extras]
    cmap = {0x20: "space", 0xA0: "nbspace", **{ord(g.char): g.name for g in glyphs}}
    charstrings, metrics = {}, {}
    ymin, ymax = 0.0, float(CAP_HEIGHT)

    for name in ("space", "nbspace"):
        charstrings[name] = T2CharStringPen(SPACE_WIDTH, None).getCharString()
        metrics[name] = (SPACE_WIDTH, 0)
    nd = T2CharStringPen(500, None)
    nd.moveTo((50, 0)); nd.lineTo((450, 0)); nd.lineTo((450, 700)); nd.lineTo((50, 700)); nd.closePath()
    charstrings[".notdef"], metrics[".notdef"] = nd.getCharString(), (500, 50)

    for g in list(glyphs) + extras:
        pen = T2CharStringPen(g.advance, None)
        oriented = orient_for_cff(g.pen) if g in extras else g.pen
        oriented.replay(pen)
        charstrings[g.name] = pen.getCharString()
        bp = BoundsPen(None)
        g.pen.replay(bp)
        metrics[g.name] = (g.advance, round(bp.bounds[0]))
        ymin, ymax = min(ymin, bp.bounds[1]), max(ymax, bp.bounds[3])

    fb = FontBuilder(UPM, isTTF=False)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    ps = f"{family.replace(' ', '')}-{STYLE}"
    fb.setupCFF(ps, {"FullName": f"{family} {STYLE}", "FamilyName": family, "Weight": STYLE}, charstrings, {})
    fb.setupHorizontalMetrics(metrics)
    asc, desc = round(ymax) + 20, round(ymin) - 20  # never clip tendrils / descenders
    fb.setupHorizontalHeader(ascent=asc, descent=desc)
    # one typographic family "Nebuloria" with two styles: Regular and Hekwerk
    fb.setupNameTable({"familyName": family, "styleName": STYLE, "uniqueFontIdentifier": f"{ps};{VERSION}",
                       "fullName": f"{family} {STYLE}" if not hekwerk else f"{FAMILY} Hekwerk",
                       "psName": ps, "version": f"Version {VERSION}",
                       "typographicFamily": FAMILY, "typographicSubfamily": "Hekwerk" if hekwerk else STYLE,
                       "copyright": "Copyright 2026 Fabian Langer",
                       "designer": "Fabian Langer", "manufacturer": "Fabian Langer",
                       "licenseDescription": "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
                                             "This license is available with a FAQ at: https://openfontlicense.org",
                       "licenseInfoURL": "https://openfontlicense.org"})
    fb.setupOS2(sTypoAscender=asc, sTypoDescender=desc, sTypoLineGap=0, usWinAscent=asc, usWinDescent=-desc,
                sxHeight=X_HEIGHT, sCapHeight=CAP_HEIGHT, achVendID="NBLR", fsType=0, version=4,
                fsSelection=0x40 | 0x80)  # REGULAR + USE_TYPO_METRICS
    fb.setupPost()
    fb.font["head"].fontRevision = float(VERSION)
    out_dir.mkdir(parents=True, exist_ok=True)
    otf = out_dir / f"{stem}.otf"
    fb.save(str(otf))
    font = TTFont(str(otf))
    addOpenTypeFeaturesFromString(font, fea)   # dlig: windows + wires
    font.save(str(otf))
    woff2 = out_dir / f"{stem}.woff2"
    font = TTFont(str(otf))
    font.flavor = "woff2"
    font.save(str(woff2))
    return otf, woff2


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glyphs", type=Path, default=Path("build/glyphs"))
    ap.add_argument("--out", type=Path, default=Path("dist"))
    ap.add_argument("--hekwerk", action="store_true", help="also build 'Nebuloria Hekwerk' (windows in every pair)")
    a = ap.parse_args(argv)
    try:
        glyphs = collect(a.glyphs)
        wires = a.glyphs.parent / "wires"   # written by prepare_glyphs.py next to the glyphs
        otf, woff2 = build(glyphs, a.out, wire_dir=wires)
        if a.hekwerk:
            hotf, _ = build(glyphs, a.out, hekwerk=True, wire_dir=wires)
            print(f"built {hotf}")
    except (OSError, ValueError, KeyError) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    print(f"built {otf} and {woff2} with {len(glyphs)} glyphs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
