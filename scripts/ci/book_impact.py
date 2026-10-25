"""Select manifest books whose PDF build inputs changed."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

import yaml

from scripts.books.book_manifest import load_manifest, normalize_manifest
from scripts.ci.ci_changes import changed_paths as shared_changed_paths
from scripts.ci.ci_changes import (
    classify,
    is_documentation,
)
from scripts.latex.latex_scan import without_comments
from scripts.repository.config.repository_config import load_image_build
from scripts.repository.path_policy import (
    BUILD_INFRA,
    CI_ONLY_FILES,
    SCAFFOLD_FILES,
    SITE_FILES,
    SNAPSHOT_FILES,
)
from scripts.repository.source_reads import parse_yaml

ROOT = Path(__file__).resolve().parents[2]
TEX_REF = re.compile(
    r"\\(?P<command>input|includegraphics|include|addbibresource|bibliography|"
    r"usepackage|RequirePackage)"
    r"(?:\s*\[[^]]*\])?\s*\{(?P<reference>[^}]+)\}"
)
IMAGE_INPUTS = set(load_image_build()["inputs"])


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout


def manifest_at(revision: str | None) -> dict | None:
    if not revision:
        return None
    try:
        text = git_output("show", f"{revision}:config/books.yml")
    except subprocess.CalledProcessError:
        return None
    try:
        return normalize_manifest(parse_yaml(text))
    except OSError, ValueError, TypeError, yaml.YAMLError:
        return None


def changed_paths(base: str | None, head: str) -> list[str] | None:
    return shared_changed_paths(base, head, root=ROOT)


def _resolve_tex(reference: str, source: Path, command: str) -> list[Path]:
    result: list[Path] = []
    try:
        relative_source = source.resolve().relative_to(ROOT / "books")
        book_root = ROOT / "books" / relative_source.parts[0]
    except ValueError, IndexError:
        book_root = source.parent
    for name in (item.strip() for item in reference.split(",")):
        if not name:
            continue
        if command == "includegraphics":
            suffixes = (
                ("",)
                if Path(name).suffix
                else (".pdf", ".png", ".jpg", ".jpeg", ".eps")
            )
            for directory in (source.parent, book_root, ROOT):
                found = next(
                    (
                        directory / (name + suffix)
                        for suffix in suffixes
                        if (directory / (name + suffix)).is_file()
                    ),
                    None,
                )
                if found is not None:
                    result.append(found.resolve())
                    break
            continue
        if command in {"usepackage", "RequirePackage"}:
            suffix = ".sty"
            search_roots = (
                source.parent,
                book_root / "styles",
                book_root,
                ROOT / "common" / "styles",
                ROOT,
            )
        elif command in {"bibliography", "addbibresource"}:
            suffix = ".bib"
            search_roots = (source.parent, book_root)
        else:
            suffix = ".tex"
            search_roots = (
                source.parent,
                book_root,
                ROOT,
                ROOT / "common" / "styles",
                ROOT / "common" / "templates",
            )
        suffix = "" if Path(name).suffix else suffix
        relative = Path(name + suffix)
        for root in search_roots:
            path = root / relative
            if path.is_file():
                result.append(path.resolve())
                break
    return result


def dependencies(slug: str) -> set[str]:
    pending = [(ROOT / "books" / slug / "book.tex").resolve()]
    seen: set[Path] = set()
    while pending:
        source = pending.pop()
        if source in seen or not source.is_file():
            continue
        seen.add(source)
        if source.suffix not in {".tex", ".sty"}:
            continue
        text = without_comments(source.read_text(encoding="utf-8", errors="ignore"))
        for match in TEX_REF.finditer(text):
            pending.extend(_resolve_tex(match["reference"], source, match["command"]))
    book_dir = ROOT / "books" / slug
    if (ROOT / "common/styles/macros.yml").is_file():
        seen.add((ROOT / "common/styles/macros.yml").resolve())
    seen.update(path.resolve() for path in book_dir.rglob("*") if path.is_file())
    return {
        path.relative_to(ROOT).as_posix() for path in seen if path.is_relative_to(ROOT)
    }


def plan(
    paths: list[str] | None,
    old_manifest: dict | None = None,
    rebuild_all: bool = False,
    *,
    release_books: tuple[str, ...] = (),
    explain: bool = False,
) -> dict:
    current_manifest = load_manifest()
    build_books = [book for book in current_manifest["books"] if book["build"]]
    slugs = [book["slug"] for book in build_books]
    if not set(release_books) <= set(slugs):
        raise ValueError("release matrix contains a book not enabled for building")
    reasons: dict[str, list[dict]] = {slug: [] for slug in slugs}

    def select(selected: list[str], reason: str, inputs: list[str]) -> None:
        for slug in selected:
            reasons[slug].append({"reason": reason, "paths": sorted(inputs)})

    if paths is None:
        select(slugs, "comparison unavailable; safe full build", [])
        reason = "comparison unavailable; safe full build"
    else:
        path_set = {PurePosixPath(path).as_posix() for path in paths}
        dependency_map = {slug: dependencies(slug) for slug in slugs}
        for slug, inputs in dependency_map.items():
            matched = path_set & inputs | {
                path for path in path_set if path.startswith(f"books/{slug}/")
            }
            if matched:
                select([slug], "changed book inputs", list(matched))
        infrastructure = path_set & (BUILD_INFRA | IMAGE_INPUTS)
        if rebuild_all:
            select(slugs, "full build requested", [])
        if infrastructure:
            select(slugs, "changed shared build infrastructure", list(infrastructure))
        if "config/books.yml" in path_set:
            if old_manifest is None:
                select(slugs, "historical manifest unavailable", ["config/books.yml"])
            else:
                old = {book["slug"]: book for book in old_manifest["books"]}
                if old_manifest.get("schema_version") != current_manifest.get(
                    "schema_version"
                ):
                    select(slugs, "manifest schema changed", ["config/books.yml"])
                for book in build_books:
                    previous = old.get(book["slug"])
                    if previous is None or previous.get("build") != book["build"]:
                        select(
                            [book["slug"]],
                            "book added or build flag changed",
                            ["config/books.yml"],
                        )
                    if book.get("site", False) and not (previous or {}).get(
                        "site", False
                    ):
                        select(
                            [book["slug"]],
                            "site publication enabled; snapshot requires a PDF",
                            ["config/books.yml"],
                        )
        known = (
            set().union(*dependency_map.values())
            | IMAGE_INPUTS
            | BUILD_INFRA
            | SITE_FILES
            | SNAPSHOT_FILES
            | CI_ONLY_FILES
            | SCAFFOLD_FILES
            | {"config/books.yml"}
        )
        ignored = ("site/", "docs/", ".github/", "tests/")
        unknown = sorted(
            path
            for path in path_set
            if path not in known
            and not path.startswith(ignored)
            and not is_documentation(path)
        )
        if unknown:
            select(slugs, "unknown build inputs; safe full build", unknown)
        reason = "changed build dependencies"
    for slug in sorted(set(release_books)):
        select([slug], "requested release requires a build", [])
    selected = [slug for slug in slugs if reasons[slug]]
    facts = classify(paths)
    result = {
        "book": selected,
        "count": len(selected),
        "site_changed": facts["site_changed"],
        "snapshot_changed": facts["snapshot_changed"],
        "reason": reason,
    }
    if explain:
        result["reasons"] = reasons
    return result
