"""Cut a one-row glyph sheet into separate glyph crops and measure its metrics.

Usage: python scripts/segment.py <sheet.png> <chars> <out_dir> [--kind lower|upper]
  chars: the letters in the row, e.g. "abcdefg" (spaces ignored)

Writes <out_dir>/<name>.png per glyph and <out_dir>/<sheet-stem>.json with:
  baseline_px, top_px (x-height for lower, cap height for upper), glyph boxes.
Metrics use "strong rows" (rows where a glyph's ink is wide), so hairline
tendrils and teardrops do not distort baseline or x-height.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_opening, label

INK = 128           # grey level below which a pixel is ink
MIN_GAP = 6         # min empty columns between glyphs (px)
STRONG = 0.30       # a row is "strong" if its ink spans > 30% of glyph width
CORE_STEM = 0.07    # (kept for reference) stem thickness as share of x-/cap-height
CORE_BAND = (0.20, 0.80)  # rows of the x-/cap-height band that define a glyph's spacing body
NO_ASC_DESC = set("acemnorsuvwxz")       # lowercase letters that sit between baseline and x-height
NO_DESC_UPPER = set("ABCDEFGHIJKLMNOPRSTUVWXYZ")


def column_runs(ink: np.ndarray) -> list[tuple[int, int]]:
    cols = ink.any(axis=0)
    runs, start, gap = [], None, 0
    for x, on in enumerate(cols):
        if on:
            if start is None:
                start = x
            gap = 0
            end = x
        elif start is not None:
            gap += 1
            if gap >= MIN_GAP:
                runs.append((start, end))
                start, gap = None, 0
    if start is not None:
        runs.append((start, end))
    return runs


def merge_to(runs: list[tuple[int, int]], n: int, ink: np.ndarray) -> list[tuple[int, int]]:
    """Merge stray fragments (detached teardrops, dots) until there are n runs."""
    runs = list(runs)
    while len(runs) > n:
        # merge the run with the least ink into its nearest neighbour
        mass = [ink[:, a:b + 1].sum() for a, b in runs]
        i = int(np.argmin(mass))
        if i == 0:
            j = 1
        elif i == len(runs) - 1:
            j = i - 1
        else:
            j = i - 1 if runs[i][0] - runs[i - 1][1] <= runs[i + 1][0] - runs[i][1] else i + 1
        a, b = min(i, j), max(i, j)
        runs[a:b + 1] = [(runs[a][0], runs[b][1])]
    return runs


def split_to(runs: list[tuple[int, int]], n: int, ink: np.ndarray) -> list[tuple[int, int]]:
    """Split touching glyphs: cut the widest run at its thinnest ink column (middle 30-70%)."""
    runs = list(runs)
    while len(runs) < n:
        i = max(range(len(runs)), key=lambda k: runs[k][1] - runs[k][0])
        a, b = runs[i]
        lo, hi = a + int((b - a) * 0.3), a + int((b - a) * 0.7)
        col = ink[:, lo:hi + 1].sum(axis=0)
        cut = lo + int(np.argmin(col))
        runs[i:i + 1] = [(a, cut), (cut + 1, b)]
    return runs


def token_id(token: str) -> str:
    """File-safe id that survives case-insensitive file systems: 'La' -> 'uc-L_lc-a', '?' -> 'u003F'."""
    return "_".join(("uc-" + c) if c.isupper() else ("lc-" + c) if c.isalnum() else f"u{ord(c):04X}"
                    for c in token)


def pair_gap(mask: np.ndarray, top: int, bot: int, stem_min: int) -> tuple[int, int] | None:
    """Columns between the two letters of a traced pair where only a thin wire passes."""
    band = mask[top:bot + 1, :]
    cols = band.sum(axis=0)
    xs = np.where(mask.any(axis=0))[0]
    if xs.size == 0:
        return None
    thin = cols <= stem_min            # empty or just a hairline wire crossing
    best, start = None, None
    for x in range(int(xs[0]), int(xs[-1]) + 1):
        if thin[x] and start is None:
            start = x
        elif not thin[x] and start is not None:
            if start > xs[0] and (best is None or x - start > best[1] - best[0]):
                best = (start, x - 1)
            start = None
    return (int(best[0]), int(best[1])) if best else None


def assign_components(ink: np.ndarray, runs: list[tuple[int, int]]) -> list[np.ndarray]:
    """Give every connected ink shape wholly to the run it overlaps most."""
    labels, count = label(ink, structure=np.ones((3, 3), bool))
    masks = [np.zeros_like(ink) for _ in runs]
    for comp in range(1, count + 1):
        ys, xs = np.where(labels == comp)
        overlap = [np.count_nonzero((xs >= a) & (xs <= b)) for a, b in runs]
        masks[int(np.argmax(overlap))][ys, xs] = True
    return masks


def strong_rows(ink: np.ndarray) -> tuple[int, int]:
    width = max(1, ink.any(axis=0).sum())
    rows = ink.sum(axis=1) / width
    ys = np.where(rows > STRONG)[0]
    if ys.size == 0:
        ys = np.where(ink.any(axis=1))[0]
    return int(ys[0]), int(ys[-1])


def segment(sheet: Path, chars: str, out_dir: Path, kind: str,
            baseline_override: float | None = None, top_override: float | None = None) -> dict:
    chars = chars.split() if " " in chars.strip() else list(chars)   # letters, or space-separated pairs
    img = Image.open(sheet).convert("L")
    ink = np.asarray(img) < INK
    runs = column_runs(ink)
    if len(runs) < len(chars):
        print(f"  {sheet.name}: {len(runs)} pieces for {len(chars)} glyphs, splitting touching letters", file=sys.stderr)
        runs = split_to(runs, len(chars), ink)
    runs = merge_to(runs, len(chars), ink)
    masks = assign_components(ink, runs)
    out_dir.mkdir(parents=True, exist_ok=True)
    boxes, tops, bottoms = {}, [], []
    ref = NO_ASC_DESC if kind == "lower" else NO_DESC_UPPER
    for ch, mask in zip(chars, masks):
        ys, xs = np.where(mask)
        if ys.size == 0:
            raise ValueError(f"{sheet.name}: glyph '{ch}' is empty")
        y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
        top, bot = strong_rows(mask[y0:y1 + 1, x0:x1 + 1])
        top, bot = int(top + y0), int(bot + y0)
        boxes[ch] = {"x0": x0, "x1": x1, "y0": y0, "y1": y1, "strong_top": top, "strong_bottom": bot}
        if all(c in ref for c in ch):
            tops.append(top)
            bottoms.append(bot)
    if baseline_override is not None and top_override is not None:
        bottoms, tops = [baseline_override], [top_override]   # manual metrics (mixed or single-glyph sheets)
    if not tops:
        raise ValueError(f"{sheet.name}: no reference letters to measure metrics; pass --baseline/--top")
    band = median(bottoms) - median(tops)
    stem_min = max(3, round(band * CORE_STEM))
    grey = np.asarray(img)
    for ch, mask in zip(chars, masks):
        box = boxes[ch]
        # spacing body = ALL ink (hairline diagonals included) in the middle of the
        # x-/cap-height band; flags on top, baseline tails, teardrops and descender
        # loops lie outside it and may overhang into the neighbour's space
        band_top, band_bot = int(median(tops)), int(median(bottoms))
        mid_top = band_top + int((band_bot - band_top) * CORE_BAND[0])
        mid_bot = band_top + int((band_bot - band_top) * CORE_BAND[1])
        core = np.zeros_like(mask)
        core[mid_top:mid_bot + 1, :] = mask[mid_top:mid_bot + 1, :]
        # ignore stray hairline specks: keep columns with a meaningful amount of ink
        core &= binary_opening(mask, structure=np.ones((2, 2), bool))
        cx = np.where(core.any(axis=0))[0]
        box["core_x0"], box["core_x1"] = (int(cx[0]), int(cx[-1])) if cx.size else (box["x0"], box["x1"])
        if len(ch) == 2:
            gap = pair_gap(mask, mid_top, mid_bot, stem_min)
            if gap:
                box["gap_x0"], box["gap_x1"] = gap
        # glyph-only image: other glyphs' fragments are blanked out
        keep = binary_dilation(mask, iterations=2)
        only = np.where(keep, grey, 250).astype("uint8")
        pad = 12
        cx0, cx1 = max(0, box["x0"] - pad), min(img.width, box["x1"] + pad + 1)
        crop_name = f"{sheet.stem}__{token_id(ch)}.png"
        Image.fromarray(only[:, cx0:cx1], mode="L").save(out_dir / crop_name)
        box["crop_x"], box["crop"] = cx0, crop_name
    meta = {
        "sheet": sheet.name, "kind": kind, "chars": chars,
        "baseline_px": float(median(bottoms)), "top_px": float(median(tops)), "glyphs": boxes,
    }
    (out_dir / f"{sheet.stem}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sheet", type=Path)
    ap.add_argument("chars")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--kind", choices=["lower", "upper"], default="lower")
    ap.add_argument("--baseline", type=float, help="override measured baseline (px)")
    ap.add_argument("--top", type=float, help="override measured x-height / cap-height top (px)")
    a = ap.parse_args(argv)
    try:
        m = segment(a.sheet, a.chars, a.out_dir, a.kind, a.baseline, a.top)
    except (OSError, ValueError) as exc:
        print(f"segment failed: {exc}", file=sys.stderr)
        return 1
    print(f"{a.sheet.name}: {len(m['chars'])} glyphs, baseline {m['baseline_px']:.0f}px, top {m['top_px']:.0f}px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
