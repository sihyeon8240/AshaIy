"""Create a textbook scaffold and restore the registry if generation fails."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.books.book_manifest import (
    add_book,
    load_manifest,
    manifest_warnings,
    require_book,
    suggested_label_prefix,
    validate_new_book_input,
)
from scripts.books.contents_generation import generate
from scripts.repository.file_updates import (
    observe_source,
    replace_file,
    retain_recovery,
    source_updates,
)

ROOT = Path(__file__).resolve().parents[2]


def create_book(slug: str, title: str, *, label_prefix: str | None = None) -> None:
    with source_updates(ROOT):
        _create_book(slug, title, label_prefix=label_prefix)


def _create_book(slug: str, title: str, *, label_prefix: str | None) -> None:
    validate_new_book_input(slug, title, label_prefix)
    print("New book input is valid")
    target = ROOT / "books" / slug
    if target.exists() or target.is_symlink():
        raise ValueError(f"refusing to overwrite existing path: {target}")

    data = load_manifest()
    prefix = label_prefix if label_prefix is not None else suggested_label_prefix(slug)
    if any(book["label_prefix"] == prefix for book in data["books"]):
        raise ValueError(f"duplicate label_prefix: {prefix}; choose another --label-prefix")
    for warning in manifest_warnings(data):
        print(f"warning: {warning}", file=sys.stderr)
    print("config/books.yml is valid")
    manifest = ROOT / "config/books.yml"
    original = manifest.read_bytes()
    observe_source(manifest, original)
    registered = original
    target.mkdir()
    try:
        introduction = target / "chapters/introduction"
        introduction.mkdir(parents=True)
        templates = ROOT / "common/templates"
        sources = {
            "book.tex": target / "book.tex",
            "chapter.tex": introduction / "index.tex",
            "section.tex": introduction / "first-section.tex",
            "chapters.yml": target / "chapters.yml",
            "sections.yml": introduction / "sections.yml",
            "references.bib": target / "references.bib",
            "formalization.md": target / "formalization.md",
        }
        for name, destination in sources.items():
            shutil.copyfile(templates / name, destination)

        add_book(slug, title, release=False, site=False, label_prefix=prefix)
        registered = manifest.read_bytes()
        print(f"Added '{slug}' to config/books.yml")
        label_prefix = require_book(slug)["label_prefix"]
        section = introduction / "first-section.tex"
        section.write_bytes(section.read_bytes().replace(b"xx:", f"{label_prefix}:".encode()))
        if generate("all", book=slug):
            raise ValueError("contents generation failed")
    except BaseException as error:
        try:
            replace_file(manifest, original, expected=registered, durable=True)
        except BaseException:
            recovery = retain_recovery({manifest: original})
            raise OSError(f"creation failed; scaffold retained at {target}; registry recovery at {recovery}") from error
        print(f"error: creation failed; removing {target}", file=sys.stderr)
        shutil.rmtree(target)
        raise

    print(f"Created books/{slug}")
    print(f"Registered '{slug}' in config/books.yml as draft")
    print("Site publication and releases remain disabled; see docs/site-metadata.md to enable it")
    print("Next: run ashaiy config generate, then ashaiy config check")
    print("Commit the new sources, config/books.yml, and synchronized .vscode/tasks.json together")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("title")
    parser.add_argument("--label-prefix")
    arguments = parser.parse_args()
    try:
        create_book(arguments.slug, arguments.title, label_prefix=arguments.label_prefix)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
