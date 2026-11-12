"""Render previews, browser fixtures, and deployment with one Jekyll contract."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.repository.config.repository_config import load_toolchain


def render(
    jekyll: str,
    source: Path,
    destination: Path,
    *,
    base_path: str | None = None,
    config: str | None = None,
    cwd: Path | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    options = []
    if base_path is not None:
        if base_path and (not base_path.startswith("/") or base_path.startswith("//") or ".." in base_path.split("/")):
            raise ValueError("site base path must be empty or an absolute URL path")
        options.extend(("--baseurl", base_path))
    if config is not None:
        options.extend(("--config", config))
    return subprocess.run(
        [jekyll, "build", "--source", str(source), "--destination", str(destination), "--disable-disk-cache", *options],
        env={**os.environ, "JEKYLL_ENV": "production"},
        cwd=cwd,
        text=True,
        capture_output=capture_output,
        check=True,
        timeout=120,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("site"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--base-path", default="")
    arguments = parser.parse_args()
    try:
        jekyll = shutil.which("jekyll")
        if jekyll is None:
            raise ValueError("Jekyll is unavailable; use the pinned development image")
        version = subprocess.check_output([jekyll, "--version"], text=True, timeout=10).strip()
        if version != "jekyll " + load_toolchain()["JEKYLL_VERSION"]:
            raise ValueError(f"unexpected Jekyll version: {version}; use the pinned development image")
        render(jekyll, arguments.source, arguments.destination, base_path=arguments.base_path)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
