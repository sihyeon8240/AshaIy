"""Load the sharded LaTeX-to-Lean proof index."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts.books.book_manifest import load_manifest
from scripts.books.contents_manifest import proof_index_paths
from scripts.repository.source_reads import field_mapping, read_yaml

SHARD_FIELDS = {"proofs"}


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = read_yaml(path)
    except FileNotFoundError as error:
        raise ValueError(f"YAML file not found: {path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"invalid YAML in {path}: {error}") from error
    return field_mapping(data, f"{path} root")


def load_proof_index(
    root: Path, *, books: list[dict[str, Any]] | None = None
) -> tuple[list[str], list[dict[str, Any]]]:
    """Load proof shards in deterministic book/chapter order."""
    errors: list[str] = []
    if books is None:
        try:
            books = load_manifest(root / "config/books.yml", root)["books"]
        except ValueError as error:
            return [str(error)], []

    assert books is not None
    paths: list[Path] = []
    for book in books:
        try:
            paths.extend(proof_index_paths(root / "books" / book["slug"]))
        except ValueError as error:
            errors.append(str(error))

    for path in sorted(set((root / "books").rglob("proofs.yml")) - set(paths)):
        errors.append(f"{path.relative_to(root)}: unregistered proof index")

    proofs: list[dict[str, Any]] = []
    for path in paths:
        relative = path.relative_to(root)
        expected_book = relative.parts[1]
        expected_chapter = path.parent.name
        is_appendix = path.parent.parent.name == "appendices"
        try:
            shard = load_yaml(path)
        except ValueError as error:
            errors.append(str(error))
            continue
        unknown = set(shard) - SHARD_FIELDS
        if unknown:
            errors.append(f"{relative} contains unknown fields: {', '.join(sorted(unknown))}")
        entries = shard.get("proofs")
        if not isinstance(entries, list):
            errors.append(f"{relative} 'proofs' must be a list")
            continue
        for number, entry in enumerate(entries, start=1):
            try:
                entry = field_mapping(entry, f"{relative} proof entry {number}")
            except ValueError as error:
                errors.append(str(error))
                continue
            shard_owned = {"book", "chapter", "source", "kind"} & set(entry)
            if shard_owned:
                errors.append(
                    f"{relative} proof entry {number} contains shard-owned fields: {', '.join(sorted(shard_owned))}"
                )
            enriched = dict(entry)
            enriched["book"] = expected_book
            enriched["chapter"] = expected_chapter
            enriched["kind"] = "appendices" if is_appendix else "chapters"
            enriched["source"] = str(relative)
            proofs.append(enriched)
    return errors, proofs
