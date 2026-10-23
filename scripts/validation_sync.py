"""Synchronize marked schema and shell expressions from shared validation rules."""

from __future__ import annotations

import json
import re
from pathlib import Path

from validation_patterns import load_patterns

SHELL_CONSUMERS = (
    ".github/actions/load-toolchain/action.yml",
    ".github/workflows/build-toolchain.yml",
    ".github/workflows/build.yml",
    ".github/workflows/pages.yml",
    "scripts/pages_current.sh",
    "scripts/snapshot_base.sh",
)
SCHEMA_CONSUMERS = tuple(
    f"config/schemas/{name}.schema.json"
    for name in ("books", "chapters", "sections", "modules")
)
MARKER = "validation-pattern: "
# These expressions use the same syntax in Python, JavaScript, and Bash ERE.
SHELL_PATTERNS = frozenset(
    {"sha256", "image_digest", "git_commit", "image_tag", "nonnegative_integer"}
)


def schema_patterns(value: object, patterns: dict[str, str]) -> None:
    if isinstance(value, dict):
        marker = value.get("$comment", "")
        if isinstance(marker, str) and marker.startswith(MARKER):
            name = marker.removeprefix(MARKER)
            if name not in patterns or "pattern" not in value:
                raise ValueError(f"{name}: marked schema must contain a pattern")
            value["pattern"] = "^" + patterns[name] + "$"
        for child in value.values():
            schema_patterns(child, patterns)
    elif isinstance(value, list):
        for child in value:
            schema_patterns(child, patterns)


def shell_patterns(text: str, patterns: dict[str, str], path: Path) -> str:
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        marker = line.strip().removeprefix("# ")
        if not marker.startswith(MARKER):
            continue
        name = marker.removeprefix(MARKER)
        if name not in SHELL_PATTERNS or index + 1 == len(lines):
            raise ValueError(f"{path}: unsupported shell validation pattern {name}")
        if name not in patterns:
            raise ValueError(f"{path}: missing validation pattern {name}")
        expression = patterns[name]
        # Keep generated expressions unquoted, single-token Bash ERE operands.
        if not re.fullmatch(r"[a-z0-9\[\]{}:+*-]+", expression):
            raise ValueError(f"{path}: expression for {name} is not shell portable")
        updated, count = re.subn(
            r"(?<==~ )\S+", lambda _: "^" + expression + "$", lines[index + 1]
        )
        if count != 1:
            raise ValueError(f"{path}: expected one marked Bash regex operand")
        lines[index + 1] = updated
    return "".join(lines)


def rendered_validation_consumers(root: Path) -> dict[Path, str]:
    patterns = load_patterns(root)
    updates = {}
    for relative in SCHEMA_CONSUMERS:
        path = root / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        schema_patterns(data, patterns)
        updates[path] = json.dumps(data, indent=2) + "\n"
    for relative in SHELL_CONSUMERS:
        path = root / relative
        updates[path] = shell_patterns(path.read_text(encoding="utf-8"), patterns, path)
    return updates
