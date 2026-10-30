"""Load ordered Lean topic manifests and render aggregation modules."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from scripts.books.book_manifest import load_manifest
from scripts.books.contents_manifest import load_book_contents
from scripts.repository.config.validation_patterns import validation_pattern
from scripts.repository.source_reads import read_text, read_yaml

ROOT = Path(__file__).resolve().parents[2]
GENERATED_NOTICE = "-- Generated from Lean module manifests; do not edit."
TOPIC = re.compile(validation_pattern("lean_name"))


def load_modules(directory: Path) -> list[str]:
    path = directory / "modules.yml"
    try:
        data = read_yaml(path)
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"{path}: cannot read YAML: {error}") from error
    if not isinstance(data, dict) or set(data) != {"schema_version", "modules"}:
        raise ValueError(f"{path}: expected schema_version and modules fields")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError(f"{path}: schema_version must be 1")
    modules = data["modules"]
    if not isinstance(modules, list):
        raise ValueError(f"{path}: modules must be a list")
    seen: set[str] = set()
    for module in modules:
        if not isinstance(module, str) or not TOPIC.fullmatch(module) or module == "All":
            raise ValueError(f"{path}: invalid topic name: {module!r}")
        if module in seen:
            raise ValueError(f"{path}: duplicate module: {module}")
        seen.add(module)
        if not (directory / f"{module}.lean").is_file():
            raise ValueError(f"{path}: declared Lean source is missing: {module}.lean")
    return modules


def book_assembly(root: Path, book: dict) -> str:
    chapters, appendices = load_book_contents(root / "books" / book["slug"])
    directory = root / "lean/Textbooks" / book["lean_module"]
    expected_sources = {directory / "All.lean"}
    expected_manifests: set[Path] = set()
    groups: list[str] = []
    for kind, entries in (("chapters", chapters), ("appendices", appendices)):
        for entry in entries:
            namespace = entry.get("lean_namespace")
            if namespace is None:
                continue
            relative = namespace if kind == "chapters" else f"Appendices/{namespace}"
            chapter = directory / relative
            if not chapter.exists():
                continue
            modules = load_modules(chapter)
            expected_manifests.add(chapter / "modules.yml")
            expected_sources.update(chapter / f"{name}.lean" for name in modules)
            if modules:
                groups.append(
                    "\n".join(
                        f"import Textbooks.{book['lean_module']}.{relative.replace('/', '.')}.{name}"
                        for name in modules
                    )
                )

    orphaned = (set(directory.rglob("*.lean")) - expected_sources) | (
        set(directory.rglob("modules.yml")) - expected_manifests
    )
    if orphaned:
        raise ValueError(f"{sorted(orphaned)[0]}: unregistered Lean source or manifest")
    return "\n\n".join([GENERATED_NOTICE, *groups]) + "\n"


def expected_files(root: Path = ROOT, book: str | None = None) -> dict[Path, str]:
    books = load_manifest(root / "config/books.yml", root)["books"]
    if book and not any(item["slug"] == book for item in books):
        raise ValueError(f"book is not registered in config/books.yml: {book}")
    lean_books = [item for item in books if item.get("lean_module")]
    registered = {item["lean_module"] for item in lean_books}
    for path in (root / "lean/Textbooks").rglob("*"):
        if path.is_file() and (path.suffix == ".lean" or path.name == "modules.yml"):
            owner = path.relative_to(root / "lean/Textbooks").parts[0]
            if owner not in registered:
                raise ValueError(f"{path}: unregistered Lean book")

    imports = [f"import Textbooks.{item['lean_module']}.All" for item in lean_books]
    root_text = "\n".join([GENERATED_NOTICE, "", *imports]).rstrip() + "\n"
    expected = {root / "lean/Textbooks.lean": root_text}
    for item in lean_books:
        if book is None or item["slug"] == book:
            path = root / "lean/Textbooks" / item["lean_module"] / "All.lean"
            expected[path] = book_assembly(root, item)
    return expected


def stale_files(expected: dict[Path, str]) -> list[Path]:
    return [path for path, text in expected.items() if not path.is_file() or read_text(path) != text]
