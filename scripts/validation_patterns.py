"""Read shared validation expressions without optional Python dependencies."""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_patterns(root: Path = ROOT) -> dict[str, str]:
    path = root / "config/validation-patterns.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "patterns"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["patterns"], dict)
        or not data["patterns"]
    ):
        raise ValueError(f"{path}: unsupported validation patterns configuration")

    for name, expression in data["patterns"].items():
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[a-z][a-z0-9_]*", name)
            or not isinstance(expression, str)
            or not expression
            or any(character in expression for character in "\r\n")
        ):
            raise ValueError(f"{path}: invalid validation pattern {name!r}")

    resolved: dict[str, str] = {}

    def resolve(name: str, visiting: frozenset[str]) -> str:
        if name in resolved:
            return resolved[name]
        if name not in data["patterns"] or name in visiting:
            raise ValueError(f"{path}: unknown or cyclic validation pattern {name}")
        expression = re.sub(
            r"\$\{([a-z][a-z0-9_]*)\}",
            lambda match: resolve(match[1], visiting | {name}),
            data["patterns"][name],
        )
        try:
            re.compile(expression)
        except re.error as error:
            raise ValueError(
                f"{path}: invalid expression for {name}: {error}"
            ) from error
        resolved[name] = expression
        return expression

    for name in data["patterns"]:
        resolve(name, frozenset())
    return resolved


@cache
def _runtime_patterns() -> dict[str, str]:
    # CLI invocations use one configuration snapshot; generation loads its root afresh.
    return load_patterns()


def validation_pattern(name: str) -> str:
    return _runtime_patterns()[name]
