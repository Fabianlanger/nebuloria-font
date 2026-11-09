"""Package the download zip for a GitHub Release.

Usage: python scripts/package_release.py [--out build/release]

Writes <out>/Nebuloria.zip. The asset name never changes, so the link
  https://github.com/Fabianlanger/nebuloria-font/releases/latest/download/Nebuloria.zip
always downloads the newest release. The folder inside the zip carries the version.
The zip is NOT committed (dist/*.zip is ignored); upload it to the release instead:
  gh release create v1.6 build/release/Nebuloria.zip --title "Nebuloria v1.6" --notes "..."
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
ASSET_NAME = "Nebuloria.zip"
FILES = {
    "fonts/otf/Nebuloria-Regular.otf": "dist/nebuloria-regular.otf",
    "fonts/otf/Nebuloria-Hekwerk.otf": "dist/nebuloria-hekwerk-regular.otf",
    "fonts/webfonts/nebuloria-regular.woff2": "dist/nebuloria-regular.woff2",
    "fonts/webfonts/nebuloria-hekwerk-regular.woff2": "dist/nebuloria-hekwerk-regular.woff2",
    "OFL.txt": "OFL.txt",
    "Nebuloria-Design-Book.pdf": "docs/Nebuloria-Design-Book.pdf",
    "Nebuloria-Style-Guide.pdf": "docs/Nebuloria-Style-Guide.pdf",
}


def font_version() -> str:
    rev = TTFont(str(ROOT / "dist/nebuloria-regular.otf"))["head"].fontRevision
    return f"{rev:.1f}"


def package(out_dir: Path) -> Path:
    missing = [src for src in FILES.values() if not (ROOT / src).is_file()]
    if missing:
        raise FileNotFoundError(f"missing release files: {', '.join(missing)}")
    folder = f"Nebuloria-v{font_version()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / ASSET_NAME
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in FILES.items():
            z.write(ROOT / src, f"{folder}/{arc}")
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "build/release")
    a = ap.parse_args(argv)
    try:
        out = package(a.out)
    except (OSError, KeyError) as exc:
        print(f"package failed: {exc}", file=sys.stderr)
        return 1
    print(f"{out}  ({out.stat().st_size // 1024} KB, version {font_version()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
