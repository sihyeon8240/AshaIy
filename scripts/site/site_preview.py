#!/usr/bin/env python3
"""Build, serve, or test the website with the local toolchain and PDFs."""

from __future__ import annotations

import argparse
import functools
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.books.book_manifest import load_manifest
from scripts.site.check_site_output import check as check_output

ROOT = Path(__file__).resolve().parents[2]


def require_tool(*names: str) -> str:
    for name in names:
        executable = shutil.which(name)
        if executable:
            return executable
    raise ValueError(
        f"required tool not found: {' or '.join(names)}; "
        "use the development image with the site tools installed"
    )


def build() -> Path:
    jekyll = require_tool("jekyll")
    books = [book for book in load_manifest()["books"] if book["site"]]
    pdfs = {book["slug"]: ROOT / "build" / book["slug"] / "book.pdf" for book in books}
    missing = [
        slug
        for slug, pdf in pdfs.items()
        if not pdf.is_file() or pdf.stat().st_size == 0
    ]
    if missing:
        commands = "; ".join(f"ashaiy book build --book {slug}" for slug in missing)
        raise ValueError(f"missing or empty local PDFs; build them first: {commands}")

    subprocess.run([sys.executable, "scripts/site/site_pages.py"], cwd=ROOT, check=True)
    destination = ROOT / "build/site-preview"
    staging = Path(tempfile.mkdtemp(prefix=".site-preview-", dir=ROOT / "build"))
    candidate = staging / "next"
    previous = staging / "previous"
    installed = False
    try:
        render(jekyll, candidate, pdfs)
        check_output(candidate, candidate, book_data=ROOT / "site/_data/books.json")
        if destination.exists():
            os.replace(destination, previous)
        try:
            os.replace(candidate, destination)
        except BaseException:
            if previous.exists():
                os.replace(previous, destination)
            raise
        installed = True
    finally:
        if installed or not previous.exists():
            shutil.rmtree(staging)
        else:
            print(f"Previous preview retained at {previous}", file=sys.stderr)
    print(f"Built local site: {destination}", flush=True)
    return destination


def render(jekyll: str, destination: Path, pdfs: dict[str, Path]) -> None:
    subprocess.run(
        [
            jekyll,
            "build",
            "--source",
            "site",
            "--destination",
            str(destination),
            "--disable-disk-cache",
        ],
        cwd=ROOT,
        check=True,
    )
    pdf_directory = destination / "pdf"
    pdf_directory.mkdir(parents=True, exist_ok=True)
    for slug, source in pdfs.items():
        shutil.copyfile(source, pdf_directory / f"{slug}.pdf")


def test() -> None:
    require_tool("jekyll")
    require_tool("chromium", "chromium-browser")
    if importlib.util.find_spec("playwright") is None:
        raise ValueError("Playwright missing; install .github/requirements-ci.txt")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-t",
            ".",
            "-s",
            "tests",
            "-p",
            "test_site_*.py",
            "-v",
        ],
        cwd=ROOT,
        check=True,
    )


def serve(destination: Path, port: int) -> None:
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(destination))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Preview: http://localhost:{port} (Ctrl+C to stop)", flush=True)
        server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "serve", "test"))
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        if args.action == "test":
            test()
        else:
            destination = build()
            if args.action == "serve":
                serve(destination, args.port)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
