"""Reuse source reads and YAML parsing during one read-only check."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SourceReads:
    texts: dict[tuple[Path, str], str] = field(default_factory=dict)
    documents: dict[Path, object] = field(default_factory=dict)


_active: ContextVar[SourceReads | None] = ContextVar("source_reads", default=None)


@contextmanager
def reuse_source_reads():
    """Discard the snapshot on exit so later checks observe source edits."""
    token = _active.set(SourceReads())
    try:
        yield
    finally:
        _active.reset(token)


def read_text(path: Path, *, errors: str = "strict") -> str:
    snapshot = _active.get()
    if snapshot is None:
        return path.read_text(encoding="utf-8", errors=errors)

    key = (path, errors)
    if key not in snapshot.texts:
        snapshot.texts[key] = path.read_text(encoding="utf-8", errors=errors)
    return snapshot.texts[key]


def read_yaml(path: Path) -> object:
    snapshot = _active.get()
    if snapshot is None:
        return yaml.safe_load(read_text(path))

    if path not in snapshot.documents:
        snapshot.documents[path] = yaml.safe_load(read_text(path))
    return snapshot.documents[path]
