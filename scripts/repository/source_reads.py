"""Reuse source reads and YAML parsing during one read-only check."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class StrictLoader(yaml.SafeLoader):
    """Safe YAML with explicit, unique mapping keys; merge keys are unsupported."""

    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "merge keys are unsupported; write each field explicitly",
                    key_node.start_mark,
                )
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as error:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "mapping keys must be scalar values",
                    key_node.start_mark,
                ) from error
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def parse_yaml(text: str) -> object:
    """Parse current or historical configuration using the same strict contract."""
    return yaml.load(text, Loader=StrictLoader)


def field_mapping(value: object, context: str) -> dict:
    """Validate named metadata fields without restricting general YAML mappings."""
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping")
    for key in value:
        if not isinstance(key, str):
            raise ValueError(f"{context} field names must be strings: {key!r}")
    return value


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
        return parse_yaml(read_text(path))

    if path not in snapshot.documents:
        snapshot.documents[path] = parse_yaml(read_text(path))
    return snapshot.documents[path]
