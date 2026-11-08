"""Build the PDF documents (design book, style guide) from their HTML sources.

Usage: python scripts/build_docs.py
  - fills the image credits into docs/book/design-book.html (<!-- CREDITS-TABLE -->)
  - prints docs/book/design-book.html  -> docs/Nebuloria-Design-Book.pdf
  - prints docs/style-guide/style-guide.html -> docs/Nebuloria-Style-Guide.pdf
Requires Microsoft Edge or another Chromium (set $CHROME) for headless printing.
"""
from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EDGE_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]
DOCS = [
    (ROOT / "docs/book/design-book.html", ROOT / "docs/Nebuloria-Design-Book.pdf"),
    (ROOT / "docs/style-guide/style-guide.html", ROOT / "docs/Nebuloria-Style-Guide.pdf"),
]


def edge() -> Path:
    """Microsoft Edge on Windows; any Chromium elsewhere (or the browser named in $CHROME)."""
    for p in EDGE_CANDIDATES:
        if p.is_file():
            return p
    if os.environ.get("CHROME") and Path(os.environ["CHROME"]).is_file():
        return Path(os.environ["CHROME"])
    for name in ("msedge", "chromium", "chromium-browser", "google-chrome", "chrome"):
        found = shutil.which(name)
        if found:
            return Path(found)
    raise FileNotFoundError("No Edge or Chromium found for headless PDF printing (set $CHROME to its path)")


def credits_table() -> str:
    data = json.loads((ROOT / "docs/book/img/insp/credits.json").read_text(encoding="utf-8"))
    rows = []
    for c in data.values():
        rows.append(
            f"<tr><td>{html.escape(c['title'])}</td><td>{html.escape(c['artist'] or 'unknown')}</td>"
            f"<td>{html.escape(c['license'])}</td></tr>"
        )
    return ("<table style=\"font-size:6.6pt\"><tr><th>Image</th><th>Author</th><th>Licence</th></tr>"
            + "".join(rows) + "</table>")


def prepare(src: Path) -> Path:
    """Return the HTML file to print (with generated parts filled in)."""
    text = src.read_text(encoding="utf-8")
    if "<!-- CREDITS-TABLE -->" not in text:
        return src
    out = src.with_name(src.stem + ".print.html")
    out.write_text(text.replace("<!-- CREDITS-TABLE -->", credits_table()), encoding="utf-8")
    return out


def print_pdf(src: Path, pdf: Path) -> None:
    page = prepare(src)
    tmp = pdf.with_suffix(".tmp.pdf")
    tmp.unlink(missing_ok=True)
    cmd = [str(edge()), "--headless=new", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files",
           "--no-pdf-header-footer", "--virtual-time-budget=15000",
           f"--print-to-pdf={tmp}", page.as_uri()]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    if not tmp.is_file():
        raise OSError(f"Edge did not write {tmp}")
    try:
        tmp.replace(pdf)
    except PermissionError as exc:
        raise OSError(f"{pdf.name} is locked (open in a PDF viewer?). Close it and run again. New version: {tmp.name}") from exc
    print(f"  {pdf.relative_to(ROOT)}  ({pdf.stat().st_size // 1024} KB)")


def main() -> int:
    ok = True
    for src, pdf in DOCS:
        if not src.is_file():
            print(f"  skip {src.relative_to(ROOT)} (not written yet)")
            continue
        try:
            print_pdf(src, pdf)
        except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
            print(f"  failed {src.name}: {exc}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
