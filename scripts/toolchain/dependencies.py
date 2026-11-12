"""Refresh reviewed Python dependency versions or report upstream tool releases."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.repository.config.python_dependencies import PYTHON_TOOLS
from scripts.repository.config.repository_config import ROOT, load_toolchain
from scripts.repository.file_updates import source_updates, write_updates

GITHUB_TOOLS = {
    "ELAN": "leanprover/elan",
    "LEAN": "leanprover/lean4",
    "RUFF": "astral-sh/ruff",
    "SHFMT": "mvdan/sh",
    "LATEXINDENT": "cmhughes/latexindent.pl",
    "GH": "cli/cli",
    "SHELLCHECK": "koalaman/shellcheck",
    "ACTIONLINT": "rhysd/actionlint",
}


def refresh_python() -> None:
    with source_updates(ROOT):
        pins = load_toolchain()
        with tempfile.TemporaryDirectory(prefix="python-lock-") as temporary:
            report = Path(temporary) / "report.json"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--dry-run",
                    "--ignore-installed",
                    "--only-binary=:all:",
                    "--report",
                    str(report),
                    *(f"{name}=={pins[key + '_VERSION']}" for name, key in PYTHON_TOOLS.items()),
                ],
                check=True,
                timeout=600,
            )
            records = json.loads(report.read_text())["install"]
            roots = {re.sub(r"[-_.]+", "-", name.lower()) for name in PYTHON_TOOLS}
            resolved = {
                item["metadata"]["name"]: item["metadata"]["version"]
                for item in records
                if re.sub(r"[-_.]+", "-", item["metadata"]["name"].lower()) not in roots
            }
            text = "# Reviewed transitive Python dependency versions; refresh with scripts/toolchain/dependencies.py.\n"
            text += "".join(
                f"{name}=={version}\n" for name, version in sorted(resolved.items(), key=lambda item: item[0].lower())
            )
            write_updates({ROOT / "config/python-dependencies.txt": text})
        print("Updated Python dependency closure; run ashaiy config generate and validate both architectures.")


def lookup(item: tuple[str, str, str]) -> dict:
    name, current, url = item
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AshaIy-dependency-report"})
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.load(response)
        latest = data["info"]["version"] if "pypi.org" in url else data.get("tag_name", data.get("version"))
        if not isinstance(latest, str):
            raise ValueError("missing release version")
        return {
            "tool": name,
            "pinned": current,
            "latest": latest,
            "different": latest.lstrip("vV") != current,
            "source": url,
        }
    except (OSError, ValueError, KeyError) as error:
        return {"tool": name, "pinned": current, "source": url, "error": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-python", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "build/dependencies/report.json")
    arguments = parser.parse_args()
    try:
        if arguments.refresh_python:
            refresh_python()
            return 0
        pins = load_toolchain()
        items = [
            (key, pins[key + "_VERSION"], f"https://pypi.org/pypi/{name}/json") for name, key in PYTHON_TOOLS.items()
        ]
        items.extend(
            (key, pins[key + "_VERSION"], f"https://api.github.com/repos/{repo}/releases/latest")
            for key, repo in GITHUB_TOOLS.items()
            if key not in {value for value in PYTHON_TOOLS.values()}
        )
        items.extend(
            (key, pins[key + "_VERSION"], f"https://rubygems.org/api/v1/gems/{name}.json")
            for key, name in (("JEKYLL", "jekyll"), ("BUNDLER", "bundler"))
        )
        with ThreadPoolExecutor(max_workers=4) as executor:
            records = list(executor.map(lookup, items))
        result = {
            "schema_version": 1,
            "tools": records,
            "manual": {
                "PYTHON_VERSION": pins["PYTHON_VERSION"],
                "TEXLIVE_ARCHIVE_DATE": pins["TEXLIVE_ARCHIVE_DATE"],
                "policy": "Review Python/base-image and TeX archive updates deliberately; update Lean and Mathlib together.",
            },
        }
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(result, indent=2) + "\n")
        print(f"Saved read-only dependency report: {arguments.output}")
        return int(any("error" in record for record in records))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
