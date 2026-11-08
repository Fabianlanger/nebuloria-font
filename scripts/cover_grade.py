"""Grade a cover photo into a background that keeps the type the focus.

Looks:
  romantic  (default) warm golden-hour grade, full colour, light vignette,
            dimming mainly behind the text zones. Hopeful, never gloomy.
  specimen  the first version: dark, desaturated olive grade (kept for reference).
The original file is never changed; the graded version is written separately.

Usage: python scripts/cover_grade.py <in.png> <out.jpg> [--look romantic|specimen]
           [--title-zone 0.5] [--foot-zone 0.18]
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


@dataclass(frozen=True)
class Look:
    exposure: float
    blur: float
    saturation: float
    warm: tuple[float, float, float]
    floor: tuple[float, float, float]
    vignette: float
    title_dim: float
    foot_dim: float
    glow: float
    grain: float


LOOKS = {
    "romantic": Look(exposure=0.78, blur=0.9, saturation=1.02, warm=(1.08, 0.98, 0.84),
                     floor=(0.07, 0.045, 0.035), vignette=0.42, title_dim=0.48, foot_dim=0.38,
                     glow=0.10, grain=0.012),
    "specimen": Look(exposure=0.42, blur=2.2, saturation=0.72, warm=(1.06, 1.00, 0.80),
                     floor=(0.055, 0.060, 0.040), vignette=0.75, title_dim=0.45, foot_dim=0.0,
                     glow=0.0, grain=0.018),
}


def grade(src: Path, dst: Path, look: Look, title_zone: float, foot_zone: float) -> Path:
    img = Image.open(src).convert("RGB")
    img.thumbnail((1800, 1800))
    sharp = np.asarray(img).astype(np.float32) / 255.0
    soft = np.asarray(img.filter(ImageFilter.GaussianBlur(14 * img.width / 1600))).astype(np.float32) / 255.0
    if look.blur:
        img = img.filter(ImageFilter.GaussianBlur(look.blur * img.width / 1600))
    a = np.asarray(img).astype(np.float32) / 255.0
    a = np.clip(a + look.glow * soft * soft, 0, 1)            # soft "Orton" bloom in the highlights

    grey = a.mean(axis=2, keepdims=True)
    a = grey + (a - grey) * look.saturation
    a = np.clip(a * np.array(look.warm) * look.exposure, 0, 1) ** 1.05

    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.55) / (h / 2)) ** 2)
    vignette = 1 - look.vignette * np.clip(r - 0.45, 0, 1) ** 1.8
    top = np.clip(1 - yy / (h * title_zone), 0, 1)          # behind the title and intro
    bottom = np.clip((yy - h * (1 - foot_zone)) / (h * foot_zone), 0, 1) if foot_zone else 0
    dim = (1 - look.title_dim * top ** 1.2) * (1 - look.foot_dim * bottom ** 1.2)
    a = a * (vignette * dim)[..., None]

    floor = np.array(look.floor)
    a = floor + a * (1 - floor)                                # warm, never pure black
    rng = np.random.default_rng(7)
    a = a + rng.normal(0, look.grain, a.shape[:2])[..., None]
    out = Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, quality=88, optimize=True)
    del sharp
    return dst


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--look", choices=sorted(LOOKS), default="romantic")
    ap.add_argument("--title-zone", type=float, default=0.5)
    ap.add_argument("--foot-zone", type=float, default=0.18)
    a = ap.parse_args(argv)
    if a.src.resolve() == a.dst.resolve():
        print("refusing to overwrite the original", file=sys.stderr)
        return 1
    try:
        grade(a.src, a.dst, LOOKS[a.look], a.title_zone, a.foot_zone)
    except (OSError, ValueError) as exc:
        print(f"grade failed: {exc}", file=sys.stderr)
        return 1
    print(f"graded ({a.look}) -> {a.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
