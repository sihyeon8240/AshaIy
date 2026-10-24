#!/usr/bin/env python3
"""Validate local links and PDF bytes in the rendered deployment artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.IGNORECASE)
RESOURCES = {
    "a": ("href",),
    "link": ("href",),
    "img": ("src",),
    "script": ("src",),
    "object": ("data",),
    "iframe": ("src",),
    "embed": ("src",),
    "source": ("src",),
    "video": ("src", "poster"),
}


class PageLinks(HTMLParser):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.links: list[str] = []
        self.anchors: set[str] = set()
        self.books: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "article" and "data-book-slug" in attributes:
            self.books.append(attributes["data-book-slug"] or "")
        anchor = attributes.get("id") or (
            attributes.get("name") if tag == "a" else None
        )
        if anchor:
            self.anchors.add(anchor)
        for attribute in RESOURCES.get(tag, ()):
            value = attributes.get(attribute)
            if value:
                self.links.append(value)


def local_target(root: Path, source: Path, link: str, base_path: str) -> Path | None:
    url = urlsplit(link)
    if url.scheme or url.netloc:
        return None
    path = unquote(url.path)
    if not path:
        return source
    if path.startswith("/"):
        if base_path and path != base_path and not path.startswith(base_path + "/"):
            raise ValueError(f"local URL is outside the Pages base path: {link}")
        target = root / path.removeprefix(base_path).lstrip("/")
    else:
        target = source.parent / path
    target = target.resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"local URL escapes the site: {link}")
    if target.is_dir():
        target /= "index.html"
    return target


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(
    destination: Path, snapshot: Path, *, book_data: Path, base_path: str = ""
) -> None:
    root = destination.resolve()
    if not (root / "index.html").is_file():
        raise ValueError("rendered site is missing index.html")
    pages = {
        path: PageLinks(path.read_text(encoding="utf-8"))
        for path in root.rglob("*.html")
    }
    links = [(path, link) for path, page in pages.items() for link in page.links]
    for path in root.rglob("*.css"):
        links.extend((path, link.strip()) for link in CSS_URL.findall(path.read_text()))
    for source, link in links:
        target = local_target(root, source, link, base_path.rstrip("/"))
        if target is None:
            continue
        if not target.is_file():
            raise ValueError(f"missing local link target in {source.name}: {link}")
        fragment = unquote(urlsplit(link).fragment)
        if fragment and target in pages and fragment not in pages[target].anchors:
            raise ValueError(f"missing HTML anchor in {source.name}: {link}")

    data = json.loads(book_data.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("unsupported generated book data")
    books = data.get("books")
    if not isinstance(books, list) or not all(
        isinstance(book, dict)
        and isinstance(book.get("slug"), str)
        and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", book["slug"])
        for book in books
    ):
        raise ValueError("invalid generated book list")
    expected = {book["slug"] for book in books}
    if len(expected) != len(books):
        raise ValueError("duplicate generated book slug")
    home = pages[root / "index.html"]
    if len(home.books) != len(expected) or set(home.books) != expected:
        raise ValueError("rendered book cards differ from the generated book list")
    for directory, suffix in (("books", ".html"), ("pdf", ".pdf")):
        path = root / directory
        actual = {entry.name for entry in path.iterdir()} if path.is_dir() else set()
        if actual != {slug + suffix for slug in expected}:
            raise ValueError(
                f"rendered {directory} set differs from the generated book list"
            )
    home_targets = {
        local_target(root, root / "index.html", link, base_path.rstrip("/"))
        for link in home.links
    }
    for slug in expected:
        detail = root / "books" / f"{slug}.html"
        pdf = root / "pdf" / f"{slug}.pdf"
        if detail not in home_targets or pdf not in home_targets:
            raise ValueError(f"missing home page book links: {slug}")
        if not any(
            local_target(root, detail, link, base_path.rstrip("/")) == pdf
            for link in pages[detail].links
        ):
            raise ValueError(f"missing detail page PDF link: {slug}")
    for pdf in sorted((root / "pdf").glob("*.pdf")):
        original = snapshot / "pdf" / pdf.name
        if not original.is_file() or checksum(pdf) != checksum(original):
            raise ValueError(f"published PDF differs from the snapshot: {pdf.name}")
        with pdf.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise ValueError(f"invalid PDF header: {pdf.name}")
    print(
        f"Validated {len(pages)} rendered pages, local links, and snapshot PDF bytes."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--book-data", type=Path, required=True)
    parser.add_argument("--base-path", default="")
    args = parser.parse_args()
    try:
        check(
            args.destination,
            args.snapshot,
            book_data=args.book_data,
            base_path=args.base_path,
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
