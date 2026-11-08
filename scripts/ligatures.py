"""Nebuloria ligatures: window ligature (R13) and wire ligatures, as `dlig`.

Window: a separate glyph `window` is INSERTED between a right-stem letter and a
left-stem letter (chained context + multiple substitution), so one component
serves every pair. It spans the gap between the two stems' spacing bodies.

Wires: for a few named pairs, a ligature glyph = first + second + a hairline
wire from the first letter's top-right to the second letter's top-left.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen

# classes from the Nebuloria rules (R13, i and l included: "the iron fence")
RIGHT_STEM = "adhilmnu"
LEFT_STEM = "bhiklmnpru"
WIRE_PAIRS = ["Fa", "La", "ng", "er", "re", "ce", "ge"]

# v1.4: lighter, as in the image renders: the window lives in the existing gap,
# everything is hairline, no filled corners, one window per word (fence = ss01)
WINDOW_ADVANCE = 50    # small extra space the window adds between the two stems
BRIDGE = 10            # thickness of the x-height and baseline bridges (hairline)
PANE_INSET = 14        # distance of the pane outline from stems and bridges
PANE_LINE = 5          # pane outline thickness (hairline)
CHAMFER = 26           # 45-degree corner cut of the pane
GLARE = (34, 52, 70)   # lengths of the three 45-degree glare lines
GLARE_W = 5            # glare line thickness
WIRE_W = 9             # wire thickness: same family as the tendrils
MAX_WORD = 12          # "one window per word": look back this many glyphs


@dataclass(frozen=True)
class Extra:
    name: str
    pen: RecordingPen
    advance: int


def _poly(pen, pts) -> None:
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()


def _bar(pen, a, b, w) -> None:
    """Straight bar of width w from a to b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1
    ox, oy = -dy / n * w / 2, dx / n * w / 2
    _poly(pen, [(a[0] + ox, a[1] + oy), (a[0] - ox, a[1] - oy), (b[0] - ox, b[1] - oy), (b[0] + ox, b[1] + oy)])


def _octagon(x0, y0, x1, y1, c) -> list[tuple[float, float]]:
    return [(x0 + c, y1), (x1 - c, y1), (x1, y1 - c), (x1, y0 + c), (x1 - c, y0), (x0 + c, y0), (x0, y0 + c), (x0, y1 - c)]


def window_glyph(sidebearing: int, x_height: int) -> Extra:
    """Hairline bridges + hairline glass pane (chamfered) + glare lines, stem to stem."""
    pen = RecordingPen()
    x0, x1 = -sidebearing, WINDOW_ADVANCE + sidebearing          # stem faces
    top = x_height
    # thin bridges at x-height and baseline, tucked 8 units into the stems
    _poly(pen, [(x0 - 8, top - BRIDGE), (x1 + 8, top - BRIDGE), (x1 + 8, top), (x0 - 8, top)])
    _poly(pen, [(x0 - 8, 0), (x1 + 8, 0), (x1 + 8, BRIDGE), (x0 - 8, BRIDGE)])
    # glass pane: hairline outline of a chamfered octagon (ring = outer + inner contour)
    px0, px1 = x0 + PANE_INSET, x1 - PANE_INSET
    py0, py1 = BRIDGE + PANE_INSET, top - BRIDGE - PANE_INSET
    _poly(pen, _octagon(px0, py0, px1, py1, CHAMFER))
    inner = _octagon(px0 + PANE_LINE, py0 + PANE_LINE, px1 - PANE_LINE, py1 - PANE_LINE, CHAMFER - PANE_LINE * 0.4)
    _poly(pen, inner[::-1])
    # glare: three 45-degree hairlines (lower-left -> upper-right), top-left and bottom-right
    g0x, g0y = px0 + PANE_LINE + 10, py1 - PANE_LINE - 10
    g1x, g1y = px1 - PANE_LINE - 10, py0 + PANE_LINE + 10
    for k in GLARE:
        _bar(pen, (g0x, g0y - k), (g0x + k, g0y), GLARE_W)
        _bar(pen, (g1x - k, g1y), (g1x, g1y + k), GLARE_W)
    return Extra("window", pen, WINDOW_ADVANCE)


# ---------------------------------------------------------------- wires
def _points(rec: RecordingPen) -> list[tuple[float, float]]:
    pts = []
    for _, args in rec.value:
        pts.extend(a for a in args if isinstance(a, tuple))
    return pts


def _anchor(rec: RecordingPen, x_height: float, side: str, min_x: float | None = None) -> tuple[float, float]:
    band = [p for p in _points(rec) if 0.55 * x_height <= p[1] <= 1.15 * x_height]
    if min_x is not None:
        band = [p for p in band if p[0] >= min_x]   # the end must lie clearly right of the start
    if not band:
        raise ValueError("no outline points near the x-height for a wire anchor")
    if side == "right":
        return max(band, key=lambda p: p[0] + 0.6 * p[1])
    return min(band, key=lambda p: p[0] - 0.6 * p[1])


