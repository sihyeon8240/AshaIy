"""Load and render the declarative textbook contents manifests."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import yaml

try:
    from scripts.validation_patterns import validation_pattern
except ModuleNotFoundError:
    from validation_patterns import validation_pattern

try:
    from scripts.source_reads import read_text, read_yaml
except ModuleNotFoundError:
    from source_reads import read_text, read_yaml

try:
    from scripts.latex_scan import has_balanced_braces, without_comments
except ModuleNotFoundError:
    from latex_scan import has_balanced_braces, without_comments

SCHEMA_VERSION = 1
SLUG = re.compile("^" + validation_pattern("chapter_slug") + "$")
SECTION_SLUG = re.compile("^" + validation_pattern("section_slug") + "$")
LEAN_NAMESPACE = re.compile(validation_pattern("lean_name"))
BEGIN_CHAPTERS = "% BEGIN GENERATED CHAPTERS"
END_CHAPTERS = "% END GENERATED CHAPTERS"
BEGIN_APPENDICES = "% BEGIN GENERATED APPENDICES"
END_APPENDICES = "% END GENERATED APPENDICES"
BEGIN_METADATA = "% BEGIN GENERATED METADATA"
END_METADATA = "% END GENERATED METADATA"
GENERATED_NOTICE = "% Generated from contents manifests; do not edit."


def _mapping(path: Path) -> dict:
    try:
        value = read_yaml(path)
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"{path}: cannot read YAML: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be a mapping")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path}: schema_version must be {SCHEMA_VERSION}")
    return value


def _entries(path: Path, field: str, allowed: set[str]) -> list[dict]:
    data = _mapping(path)
    unknown_root = set(data) - {"schema_version", field}
    if unknown_root:
        raise ValueError(f"{path}: unknown field(s): {', '.join(sorted(unknown_root))}")
    values = data.get(field)
    if not isinstance(values, list) or not values:
        raise ValueError(f"{path}: {field} must be a non-empty list")
    _validate_entries(path, field, values, allowed)
    return values


def _validate_entries(
    path: Path, field: str, values: list[dict], allowed: set[str]
) -> None:
    seen: set[str] = set()
    for number, item in enumerate(values, 1):
        prefix = f"{path}: {field}[{number}]"
        if not isinstance(item, dict):
            raise ValueError(f"{prefix} must be a mapping")
        unknown = set(item) - allowed
        if unknown:
            raise ValueError(
                f"{prefix}: unknown field(s): {', '.join(sorted(unknown))}"
            )
        slug = item.get("slug")
        title = item.get("title")
        pattern = SECTION_SLUG if field == "sections" else SLUG
        if not isinstance(slug, str) or not pattern.fullmatch(slug):
            raise ValueError(f"{prefix}.slug must be lowercase hyphenated text")
        if field == "sections" and slug == "index":
            raise ValueError(
                f"{prefix}.slug 'index' is reserved for generated assembly"
            )
        if slug in seen:
            raise ValueError(f"{path}: duplicate {field[:-1]} slug {slug!r}")
        seen.add(slug)
        if (
            not isinstance(title, str)
            or not title.strip()
            or "\n" in title
            or "\r" in title
            or not has_balanced_braces(title)
        ):
            raise ValueError(
                f"{prefix}.title must be a non-empty, balanced single-line string"
            )


def load_book_contents(book_dir: Path) -> tuple[list[dict], list[dict]]:
    path = book_dir / "chapters.yml"
    data = _mapping(path)
    unknown_root = set(data) - {"schema_version", "chapters", "appendices"}
    if unknown_root:
        raise ValueError(
            f"{path}: unknown field(s): " + ", ".join(sorted(unknown_root))
        )

    chapters = data.get("chapters")
    appendices = data.get("appendices", [])
    for field, values, required in (
        ("chapters", chapters, True),
        ("appendices", appendices, False),
    ):
        if not isinstance(values, list) or (required and not values):
            raise ValueError(f"{path}: {field} must be a non-empty list")
        if not required and "appendices" in data and not values:
            raise ValueError(
                f"{path}: appendices must be a non-empty list when present"
            )
        _validate_entries(path, field, values, {"slug", "title", "lean_namespace"})
        namespaces: set[str] = set()
        for item in values:
            if "lean_namespace" not in item:
                continue
            namespace = item["lean_namespace"]
            if (
                not isinstance(namespace, str)
                or not LEAN_NAMESPACE.fullmatch(namespace)
                or namespace in {"All", "Appendices"}
                or re.fullmatch(
                    validation_pattern("reserved_lean_namespace"), namespace
                )
            ):
                raise ValueError(f"{path}: invalid lean_namespace: {namespace!r}")
            if namespace in namespaces:
                raise ValueError(f"{path}: duplicate lean_namespace: {namespace}")
            namespaces.add(namespace)
    return cast(list[dict], chapters), cast(list[dict], appendices)


def load_chapters(book_dir: Path) -> list[dict]:
    return load_book_contents(book_dir)[0]


def load_sections(chapter_dir: Path) -> list[dict]:
    path = chapter_dir / "sections.yml"
    return _entries(path, "sections", {"slug", "title"})


def chapter_directory(book_dir: Path, chapter: dict) -> Path:
    return book_dir / "chapters" / chapter["slug"]


def appendix_directory(book_dir: Path, appendix: dict) -> Path:
    return book_dir / "appendices" / appendix["slug"]


def proof_index_paths(book_dir: Path) -> list[Path]:
    """Return chapter and appendix proof indexes in contents order."""
    chapters, appendices = load_book_contents(book_dir)
    return [
        directory_for(book_dir, entry) / "proofs.yml"
        for entries, directory_for in (
            (chapters, chapter_directory),
            (appendices, appendix_directory),
        )
        for entry in entries
    ]


def section_filenames(section: dict) -> list[str]:
    return [f"{section['slug']}.tex"]


def render_include_block(entries: list[dict], kind: str) -> str:
    begin, end = (
        (BEGIN_CHAPTERS, END_CHAPTERS)
        if kind == "chapters"
        else (BEGIN_APPENDICES, END_APPENDICES)
    )
    lines = [begin]
    if kind == "appendices" and entries:
        lines.append(r"\appendix")
    lines.extend(f"\\include{{{kind}/{entry['slug']}/index}}" for entry in entries)
    lines.append(end)
    return "\n".join(lines)


def render_metadata(book: dict) -> str:
    return "\n".join(
        (
            BEGIN_METADATA,
            f"\\newcommand{{\\name}}{{{book['author']}}}",
            f"\\newcommand{{\\displaytitle}}{{{book['title']}}}",
            f"\\newcommand{{\\version}}{{{book['version']}}}",
            f"\\newcommand{{\\slug}}{{{book['slug']}}}",
            r"\title{\displaytitle}",
            r"\author{\name}",
            r"\hypersetup{pdftitle={\displaytitle},pdfauthor={\name}}",
            END_METADATA,
        )
    )


def replace_generated_block(
    text: str, rendered: str, path: Path, begin: str, end: str
) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError(f"{path}: expected exactly one {begin!r} and {end!r}")
    start = text.index(begin)
    finish = text.index(end, start) + len(end)
    return text[:start] + rendered + text[finish:]


def render_contents_index(
    book_dir: Path, directory: Path, entry: dict, sections: list[dict] | None = None
) -> str:
    if sections is None:
        sections = load_sections(directory)
    lines = [GENERATED_NOTICE, "", f"\\chapter{{{entry['title']}}}"]
    relative = directory.relative_to(book_dir).as_posix()
    for section in sections:
        lines.extend(("", f"\\section{{{section['title']}}}"))
        lines.extend(
            f"\\input{{{relative}/{filename}}}"
            for filename in section_filenames(section)
        )
    return "\n".join(lines) + "\n"


def expected_files(
    book_dir: Path, scope: str = "all", book: dict | None = None
) -> dict[Path, str]:
    chapters, appendices = load_book_contents(book_dir)
    expected: dict[Path, str] = {}
    if scope in {"chap", "all"}:
        path = book_dir / "book.tex"
        if book is None:
            raise ValueError(f"{path}: book manifest record is required")
        template_path = (
            Path(__file__).resolve().parent.parent / "common/templates/book.tex"
        )
        original = read_text(template_path)
        original = replace_generated_block(
            original,
            render_metadata(book),
            template_path,
            BEGIN_METADATA,
            END_METADATA,
        )
        if original.count(r"\backmatter") != 1 or original.index(
            END_APPENDICES
        ) > original.index(r"\backmatter"):
            raise ValueError(
                f"{template_path}: generated appendices block must precede exactly one \\backmatter"
            )
        text = replace_generated_block(
            original,
            render_include_block(chapters, "chapters"),
            template_path,
            BEGIN_CHAPTERS,
            END_CHAPTERS,
        )
        expected[path] = replace_generated_block(
            text,
            render_include_block(appendices, "appendices"),
            template_path,
            BEGIN_APPENDICES,
            END_APPENDICES,
        )
    if scope in {"sec", "all"}:
        groups = ((chapters, chapter_directory), (appendices, appendix_directory))
        for entries, directory_for in groups:
            for entry in entries:
                directory = directory_for(book_dir, entry)
                sections = load_sections(directory)
                expected[directory / "index.tex"] = render_contents_index(
                    book_dir, directory, entry, sections
                )
                expected_sources = {
                    directory / filename
                    for section in sections
                    for filename in section_filenames(section)
                }
                actual_sources = {
                    path for path in directory.glob("*.tex") if path.name != "index.tex"
                }
                missing = sorted(expected_sources - actual_sources)
                orphaned = sorted(actual_sources - expected_sources)
                if missing:
                    raise ValueError(
                        f"{missing[0]}: declared section source is missing"
                    )
                if orphaned:
                    raise ValueError(f"{orphaned[0]}: orphan section source")
                for source in sorted(expected_sources):
                    declaration = re.search(
                        r"\\(chapter|section)(?![A-Za-z@])",
                        without_comments(read_text(source)),
                    )
                    if declaration:
                        command = declaration.group(1)
                        manifest = (
                            "chapters.yml" if command == "chapter" else "sections.yml"
                        )
                        raise ValueError(
                            f"{source}: {command} declarations belong in {manifest}"
                        )
    return expected
