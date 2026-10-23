#!/usr/bin/env python3
"""Preserve tested images and reuse matching, successful same-repository PR runs."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import github_artifacts
from github_artifacts import checksum, eligible_run

ROOT = Path(__file__).resolve().parent.parent
POLICY = "toolchain-candidate-v1"
MAX_BYTES = 20 * 1024**3


def command(*args: str) -> str:
    return github_artifacts.command(*args).decode().strip()


def api(endpoint: str):
    return github_artifacts.api(endpoint, command)


def identity(arch: str) -> dict:
    return {
        "policy": POLICY,
        "tree": command("git", "rev-parse", "HEAD^{tree}"),
        "arch": arch,
    }


def record(arch: str, image: str, directory: Path) -> None:
    manifest = {
        **identity(arch),
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "image_id": command("docker", "image", "inspect", image, "--format", "{{.Id}}"),
        "checksum": checksum(directory / "image.tar.gz"),
    }
    (directory / "candidate.json").write_text(json.dumps(manifest) + "\n")


def validate_manifest(manifest: dict, expected: dict, run: dict) -> None:
    github_artifacts.validate_identity(manifest, expected, run, label="candidate")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", manifest.get("image_id", "")):
        raise ValueError("invalid candidate image ID")


def load_candidate(
    repository: str, artifact: dict, expected: dict, run: dict, image: str
) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        archive_path = directory / "candidate.zip"
        github_artifacts.download(
            repository, artifact, archive_path, max_bytes=MAX_BYTES
        )
        print(f"Extracting {expected['arch']} candidate archive", flush=True)
        with zipfile.ZipFile(archive_path) as archive:
            if sorted(archive.namelist()) != ["candidate.json", "image.tar.gz"]:
                raise ValueError("unexpected candidate files")
            if sum(info.file_size for info in archive.infolist()) > MAX_BYTES:
                raise ValueError("expanded candidate is too large")
            if archive.getinfo("candidate.json").file_size > 16384:
                raise ValueError("candidate manifest is too large")
            manifest = json.loads(archive.read("candidate.json"))
            if not isinstance(manifest, dict):
                raise ValueError("invalid candidate manifest")
            validate_manifest(manifest, expected, run)
            image_path = directory / "image.tar.gz"
            with (
                archive.open("image.tar.gz") as source,
                image_path.open("wb") as target,
            ):
                shutil.copyfileobj(source, target)
        archive_path.unlink()
        print(f"Verifying {expected['arch']} image checksum", flush=True)
        if checksum(image_path) != manifest["checksum"]:
            raise ValueError("candidate image checksum mismatch")
        print(f"Loading {expected['arch']} image into Docker", flush=True)
        subprocess.run(
            ["docker", "load", "--input", str(image_path)], check=True, timeout=600
        )
        image_id = manifest["image_id"]
        arch = command(
            "docker", "image", "inspect", image_id, "--format", "{{.Architecture}}"
        )
        if arch != expected["arch"]:
            raise ValueError("candidate architecture mismatch")
        command("docker", "tag", image_id, image)
        print(f"Loaded and verified {expected['arch']} image", flush=True)


def restore(arch: str, image: str) -> bool:
    repository = os.environ["GITHUB_REPOSITORY"]
    commit = os.environ["GITHUB_SHA"]
    expected = identity(arch)
    pulls = api(f"repos/{repository}/commits/{commit}/pulls?per_page=100")
    for pull in pulls:
        if (
            not pull.get("merged_at")
            or pull.get("merge_commit_sha") != commit
            or pull.get("base", {}).get("ref") != "main"
            or (pull.get("head", {}).get("repo") or {}).get("full_name") != repository
        ):
            continue
        head = pull["head"]["sha"]
        # Bind provenance to GitHub's commit tree, not an artifact's own claims.
        if (
            api(f"repos/{repository}/git/commits/{head}")["tree"]["sha"]
            != expected["tree"]
        ):
            continue
        runs = api(
            f"repos/{repository}/actions/workflows/build.yml/runs"
            f"?event=pull_request&status=success&head_sha={head}&per_page=30"
        )["workflow_runs"]
        for run in runs:
            if not eligible_run(run, repository, head):
                continue
            artifacts = api(
                f"repos/{repository}/actions/runs/{run['id']}/artifacts?per_page=100"
            )["artifacts"]
            # Both architectures must survive; never promote half of a candidate.
            candidates = {
                artifact["name"]: artifact
                for artifact in artifacts
                if not artifact.get("expired", True)
                and artifact.get("size_in_bytes", MAX_BYTES + 1) <= MAX_BYTES
            }
            if not all(
                f"toolchain-image-{item}" in candidates for item in ("amd64", "arm64")
            ):
                continue
            load_candidate(
                repository, candidates[f"toolchain-image-{arch}"], expected, run, image
            )
            print(f"Reused {arch} candidate from PR #{pull['number']}, run {run['id']}")
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("record", "restore", "publish-pr"))
    parser.add_argument("--arch", choices=("amd64", "arm64"))
    parser.add_argument("--image")
    args = parser.parse_args()
    if args.mode == "publish-pr":
        import image_pr

        image_pr.publish(load_candidate, policy=POLICY, max_bytes=MAX_BYTES)
        return
    if not args.arch or not args.image:
        parser.error("--arch and --image are required for record and restore")
    if args.mode == "record":
        record(args.arch, args.image, ROOT / "build/toolchain-image")
        return
    reused = False
    try:
        reused = restore(args.arch, args.image)
    except (
        ValueError,
        KeyError,
        OSError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as error:
        print(f"Candidate unavailable; building from source: {error}")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"reused={str(reused).lower()}\n")


if __name__ == "__main__":
    main()
