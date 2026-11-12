"""Check explicitly linked Lean display fragments without rewriting either source."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

from scripts.books.book_manifest import load_manifest
from scripts.latex.latex_scan import source_spans
from scripts.lean.lean_source import ignored_spans
from scripts.repository.source_reads import read_text

MARKER = re.compile(r"-- textbook:(begin|end) ([a-z][a-z0-9-]*)$")
LINK = re.compile(r"%\s*lean-source: (lean/Textbooks/[A-Za-z0-9/]+\.lean)#([a-z][a-z0-9-]*)$")
BLOCK = re.compile(r"\s*\\begin\{lean\}[ \t]*\n(.*?)\n[ \t]*\\end\{lean\}", re.DOTALL)


def regions(text: str) -> dict[str, str]:
    result = {}
    active = None
    for start, end, kind in ignored_spans(text):
        if kind != "comment" or not (match := MARKER.fullmatch(text[start:end])):
            continue
        action, name = match.groups()
        if action == "begin":
            if active is not None or name in result:
                raise ValueError(f"nested or duplicate Lean fragment: {name}")
            active = (name, end + 1)
        else:
            if active is None or active[0] != name:
                raise ValueError(f"unmatched Lean fragment end: {name}")
            result[name] = text[active[1] : start]
            active = None
    if active is not None:
        raise ValueError(f"unclosed Lean fragment: {active[0]}")
    return result


def normalized(text: str) -> str:
    text = text.strip("\n")
    if any(kind == "literal" and "\n" in text[start:end] for start, end, kind in ignored_spans(text)):
        return text
    return textwrap.dedent(text).rstrip()


def check_file(path: Path, root: Path, *, owner: str | None = None) -> list[str]:
    text = read_text(path)
    errors = []
    sources = {}
    for span in source_spans(text):
        annotation = text[span.start : span.end]
        if span.kind != "comment" or not re.match(r"%\s*lean-source:", annotation):
            continue
        location = f"{path.relative_to(root)}:{text.count(chr(10), 0, span.start) + 1}"
        link = LINK.fullmatch(annotation)
        block = BLOCK.match(text, span.end)
        if link is None or block is None:
            errors.append(f"{location}: malformed lean-source link or missing adjacent lean block")
            continue
        relative, name = link.groups()
        target = root / relative
        if not target.resolve().is_relative_to(root.resolve() / "lean/Textbooks") or (
            owner is not None and not relative.startswith(f"lean/Textbooks/{owner}/")
        ):
            errors.append(f"{location}: Lean display source is outside its owning textbook")
            continue
        try:
            if target not in sources:
                sources[target] = regions(read_text(target))
            expected = sources[target].get(name)
            if expected is None:
                raise ValueError(f"missing Lean fragment: {relative}#{name}")
            if normalized(expected) != normalized(block[1]):
                raise ValueError(f"displayed Lean differs from {relative}#{name}")
        except (OSError, ValueError) as error:
            errors.append(f"{location}: {error}")
    return errors


def validate_displayed_code(root: Path) -> list[str]:
    errors = []
    for book in load_manifest(root / "config/books.yml", root)["books"]:
        for path in sorted((root / "books" / book["slug"]).rglob("*.tex")):
            errors.extend(check_file(path, root, owner=book.get("lean_module", "")))
    return errors
