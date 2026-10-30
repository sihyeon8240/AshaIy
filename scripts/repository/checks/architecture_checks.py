#!/usr/bin/env python3
"""Validate the policies documented in docs/ARCHITECTURE.md."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.books.book_manifest import load_manifest
from scripts.books.contents_manifest import (
    appendix_directory,
    chapter_directory,
    load_book_contents,
    load_sections,
    section_filenames,
)
from scripts.latex.bibtex import entry_keys
from scripts.latex.latex_scan import command_arguments
from scripts.latex.latex_titles import chapter_titles as extract_chapter_titles
from scripts.repository.config.validation_patterns import validation_pattern
from scripts.repository.source_reads import read_text

ROOT = Path(__file__).resolve().parents[3]
CHAPTER_DIRECTORY = re.compile("^" + validation_pattern("chapter_slug") + "$")
SECTION_FILENAME = re.compile(rf"^(?P<slug>{validation_pattern('section_slug')})\.tex$")
GENERIC_SECTION_SLUGS = {"continuation", "misc"}


@dataclass
class Findings:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, value: str) -> None:
        self.errors.append(value)

    def warn(self, value: str) -> None:
        self.warnings.append(value)


@dataclass(frozen=True)
class SectionSource:
    path: Path
    slug: str


def parse_section_sources(paths: list[Path], chapter_name: str, out: Findings) -> list[SectionSource]:
    """Parse the single source file for each logical section."""
    sources: list[SectionSource] = []
    for path in sorted(paths):
        match = SECTION_FILENAME.fullmatch(path.name)
        if match is None:
            out.error(f"chapter {chapter_name}: section filename {path.name} must match lowercase-hyphenated-name.tex")
            continue
        slug = match.group("slug")
        if slug in GENERIC_SECTION_SLUGS or re.fullmatch(r"(?:section-)?part-[0-9]+", slug):
            out.error(
                f"chapter {chapter_name}: section filename {path.name} uses "
                "a context-dependent name; use the logical section slug"
            )
        sources.append(SectionSource(path, slug))

    return sources


def tex_path(base: Path, target: str) -> Path:
    path = base / target
    path = path if path.suffix else path.with_suffix(".tex")
    if path.is_file():
        return path
    fallback = ROOT / "common" / "templates" / path.name
    return fallback if fallback.is_file() else path


def includes(text: str, source: Path, out: Findings) -> list[str]:
    found = [item.argument for item in command_arguments(text, {"include", "input"})]
    seen: set[str] = set()
    for target in found:
        if target in seen:
            out.error(f"{source}: duplicate include/input target: {target}")
        seen.add(target)
    return found


def bibliography_checks(book_dir: Path, text: str, out: Findings) -> None:
    required = book_dir / "references.bib"
    if not required.is_file():
        out.error(f"{required}: required bibliography is missing")
        return

    resources = [item.argument for item in command_arguments(text, {"addbibresource"})]
    for path in sorted(book_dir.rglob("*.bib")):
        if path.relative_to(book_dir).as_posix() not in resources:
            out.warn(f"{path}: unused bibliography file")

    keys: dict[str, Path] = {}
    for resource in resources:
        path = book_dir / resource
        if not path.is_file():
            out.error(f"{path}: configured bibliography does not exist")
            continue
        for key in entry_keys(read_text(path)):
            if key in keys:
                out.error(f"{path}: duplicate bibliography key {key!r}")
            keys[key] = path
    if r"\nocite{*}" not in text:
        out.warn(f"{book_dir / 'book.tex'}: \\nocite{{*}} is absent")


def check_chapter_index(chapter: Path, book_dir: Path, expected_sources: list[Path], out: Findings) -> None:
    text = read_text(chapter)
    if len(extract_chapter_titles(text)) != 1:
        out.error(f"{chapter}: expected one chapter declaration")

    referenced: set[Path] = set()
    ordered_paths: list[Path] = []
    for section in includes(text, chapter, out):
        base = book_dir if section.startswith(("chapters/", "appendices/")) else chapter.parent
        path = tex_path(base, section)
        ordered_paths.append(path)
        referenced.add(path)
        if not path.is_file():
            out.error(f"{chapter}: target does not exist: {section}")

    resolved_order = [path.resolve() for path in ordered_paths]
    expected_order = [path.resolve() for path in expected_sources]
    if resolved_order != expected_order:
        out.error(f"{chapter}: section inputs do not match the canonical sections.yml order")

    section_files = {path for path in chapter.parent.glob("*.tex") if path.name != "index.tex"}
    parse_section_sources(list(section_files), chapter.parent.name, out)
    for orphan in sorted(section_files - referenced):
        out.error(f"{orphan}: orphan section file")


def check_content_targets(entry: Path, book_dir: Path, kind: str, targets: list[str], out: Findings) -> set[Path]:
    label = "chapter" if kind == "chapters" else "appendix"
    referenced_dirs: set[Path] = set()
    for target in targets:
        index = tex_path(book_dir, target)
        referenced_dirs.add(index.parent)
        if index.name != "index.tex":
            out.error(f"{entry}: {label} target is not index.tex: {target}")
        if not index.is_file():
            continue
        try:
            sections = load_sections(index.parent)
            expected_sources = [
                index.parent / filename for section in sections for filename in section_filenames(section)
            ]
        except ValueError:
            # Manifest errors are reported before inspecting generated indexes.
            expected_sources = []
        check_chapter_index(index, book_dir, expected_sources, out)

    return referenced_dirs


def check_content_directories(book_dir: Path, kind: str, referenced_dirs: set[Path], out: Findings) -> None:
    label = "chapter" if kind == "chapters" else "appendix"
    content_root = book_dir / kind
    directories = sorted(path for path in content_root.iterdir() if path.is_dir()) if content_root.is_dir() else []
    for directory in directories:
        if not (directory / "index.tex").is_file():
            out.error(f"{directory}: index.tex is missing")
        if directory not in referenced_dirs:
            out.error(f"{directory}: orphan {label} directory")
        if not CHAPTER_DIRECTORY.fullmatch(directory.name):
            out.error(f"{directory}: chapter directory name must match lowercase-hyphenated-name")


def check_book(book: dict, root: Path, out: Findings) -> None:
    book_dir = root / "books" / book["slug"]
    entry = book_dir / "book.tex"
    if not entry.is_file():
        out.error(f"{entry}: required file is missing")
        return

    try:
        canonical_chapters, canonical_appendices = load_book_contents(book_dir)
        groups = (
            (canonical_chapters, chapter_directory),
            (canonical_appendices, appendix_directory),
        )
        for entries, directory_for in groups:
            for entry_data in entries:
                load_sections(directory_for(book_dir, entry_data))
    except ValueError as error:
        out.error(str(error))
        canonical_chapters = []
        canonical_appendices = []

    entry_text = read_text(entry)
    entry_targets = includes(entry_text, entry, out)
    for target in entry_targets:
        if not tex_path(book_dir, target).is_file():
            out.error(f"{entry}: target does not exist: {target}")

    chapter_targets = [target for target in entry_targets if target.startswith("chapters/")]
    appendix_targets = [target for target in entry_targets if target.startswith("appendices/")]
    expected_chapter_targets = [f"chapters/{item['slug']}/index" for item in canonical_chapters]
    expected_appendix_targets = [f"appendices/{item['slug']}/index" for item in canonical_appendices]
    if chapter_targets != expected_chapter_targets:
        out.error(f"{entry}: chapter includes do not match canonical chapters.yml")
    if appendix_targets != expected_appendix_targets:
        out.error(f"{entry}: appendix includes do not match canonical chapters.yml")
    referenced_dirs = check_content_targets(entry, book_dir, "chapters", chapter_targets, out)
    referenced_dirs.update(check_content_targets(entry, book_dir, "appendices", appendix_targets, out))
    for kind, targets in (
        ("chapters", chapter_targets),
        ("appendices", appendix_targets),
    ):
        check_content_directories(book_dir, kind, referenced_dirs, out)
    bibliography_checks(book_dir, entry_text, out)


def validate_repository(root: Path = ROOT) -> Findings:
    out = Findings()
    if not (root / "docs/ARCHITECTURE.md").is_file():
        out.error("docs/ARCHITECTURE.md is missing")

    try:
        manifest = load_manifest(path=root / "config/books.yml", repository_root=root)
    except (OSError, UnicodeError, ValueError) as error:
        out.error(f"config/books.yml cannot be read: {error}")
        return out

    books = manifest["books"]
    registered = {book["slug"] for book in books}
    books_root = root / "books"
    actual = {path.name for path in books_root.iterdir() if path.is_dir()} if books_root.is_dir() else set()
    for slug in sorted(actual - registered):
        out.error(f"books/{slug}: orphan book directory")
    for slug in sorted(registered - actual):
        out.error(f"books/{slug}: registered directory is missing")

    for book in books:
        check_book(book, root, out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    return check_architecture(parser.parse_args().root.resolve())


def check_architecture(root: Path = ROOT) -> int:
    out = validate_repository(root)
    for value in out.warnings:
        print(f"warning: {value}", file=sys.stderr)
    for value in out.errors:
        print(f"error: {value}", file=sys.stderr)
    if out.errors:
        print(
            f"Architecture checks failed: {len(out.errors)} error(s).",
            file=sys.stderr,
        )
        return 1
    print("Repository architecture checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
