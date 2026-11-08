"""Glyphs built from glyphs that were drawn (v1.6): accented letters, dotless i, ellipsis, middle dot, dashes.

Accented letters are composites, as in any professional font: the drawn letter plus a drawn accent,
so an é is always exactly the e of the font. Nothing here is drawn by an image model.

Used by build_font.py; `make(name, char, pen, advance)` creates a Glyph.
"""
from __future__ import annotations

import unicodedata

from fontTools.agl import UV2AGL

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen

MARK_GAP = 55        # units between the top of a letter and the bottom of its accent
CEDILLA_OVERLAP = 20  # units the cedilla reaches up into the letter it hangs from

# accent character -> letters that get it (lowercase and capitals)
ACCENTS = {
    "´": "eaiouEAIOU",   # acute: é á í ó ú
    "`": "eaiouEAIOU",        # grave: è à ì ò ù
    "ˆ": "eaiouEAIOU",   # circumflex: ê â î ô û
    "¨": "eaiouEAIOU",   # dieresis: ë ä ï ö ü
    "˜": "nN",           # tilde: ñ
    "¸": "cC",           # cedilla: ç
}
COMBINING = {"´": "́", "`": "̀", "ˆ": "̂", "¨": "̈", "˜": "̃",
             "¸": "̧"}


def bounds(pen: RecordingPen) -> tuple[float, float, float, float]:
    bp = BoundsPen(None)
    pen.replay(bp)
    if bp.bounds is None:
        raise ValueError("empty glyph")
    return bp.bounds


def moved(pen: RecordingPen, dx: float, dy: float, sx: float = 1.0) -> RecordingPen:
    out = RecordingPen()
    pen.replay(TransformPen(out, (sx, 0, 0, 1, dx, dy)))
    return out


def joined(*pens: RecordingPen) -> RecordingPen:
    out = RecordingPen()
    for p in pens:
        p.replay(out)
    return out


def contours(pen: RecordingPen) -> list[RecordingPen]:
    parts, cur = [], RecordingPen()
    for op, args in pen.value:
        cur.value.append((op, args))
        if op in ("closePath", "endPath"):
            parts.append(cur)
            cur = RecordingPen()
    return parts


def dotless(i_pen: RecordingPen, x_height: int) -> RecordingPen:
    """The i without its diamond dot: drop every contour that lies wholly above the x-height."""
    keep = [c for c in contours(i_pen) if bounds(c)[1] < x_height * 0.92]
    return joined(*keep)


def stretched(pen: RecordingPen, delta: float) -> RecordingPen:
    """Make a bar `delta` units longer by moving its right half; the 45-degree end cuts stay intact."""
    x0, _, x1, _ = bounds(pen)
    mid = (x0 + x1) / 2
    out = RecordingPen()
    out.value = [(op, tuple((a[0] + delta, a[1]) if isinstance(a, tuple) and a[0] > mid else a for a in args))
                 for op, args in pen.value]
    return out


def derive(glyphs: list, make, x_height: int, cap_height: int) -> list:
    by_char = {g.char: g for g in glyphs}
    out = []

    i = by_char.get("i")
    if i is not None:
        out.append(make("dotlessi", "ı", dotless(i.pen, x_height), i.advance))
        by_char["ı"] = out[-1]

    for accent, letters in ACCENTS.items():
        mark = by_char.get(accent)
        if mark is None:
            continue
        mx0, my0, mx1, my1 = bounds(mark.pen)
        for letter in letters:
            base = by_char.get("ı" if letter == "i" else letter)
            if base is None:
                continue
            char = unicodedata.normalize("NFC", letter + COMBINING[accent])
            cx = base.advance / 2
            if accent == "¸":   # cedilla hangs below the baseline
                dy = CEDILLA_OVERLAP - my1
            else:
                top = cap_height if letter.isupper() else x_height
                dy = top + MARK_GAP - my0
            placed = moved(mark.pen, cx - (mx0 + mx1) / 2, dy)
            name = UV2AGL.get(ord(char), f"uni{ord(char):04X}")
            out.append(make(name, char, joined(base.pen, placed), base.advance))

    period = by_char.get(".")
    if period is not None:
        px0, py0, px1, py1 = bounds(period.pen)
        step = period.advance * 0.78
        dots = joined(*(moved(period.pen, k * step, 0) for k in range(3)))
        out.append(make("ellipsis", "…", dots, round(period.advance + 2 * step)))
        lift = x_height / 2 - (py0 + py1) / 2
        out.append(make("periodcentered", "·", moved(period.pen, 0, lift), period.advance))

    hyphen = by_char.get("-")
    if hyphen is not None:
        hx0, _, hx1, _ = bounds(hyphen.pen)
        # en dash clearly longer than the (long) drawn hyphen, em dash about one em
        for name, char, ink in (("endash", "\u2013", 1.5 * (hx1 - hx0)), ("emdash", "\u2014", 960)):
            delta = max(0.0, ink - (hx1 - hx0))
            out.append(make(name, char, stretched(hyphen.pen, delta), round(hyphen.advance + delta)))
    return out
