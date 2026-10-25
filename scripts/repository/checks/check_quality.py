#!/usr/bin/env python3
"""Check Python types, YAML, manifest schemas, and Liquid templates."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.repository.config.json_config import read_json

ROOT = Path(__file__).resolve().parents[3]


def run(root: Path, *arguments: str) -> int:
    print(f"[quality] {arguments[0]}", flush=True)
    status = subprocess.run(arguments, cwd=root, check=False).returncode
    return 128 - status if status < 0 else status


def check_schemas(root: Path, files: set[Path]) -> int:
    # Reuse the editor's schema associations so CLI coverage cannot drift.
    settings = read_json(root / ".vscode/settings.json")
    associations = list(settings["yaml.schemas"].items())
    associations.extend(
        (item["url"], item["fileMatch"]) for item in settings.get("json.schemas", [])
    )
    for schema, patterns in associations:
        targets = sorted(
            {
                path.relative_to(root)
                for pattern in patterns
                for path in root.glob(pattern.lstrip("/"))
                if path.relative_to(root) in files
            }
        )
        if not targets:
            continue
        status = run(
            root,
            "check-jsonschema",
            "--schemafile",
            schema,
            *(str(path) for path in targets),
        )
        if status:
            return status

    schemas = sorted(
        path
        for path in files
        if path.parent == Path("config/schemas") and path.suffix == ".json"
    )
    if schemas:
        return run(
            root,
            "check-jsonschema",
            "--check-metaschema",
            *(str(path) for path in schemas),
        )
    return 0


def main() -> int:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
        )
        files = {
            Path(os.fsdecode(name))
            for name in output.split(b"\0")
            if name and (ROOT / os.fsdecode(name)).is_file()
        }
        for path in sorted(files):
            if path.suffix == ".json":
                read_json(ROOT / path)
        status = run(
            ROOT,
            "basedpyright",
            "--project",
            "config/pyproject.toml",
            "--pythonpath",
            sys.executable,
        )
        if status:
            return status

        yaml_files = sorted(
            str(path) for path in files if path.suffix in {".yaml", ".yml", ".cff"}
        )
        if yaml_files:
            status = run(ROOT, "yamllint", "-c", "config/yamllint.yml", *yaml_files)
            if status:
                return status
        status = check_schemas(ROOT, files)
        if status:
            return status

        templates = sorted(
            str(path)
            for path in files
            if path.is_relative_to("site") and path.suffix == ".html"
        )
        if templates:
            return run(ROOT, "djlint", "--profile=liquid", "--lint", *templates)
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
