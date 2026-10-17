#!/usr/bin/env python3
"""Check task dependencies without requiring the complete container image."""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES = {
    "pdf": ("bash", "git", "latexmk", "lualatex", "kpsewhich", "biber"),
    "lean": ("bash", "git", "elan", "lean", "lake"),
    "format": ("bash", "rg", "ruff", "shfmt", "shellcheck", "latexindent"),
    "site": ("ruby", "bundle", "jekyll"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES)
    arguments = parser.parse_args()
    errors = []

    if platform.system() != "Linux":
        errors.append("local support requires Linux or WSL2")
    if sys.version_info < (3, 14):
        errors.append("Python 3.14 or newer is required")
    try:
        print(f"PyYAML {importlib.metadata.version('PyYAML')}")
    except importlib.metadata.PackageNotFoundError:
        errors.append("PyYAML missing; run scripts/setup-local.sh")

    for command in PROFILES[arguments.profile]:
        executable = shutil.which(command)
        if executable:
            print(f"{command}: {executable}")
        else:
            errors.append(f"{command} missing")

    if arguments.profile == "pdf" and shutil.which("kpsewhich"):
        for filename in (
            "fontspec.sty",
            "biblatex.sty",
            "microtype.sty",
            "cleveref.sty",
        ):
            if subprocess.run(["kpsewhich", filename], capture_output=True).returncode:
                errors.append(f"TeX package missing: {filename}")

    if arguments.profile == "lean" and shutil.which("lean"):
        expected = (ROOT / "lean/lean-toolchain").read_text().strip().split(":")[-1]
        result = subprocess.run(
            ["lean", "--version"], cwd=ROOT / "lean", capture_output=True, text=True
        )
        if result.returncode or expected.removeprefix("v") not in result.stdout:
            errors.append(f"Lean {expected} required by lean/lean-toolchain")

    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"{arguments.profile} tools are ready; run the task to verify compatibility.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
