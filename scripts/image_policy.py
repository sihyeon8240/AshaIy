#!/usr/bin/env python3
"""Read image build policy at runtime without generated workflow fragments."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.repository_config import ROOT, load_image_build


def input_hash(root: Path = ROOT) -> str:
    config = load_image_build(root)
    digest = hashlib.sha256()
    for path in config["inputs"]:
        source = root / path
        mode = source.lstat().st_mode
        if not stat.S_ISREG(mode) or any(
            parent.is_symlink() for parent in source.parents if parent != root.parent
        ):
            raise ValueError(
                f"image input must be a regular file without symlinks: {path}"
            )
        with source.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        executable = "100755" if mode & 0o111 else "100644"
        digest.update(f"{executable} {checksum}  {path}\n".encode())
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
                output = json.dumps(
                    {"include": config["platforms"]}, separators=(",", ":")
                )
            else:
                output = " ".join(item["arch"] for item in config["platforms"])
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
