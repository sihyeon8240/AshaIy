#!/usr/bin/env python3
"""Read image build policy at runtime without generated workflow fragments."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import stat
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.repository.config.repository_config import ROOT, load_image_build


def docker_instructions(text: str):
    """Join continuations while retaining the physical source line for diagnostics."""
    pending = ""
    start = 1
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not pending:
            start = number
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        yield start, pending + line
        pending = ""
    if pending:
        raise ValueError(f"Dockerfile:{start}: unfinished continuation")


def validate_context(root: Path, inputs: list[str]) -> None:
    """Keep every repository COPY source and its fixed permissions in the hash."""
    recipe = root / ".devcontainer/Dockerfile"
    if not recipe.is_file():
        return
    required = {".devcontainer/Dockerfile", ".devcontainer/Dockerfile.dockerignore"}
    stages: set[str] = set()
    for number, line in docker_instructions(recipe.read_text()):
        parts = line.strip().split(None, 1)
        if not parts:
            continue
        instruction = parts[0].upper()
        if instruction in {"FROM", "COPY"} and len(parts) != 2:
            raise ValueError(f"{recipe}:{number}: missing {instruction} arguments")
        if instruction == "FROM":
            words = shlex.split(parts[1])
            base = next((word for word in words if not word.startswith("--")), None)
            if base is None:
                raise ValueError(f"{recipe}:{number}: missing base image")
            if base != "scratch" and base not in stages and not re.search(r"@sha256:[0-9a-f]{64}$", base):
                raise ValueError(f"{recipe}:{number}: FROM requires an immutable digest")
            if len(words) >= 3 and words[-2].upper() == "AS":
                stages.add(words[-1])
            continue
        if instruction == "ADD":
            raise ValueError(f"{recipe}:{number}: use explicit COPY sources instead of ADD")
        if instruction != "COPY":
            continue
        arguments = parts[1]
        options = []
        while arguments.startswith("--"):
            option_parts = arguments.split(None, 1)
            if len(option_parts) != 2:
                raise ValueError(f"{recipe}:{number}: missing COPY sources")
            options.append(option_parts[0])
            arguments = option_parts[1]
        source_stage = next((option[7:] for option in options if option.startswith("--from=")), None)
        if source_stage is not None:
            if (
                source_stage not in stages
                and not source_stage.isdecimal()
                and not re.search(r"@sha256:[0-9a-f]{64}$", source_stage)
            ):
                raise ValueError(f"{recipe}:{number}: external COPY requires an immutable digest")
            continue
        if not any(re.fullmatch(r"--chmod=0?[0-7]{3}", option) for option in options):
            raise ValueError(f"{recipe}:{number}: repository COPY requires explicit --chmod")
        sources = json.loads(arguments) if arguments.startswith("[") else shlex.split(arguments)
        if not isinstance(sources, list) or len(sources) < 2 or not all(isinstance(source, str) for source in sources):
            raise ValueError(f"{recipe}:{number}: invalid COPY sources")
        required.update(sources[:-1])
    missing = sorted(required - set(inputs))
    if missing:
        raise ValueError("unhashed Docker build inputs: " + ", ".join(missing))


def input_hash(root: Path = ROOT) -> str:
    """Hash the publication transcript shared by independently deployed readers.

    Docker COPY fixes input permissions in the recipe, so checkout mode bits do
    not change image contents. Keep this byte protocol stable across PR and main.
    """
    root = root.resolve()
    config = load_image_build(root)
    validate_context(root, config["inputs"])
    digest = hashlib.sha256()
    for path in config["inputs"]:
        source = root / path
        mode = source.lstat().st_mode
        if not stat.S_ISREG(mode) or any(
            parent.is_symlink() for parent in source.parents if parent.is_relative_to(root)
        ):
            raise ValueError(f"image input must be a regular file without symlinks: {path}")
        with source.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        digest.update(f"{checksum}  {path}\n".encode())
    platforms = ",".join(f"linux/{item['arch']}" for item in config["platforms"])
    digest.update(f"{config['policy_version']}\n{platforms}\n".encode())
    return digest.hexdigest()[:12]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("consumer", choices=("hash", "matrix", "architectures"))
    args = parser.parse_args()
    try:
        if args.consumer == "hash":
            output = input_hash()
        else:
            config = load_image_build()
            if args.consumer == "matrix":
                output = json.dumps({"include": config["platforms"]}, separators=(",", ":"))
            else:
                output = " ".join(item["arch"] for item in config["platforms"])
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
