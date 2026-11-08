"""Find freely licensed reference images on Wikimedia Commons, with licence metadata.

Usage: python scripts/commons_search.py <queries.json> <out_dir> [--per 6]
queries.json: {"slug": "search terms", ...}
Writes <out_dir>/<slug>_<n>.jpg thumbnails, <out_dir>/candidates.json and a
contact sheet <out_dir>/<slug>_sheet.jpg per query for quick visual review.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

from PIL import Image, ImageDraw

API = "https://commons.wikimedia.org/w/api.php"
UA = "NebuloriaDesignBook/1.0 (type design research; contact via project repository)"
FREE = re.compile(r"(cc0|public domain|pd|cc by(-sa)? ?[1-4]\.\d|cc-by)", re.I)


def get(url: str, tries: int = 4) -> bytes:
    """GET with a polite User-Agent; back off on HTTP 429 (rate limit)."""
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise OSError("unreachable")


def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def search(query: str, per: int) -> list[dict]:
    params = {
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": "6", "gsrlimit": str(per * 2), "prop": "imageinfo",
        "iiprop": "url|extmetadata|size", "iiurlwidth": "900",
    }
    data = json.loads(get(API + "?" + urllib.parse.urlencode(params)))
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
        if not FREE.search(lic) or info.get("width", 0) < 800:
            continue
        out.append({
            "title": p["title"], "page": info.get("descriptionurl"), "thumb": info.get("thumburl"),
            "full": info.get("url"), "license": lic,
            "license_url": strip_html(meta.get("LicenseUrl", {}).get("value", "")),
            "artist": strip_html(meta.get("Artist", {}).get("value", ""))[:160],
            "credit": strip_html(meta.get("Credit", {}).get("value", ""))[:160],
        })
        if len(out) >= per:
            break
    return out


def contact_sheet(paths: list[Path], dst: Path) -> None:
    thumbs = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((420, 300))
        thumbs.append(im)
    if not thumbs:
        return
    sheet = Image.new("RGB", (430 * len(thumbs), 330), "white")
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(thumbs):
        sheet.paste(im, (i * 430 + 5, 25))
        d.text((i * 430 + 8, 5), str(i), fill="black")
    sheet.save(dst, quality=85)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("queries", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--per", type=int, default=6)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    queries = json.loads(a.queries.read_text(encoding="utf-8"))
    existing = a.out / "candidates.json"
    result = json.loads(existing.read_text(encoding="utf-8")) if existing.is_file() else {}
    for slug, q in queries.items():
        try:
            found = search(q, a.per)
        except (OSError, ValueError) as exc:
            print(f"  {slug}: search failed: {exc}", file=sys.stderr)
            continue
        paths = []
        for i, c in enumerate(found):
            dst = a.out / f"{slug}_{i}.jpg"
            try:
                Image.open(io.BytesIO(get(c["thumb"]))).convert("RGB").save(dst, quality=88)
                c["file"] = dst.name
                paths.append(dst)
            except (OSError, ValueError) as exc:
                print(f"  {slug}_{i}: download failed: {exc}", file=sys.stderr)
            time.sleep(0.3)  # be polite to the API
        contact_sheet(paths, a.out / f"{slug}_sheet.jpg")
        result[slug] = found
        print(f"  {slug}: {len(paths)} candidates")
        time.sleep(2)
    (a.out / "candidates.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
