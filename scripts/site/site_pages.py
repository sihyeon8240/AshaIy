#!/usr/bin/env python3
"""Generate deterministic Jekyll book pages from the canonical manifest."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.books.book_manifest import STATUS_LABELS, load_manifest
from scripts.lean.lean_coverage import (
    book_content_metrics,
    book_lean_metrics,
    registered_results,
)
from scripts.repository.config.validation_patterns import validation_pattern
from scripts.repository.file_updates import source_updates, write_updates

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = REPO_ROOT / "site"
SITE_FIELDS = ("slug", "title", "status", "order", "site", "release", "label_prefix")


def source_revision() -> str:
    """Identify the source checkout paired with the published PDF snapshot."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except OSError, subprocess.SubprocessError:
        # Exported sources can still render without Git metadata.
        return ""
    return result.stdout.strip()


def snapshot_revision() -> str:
    revision = os.environ.get("SITE_SNAPSHOT_SHA", "")
    if revision:
        if not re.fullmatch(validation_pattern("git_commit"), revision):
            raise ValueError("SITE_SNAPSHOT_SHA must be a full snapshot commit SHA")
        return revision
    return source_revision()


def site_books(manifest: dict) -> list[dict]:
    selected = [source for source in manifest["books"] if source["site"]]
    registered = registered_results() if selected else {}
    revision = snapshot_revision() if selected else ""
    source_sha = source_revision() if selected else ""
    books = []
    for source in selected:
        book = {field: source.get(field) for field in SITE_FIELDS}
        book["status_label"] = STATUS_LABELS[source["status"]]
        book["snapshot_revision"] = revision
        book["source_revision"] = source_sha
        book["url"] = f"/books/{source['slug']}.html"

        lean = book_lean_metrics(source["slug"], registered=registered)
        book["lean_verified"] = lean["verified"]
        book["lean_total"] = lean["total"]
        book["lean_coverage"] = lean["percentage"]
        content = book_content_metrics(source["slug"])
        book["sections_total"] = content["sections"]
        book["sections_written"] = content["written"]
        books.append(book)
    return books


def render_site_page(book: dict) -> str:
    """Keep routing and presentation separate from the generated book data."""
    front_matter = {
        "layout": "book",
        "stylesheet": "book",
        "edit_path": "site/_layouts/book.html",
        "book_slug": book["slug"],
    }
    return (
        "---\n"
        + yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False)
        + "---\n"
    )


def render_site(manifest: dict) -> dict[str, str]:
    books = site_books(manifest)
    return {
        "_data/books.json": json.dumps(
            {"schema_version": 1, "books": books}, ensure_ascii=False, indent=2
        )
        + "\n",
        **{f"books/{book['slug']}.html": render_site_page(book) for book in books},
    }


def generate(
    *,
    check: bool = False,
    site_dir: Path = SITE_DIR,
    book: str | None = None,
    skip_disabled: bool = False,
    verify_output: bool = False,
) -> int:
    with source_updates(REPO_ROOT, check=check):
        return _generate(
            check=check,
            site_dir=site_dir,
            book=book,
            skip_disabled=skip_disabled,
            verify_output=verify_output,
        )


def _generate(
    *,
    check: bool,
    site_dir: Path,
    book: str | None,
    skip_disabled: bool,
    verify_output: bool,
) -> int:
    manifest = load_manifest()
    if book:
        registered = {item["slug"]: item for item in manifest["books"]}
        if book not in registered:
            raise ValueError(f"book is not registered in config/books.yml: {book}")
        if not registered[book]["site"]:
            if skip_disabled:
                print(f"Skipped site generation for disabled book: {book}")
                return 0
            raise ValueError(
                f"book is not enabled for site in config/books.yml: {book}"
            )
    outputs = render_site(manifest)
    if book:
        outputs = {
            name: content
            for name, content in outputs.items()
            if name in {"_data/books.json", f"books/{book}.html"}
        }
    if check:
        return validate_site(outputs, site_dir, book=book)

    write_updates({site_dir / name: content for name, content in outputs.items()})
    pages_dir = site_dir / "books"
    if not book and pages_dir.is_dir():
        for path in pages_dir.iterdir():
            if path.relative_to(site_dir).as_posix() not in outputs:
                if path.is_dir() and not path.is_symlink():
                    raise ValueError(f"unexpected directory in generated pages: {path}")
                path.unlink()

    count = len(outputs) - 1
    print(f"Generated book data and {count} site book page(s)")
    if verify_output:
        return validate_site(outputs, site_dir, book=book)
    return 0


def validate_site(
    outputs: dict[str, str], site_dir: Path, *, book: str | None = None
) -> int:
    pages_dir = site_dir / "books"
    actual_names = (
        {path.relative_to(site_dir).as_posix() for path in pages_dir.iterdir()}
        if pages_dir.is_dir()
        else set()
    )
    stale = [
        name
        for name, expected in outputs.items()
        if not (site_dir / name).is_file()
        or (site_dir / name).read_text(encoding="utf-8") != expected
    ]
    orphaned = sorted(actual_names - outputs.keys()) if not book else []
    if stale or orphaned:
        for name in sorted(stale):
            print(f"error: generated site page is stale: {name}", file=sys.stderr)
        for name in orphaned:
            print(f"error: orphan generated site page: {name}", file=sys.stderr)
        return 1
    print(f"Validated book data and {len(outputs) - 1} generated site book page(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-disabled", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--check", action="store_true", help="fail instead of updating stale output"
    )
    parser.add_argument(
        "--book", metavar="SLUG", help="limit page generation to one site-enabled book"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SITE_DIR,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    try:
        return generate(
            check=args.check,
            site_dir=args.output_dir,
            book=args.book,
            skip_disabled=args.skip_disabled,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
