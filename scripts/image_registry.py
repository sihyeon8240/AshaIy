#!/usr/bin/env python3
"""Promote the current main image and report bootstrap readiness."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from repository_config import IMAGE, image_name, load_image, load_image_build


def command(*args: str, env: dict | None = None) -> str:
    return subprocess.run(
        args, env=env, check=True, capture_output=True, text=True, timeout=60
    ).stdout.strip()


def report(image: str) -> None:
    if not IMAGE.fullmatch(image):
        raise ValueError("expected an immutable GHCR image reference")
    pin = load_image()
    name = image_name(pin)
    if image_name(image) != name:
        raise ValueError("published image does not belong to the configured package")
    commit = os.environ["GITHUB_SHA"]
    current = command("git", "ls-remote", "origin", "refs/heads/main").split()
    messages = [f"Published toolchain: `{image}`"]
    if current and current[0] == commit:
        command(
            "docker",
            "buildx",
            "imagetools",
            "create",
            "--tag",
            f"{name}:latest",
            "--tag",
            f"{name}:sha-{commit}",
            image,
        )
        messages.append("Updated latest and source-commit aliases for current main.")
    else:
        messages.append(
            "Main advanced; skipped mutable alias updates for this older run."
        )
    platforms = ", ".join(item["arch"] for item in load_image_build()["platforms"])
    messages.append(f"Validated Linux platforms: {platforms}.")
    if pin == image:
        messages.append("The local and Dev Container pin matches the prepared image.")
    else:
        messages.append(
            "The local pin differs. On a development branch, run "
            f"`ashaiy image pin --digest {image.split('@sha256:')[1]}` and submit the synchronized pin."
        )
    # A new GHCR package is private even when its repository is public.
    with tempfile.TemporaryDirectory() as temporary:
        try:
            manifest = json.loads(
                command(
                    "docker",
                    "manifest",
                    "inspect",
                    image,
                    env={**os.environ, "DOCKER_CONFIG": temporary},
                )
            )
            required = {
                ("linux", item["arch"]) for item in load_image_build()["platforms"]
            }
            available = {
                (
                    entry.get("platform", {}).get("os"),
                    entry.get("platform", {}).get("architecture"),
                )
                for entry in manifest.get("manifests", [])
            }
            if not required <= available:
                raise ValueError("anonymous index is missing a configured platform")
            messages.append(
                "Anonymous image lookup succeeded; fork PRs and local pulls can access the index."
            )
        except (subprocess.SubprocessError, ValueError) as error:
            messages.append(
                "Anonymous image lookup failed. For fork PRs or anonymous local pulls, "
                "make the GHCR package public and verify registry connectivity. "
                f"Diagnostic: {type(error).__name__}."
            )
            print("::warning::Anonymous toolchain image access is not verified.")
    text = "\n\n".join(messages) + "\n"
    print(text)
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if destination:
        with Path(destination).open("a") as stream:
            stream.write(text)


if __name__ == "__main__":
    report(os.environ["IMAGE_REF"])
