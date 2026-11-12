"""Record installed toolchain packages and their manifest digests using the stdlib."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
from pathlib import Path
from typing import TypedDict


class PythonPackage(TypedDict):
    name: str
    version: str
    record_sha256: str | None


def captured(command: list[str]) -> str | None:
    if shutil.which(command[0]) is None:
        return None
    return subprocess.check_output(command, text=True, timeout=60).strip()


def inventory() -> dict:
    packages: list[PythonPackage] = []
    for distribution in importlib.metadata.distributions():
        record = distribution.read_text("RECORD")
        packages.append(
            {
                "name": distribution.metadata["Name"] or "unknown",
                "version": distribution.version,
                "record_sha256": hashlib.sha256(record.encode()).hexdigest() if record is not None else None,
            }
        )
    return {
        "schema_version": 1,
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python": sorted(packages, key=lambda item: item["name"].lower()),
        "debian": captured(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"]),
        "ruby": captured(["gem", "list", "--local"]),
        "texlive": captured(["tlmgr", "info", "--only-installed", "--data", "name,localrev"]),
        "lean": captured(["lean", "--version"]),
        "note": "Package/RECORD inventory complements image digests; it is not a bit-reproducible rebuild guarantee.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(inventory(), indent=2) + "\n")
    print(f"Saved installed toolchain inventory: {arguments.output}")


if __name__ == "__main__":
    main()