def _wire(pen, a, b, x_height: float) -> None:
    """A hanging liana from a to b: a round U-sag between two high points (as in Langer v0.4).

    The sag grows with the gap, so a short gap gets a shallow round dip and never a spike.
    """
    d = max(b[0] - a[0], 0.25 * x_height)
    sag = max(0.12 * x_height, min(0.32 * x_height, 0.6 * d))
    c1 = (a[0] + 0.28 * d, min(a[1], b[1]) - sag)
    c2 = (b[0] - 0.28 * d, min(a[1], b[1]) - sag)
    steps, left, right = 64, [], []
    curve = []
    for i in range(steps + 1):
        t = i / steps
        m = 1 - t
        curve.append((m**3 * a[0] + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t**3 * b[0],
                      m**3 * a[1] + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t**3 * b[1]))
    for i, p in enumerate(curve):
        q0, q1 = curve[max(0, i - 1)], curve[min(steps, i + 1)]
        ang = math.atan2(q1[1] - q0[1], q1[0] - q0[0])
        nx, ny = -math.sin(ang) * WIRE_W / 2, math.cos(ang) * WIRE_W / 2
        left.append((p[0] + nx, p[1] + ny))
        right.append((p[0] - nx, p[1] - ny))
    _poly(pen, left + right[::-1])


def wire_ligature(first, second, x_height: float, cap_height: float) -> Extra:
    pen = RecordingPen()
    first.pen.replay(pen)
    shifted = RecordingPen()
    second.pen.replay(TransformPen(shifted, (1, 0, 0, 1, first.advance, 0)))
    shifted.replay(pen)
    # both anchors sit near the x-height, also for capitals (F: middle arm, L: stem), as in Langer
    a = _anchor(first.pen, x_height, "right")
    b = _anchor(shifted, x_height, "left", min_x=a[0] + 0.18 * x_height)
    _wire(pen, a, b, x_height)
    return Extra(f"{first.name}_{second.name}.dlig", pen, first.advance + second.advance)


# ---------------------------------------------------------------- features
def build_extras(glyphs, sidebearing: int, x_height: int, cap_height: int,
                 traced_ligs=(), fence: bool = False, overlays=None) -> tuple[list[Extra], str]:
    """Wire sources, best first:
    overlays    pair -> wire pen in font units drawn over the font's OWN letters (wire_extract.py)
    traced_ligs pair glyphs drawn whole by the image model
    fallback    code-drawn liana
    """
    by_char = {g.char: g for g in glyphs}
    traced = {g.char: g for g in traced_ligs}
    overlays = overlays or {}
    extras = [window_glyph(sidebearing, x_height)]
    wires = []
    for pair in WIRE_PAIRS:
        if pair[0] in by_char and pair[1] in by_char:
            first, second = by_char[pair[0]], by_char[pair[1]]
            if pair in overlays:
                pen = RecordingPen()
                first.pen.replay(pen)
                second.pen.replay(TransformPen(pen, (1, 0, 0, 1, first.advance, 0)))
                overlays[pair].replay(pen)
                lig = Extra(f"{first.name}_{second.name}.dlig", pen, first.advance + second.advance)
            elif pair in traced:
                t = traced[pair]
                lig = Extra(t.name, t.pen, t.advance)
            else:
                lig = wire_ligature(by_char[pair[0]], by_char[pair[1]], x_height, cap_height)
            extras.append(lig)
            wires.append((pair, by_char[pair[0]].name, by_char[pair[1]].name, lig.name))
    # a wired pair keeps the window behaviour of its outer letters:
    # F_a ends in a right stem (a), n_g starts with a left stem (n)
    right_names = [by_char[c].name for c in RIGHT_STEM if c in by_char]
    left_names = [by_char[c].name for c in LEFT_STEM if c in by_char]
    for pair, _, _, lig in wires:
        if pair[1] in RIGHT_STEM:
            right_names.append(lig)
        if pair[0] in LEFT_STEM:
            left_names.append(lig)
    right, left = " ".join(right_names), " ".join(left_names)
    insert = "\n".join(f"    sub {n} by {n} window;" for n in right_names)
    wire_subs = "\n".join(f"    sub {a} {b} by {lig};" for _, a, b, lig in wires)
    letters = " ".join([g.name for g in glyphs] + [w[3] for w in wires])
    # one window per word: skip a pair if a window already appeared up to MAX_WORD glyphs back
    ignores = "\n".join(
        "    ignore sub window " + "@LETTER " * k + "@RIGHT_STEM' @LEFT_STEM;" for k in range(MAX_WORD + 1)
    )
    fea = f"""
@RIGHT_STEM = [{right}];
@LEFT_STEM = [{left}];
@LETTER = [{letters}];

lookup INSERT_WINDOW {{
{insert}
}} INSERT_WINDOW;

lookup WIRES {{
{wire_subs}
}} WIRES;

lookup ONE_WINDOW_PER_WORD {{
{ignores}
    sub @RIGHT_STEM' lookup INSERT_WINDOW @LEFT_STEM;
}} ONE_WINDOW_PER_WORD;

lookup ALL_WINDOWS {{
    sub @RIGHT_STEM' lookup INSERT_WINDOW @LEFT_STEM;
}} ALL_WINDOWS;

# dlig: wires + {"a window in EVERY qualifying pair (Hekwerk family)" if fence else "at most ONE window per word (readable)"}
feature dlig {{
    lookup WIRES;
    lookup {"ALL_WINDOWS" if fence else "ONE_WINDOW_PER_WORD"};
}} dlig;

# ss01: the other window behaviour, so both families can switch
feature ss01 {{
    lookup {"ONE_WINDOW_PER_WORD" if fence else "ALL_WINDOWS"};
}} ss01;
"""
    return extras, fea
