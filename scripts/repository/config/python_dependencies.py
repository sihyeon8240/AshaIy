"""Render top-level tool pins and the reviewed Python dependency closure."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.repository.file_updates import read_source

PYTHON_TOOLS = {
    "PyYAML": "PYYAML",
    "ruff": "RUFF",
    "coverage": "COVERAGE",
    "hypothesis": "HYPOTHESIS",
    "playwright": "PLAYWRIGHT",
    "ty": "TY",
    "yamllint": "YAMLLINT",
    "djlint": "DJLINT",
    "check-jsonschema": "CHECK_JSONSCHEMA",
}


def requirements(root: Path, toolchain: dict[str, str]) -> str:
    lines = [f"{name}=={toolchain[key + '_VERSION']}" for name, key in PYTHON_TOOLS.items()]
    seen = {re.sub(r"[-_.]+", "-", name.lower()) for name in PYTHON_TOOLS}
    for line in read_source(root / "config/python-dependencies.txt").splitlines():
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)", line)
        if match is None:
            raise ValueError(f"invalid Python dependency pin: {line}")
        name = re.sub(r"[-_.]+", "-", match[1].lower())
        if name in seen:
            raise ValueError(f"duplicate or top-level Python dependency pin: {name}")
        seen.add(name)
        lines.append(line)
    return "\n".join(lines) + "\n"
