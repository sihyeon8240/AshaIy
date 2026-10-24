"""Read unambiguous JSON configuration without optional dependencies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def unique_mapping(pairs: list[tuple[str, object]]) -> dict:
    values = {}
    for key, value in pairs:
        if key in values:
            raise ValueError(f"duplicate JSON key: {key}")
        values[key] = value
    return values


def parse_json(text: str) -> Any:
    def reject_constant(value: str):
        raise ValueError(f"invalid JSON constant: {value}")

    return json.loads(
        text, object_pairs_hook=unique_mapping, parse_constant=reject_constant
    )


def read_json(path: Path):
    try:
        return parse_json(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise ValueError(f"{path}: {error}") from error
