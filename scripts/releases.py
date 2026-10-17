#!/usr/bin/env python3
"""Prepare reviewed version changes and plan post-merge textbook releases."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml
from book_manifest import SLUG_PATTERN, load_manifest, normalize_manifest, version_key
from contents_manifest import expected_files

ROOT = Path(__file__).resolve().parent.parent


class ReleaseVersionMismatch(ValueError):
    """A valid tag disagrees with the registered version."""


def plan_tag(tag: str, manifest: dict) -> dict:
    match = re.fullmatch(r"([a-z0-9]+(?:-[a-z0-9]+)*)-v(.+)", tag)
    try:
        if match is None:
            raise ValueError("invalid slug")
        slug, version = match.groups()
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError("invalid slug")
        version_key(version)
    except ValueError as error:
        raise ValueError(
            f"invalid release tag '{tag}'; expected <book>-v<version>"
        ) from error

    book = next((book for book in manifest["books"] if book["slug"] == slug), None)
    if book is None or not book["release"]:
        raise ValueError(f"book is not enabled for release in config/books.yml: {slug}")
    if book["version"] != version:
        raise ReleaseVersionMismatch(
            f"tag version {version} does not match config/books.yml (version={book['version']})"
        )
    return book


def plan(previous: dict, current: dict) -> list[str]:
    old = {book["slug"]: book for book in previous["books"]}
    selected = []
    for book in current["books"]:
        before = old.get(book["slug"])
        changed = before is not None and before["version"] != book["version"]
        if changed and version_key(book["version"]) <= version_key(before["version"]):
            raise ValueError(f"version must increase: {book['slug']}")
        enabled_before = before is not None and before.get(
            "release", previous.get("defaults", {}).get("release", False)
        )
        if book["release"] and (changed or not enabled_before):
            version_key(book["version"])
            if not book["build"]:
                raise ValueError(f"release requires build: true: {book['slug']}")
            selected.append(book["slug"])
    return selected


def report_plan(selected: list[str], manifest: dict, summary: Path) -> None:
    books = {book["slug"]: book for book in manifest["books"]}
    lines = ["## Planned textbook releases", ""]
    if selected:
        lines.extend(["Book | Version | Tag", "--- | --- | ---"])
        for slug in selected:
            version = books[slug]["version"]
            lines.append(f"{slug} | {version} | `{slug}-v{version}`")
        lines.extend(["", "A main merge publishes these versions after CI passes."])
    else:
        lines.append("No textbook releases planned.")
    with summary.open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def check_remote_tags(selected: list[str], manifest: dict) -> None:
    books = {book["slug"]: book for book in manifest["books"]}
    refs = [f"refs/tags/{slug}-v{books[slug]['version']}" for slug in selected]
    if not refs:
        return

    # Query the base repository directly; checkout's local tags may be stale.
    output = subprocess.check_output(
        ["git", "ls-remote", "--refs", "origin", *refs], cwd=ROOT, text=True
    )
    existing = {line.split()[1] for line in output.splitlines()}
    conflicts = [ref.removeprefix("refs/tags/") for ref in refs if ref in existing]
    if conflicts:
        raise ValueError(
            "release tags already exist; choose a higher version: "
            + ", ".join(conflicts)
        )


def prepare(book_slug: str, version: str) -> None:
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    if not branch or branch == "main":
        raise ValueError("prepare releases on local-work or another development branch")

    manifest = load_manifest()
    book = next((b for b in manifest["books"] if b["slug"] == book_slug), None)
    if book is None:
        raise ValueError(f"unknown book: {book_slug}")
    if not book["build"]:
        raise ValueError("release preparation requires build: true")

    requested, current = version_key(version), version_key(book["version"])
    if requested < current or (requested == current and book["release"]):
        raise ValueError(
            "version must increase unless enabling release for the first time"
        )

    path = ROOT / "config/books.yml"
    text = path.read_text()
    document = yaml.compose(text)
    books_node = next(v for k, v in document.value if k.value == "books")
    node = next(
        item
        for item in books_node.value
        if any(k.value == "slug" and v.value == book_slug for k, v in item.value)
    )
    value = next(v for k, v in node.value if k.value == "version")
    edits = [(value.start_mark.index, value.end_mark.index, version)]
    release = next((v for k, v in node.value if k.value == "release"), None)
    if release is not None:
        edits.append((release.start_mark.index, release.end_mark.index, "true"))
    else:
        # Insert before the version field, respecting its existing indentation.
        key = next(k for k, _ in node.value if k.value == "version")
        position = text.rfind("\n", 0, key.start_mark.index) + 1
        indent = " " * key.start_mark.column
        edits.append((position, position, f"{indent}release: true\n"))

    # Preserve comments, formatting, and unrelated in-progress manifest edits.
    updated = text
    for start, end, replacement in sorted(edits, reverse=True):
        updated = updated[:start] + replacement + updated[end:]

    book = {**book, "version": version, "release": True}
    updates = expected_files(ROOT / "books" / book_slug, "all", book=book)
    updates[path] = updated

    original = {p: p.read_bytes() if p.exists() else None for p in updates}
    try:
        for target, content in updates.items():
            target.write_text(content, encoding="utf-8")
        load_manifest()
    except Exception:
        for target, content in original.items():
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(content)
        raise

    print(f"Prepared {book_slug} {version}; review and commit the changes in your PR.")
    print(
        "Merging this release preparation authorizes automatic publication after CI passes."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--book", required=True)
    prep.add_argument("--version", required=True)

    planning = sub.add_parser("plan")
    planning.add_argument("--base", required=True)
    planning.add_argument("--check-remote-tags", action="store_true")
    planning.add_argument("--summary", type=Path)

    tag_parser = sub.add_parser(
        "tag", help="validate a release tag and export its plan"
    )
    tag_parser.add_argument("tag")
    args = parser.parse_args()

    try:
        if args.command == "prepare":
            prepare(args.book, args.version)
        elif args.command == "tag":
            book = plan_tag(args.tag, load_manifest())
            print(f"{book['slug'].replace('-', '_')}_version={book['version']}")
            print(f"version={book['version']}")
            print(
                "matrix=" + json.dumps({"book": [book["slug"]]}, separators=(",", ":"))
            )
        else:
            # A branch's first push has no previous manifest to compare.
            previous = {"books": []}
            if args.base != "0" * 40:
                previous = normalize_manifest(
                    yaml.safe_load(
                        subprocess.check_output(
                            ["git", "show", f"{args.base}:config/books.yml"],
                            cwd=ROOT,
                            text=True,
                        )
                    )
                )
            manifest = load_manifest()
            selected = plan(previous, manifest)
            if args.summary:
                report_plan(selected, manifest, args.summary)
            if args.check_remote_tags:
                check_remote_tags(selected, manifest)
            print("matrix=" + json.dumps({"book": selected}, separators=(",", ":")))
            print(f"count={len(selected)}")
        return 0
    except ReleaseVersionMismatch as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except (
        ValueError,
        OSError,
        subprocess.CalledProcessError,
        yaml.YAMLError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
