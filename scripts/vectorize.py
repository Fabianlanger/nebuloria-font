"""Trace a black-on-light glyph image into a clean single-colour SVG outline.

Usage: python scripts/vectorize.py <input.png> <output.svg> [--threshold 128] [--scale 2]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np
import vtracer
from PIL import Image, ImageFilter


def binarize(src: Path, threshold: int, scale: int) -> Image.Image:
    """Return a pure black/white image, upscaled for smoother curves."""
    img = Image.open(src).convert("L")
    if scale > 1:
        img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
    # light blur only: removes JPEG-like noise but keeps needle points and crisp chamfers
    img = img.filter(ImageFilter.GaussianBlur(radius=0.45 * scale))
    arr = np.asarray(img)
    bw = np.where(arr < threshold, 0, 255).astype("uint8")
    return Image.fromarray(bw, mode="L").convert("RGB")


def trace(src: Path, dst: Path, threshold: int = 128, scale: int = 2) -> Path:
    if not src.is_file():
        raise FileNotFoundError(f"input image not found: {src}")
    bw = binarize(src, threshold, scale)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_png = Path(tmp) / "bw.png"
        bw.save(tmp_png)
        vtracer.convert_image_to_svg_py(
            str(tmp_png),
            str(dst),
            colormode="binary",
            mode="spline",
            filter_speckle=8 * scale,
            corner_threshold=40,  # lower = more sharp corners preserved
            length_threshold=3.5,
            splice_threshold=45,
            path_precision=2,
        )
    return dst


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--threshold", type=int, default=128)
    ap.add_argument("--scale", type=int, default=2)
    args = ap.parse_args(argv)
    try:
        out = trace(args.src, args.dst, args.threshold, args.scale)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"trace failed: {exc}", file=sys.stderr)
        return 1
    print(f"traced {args.src} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
