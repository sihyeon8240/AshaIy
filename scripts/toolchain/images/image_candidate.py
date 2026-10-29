#!/usr/bin/env python3
"""Preserve tested images and reuse matching, successful same-repository PR runs."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.ci import github_artifacts
from scripts.ci.github_artifacts import checksum, eligible_run
from scripts.repository.config.repository_config import load_image_build
from scripts.repository.config.validation_patterns import validation_pattern
from scripts.toolchain.images.image_policy import input_hash

ROOT = Path(__file__).resolve().parents[3]
POLICY = "toolchain-candidate-v1"
MAX_BYTES = 20 * 1024**3
MAX_IMAGE_BYTES = 40 * 1024**3


def command(*args: str) -> str:
    return github_artifacts.command(*args).decode().strip()


def api(endpoint: str):
    return github_artifacts.api(endpoint, command)


def identity(arch: str) -> dict:
    return {
        "policy": POLICY,
        "tree": command("git", "rev-parse", "HEAD^{tree}"),
        "arch": arch,
        "image_tag": "texlive-" + input_hash(ROOT),
    }


def record(arch: str, image: str, directory: Path) -> None:
    archive = directory / "image.tar.gz"
    if not 0 < archive.stat().st_size <= MAX_BYTES:
        raise ValueError("candidate archive is empty or too large")
    manifest = {
        **identity(arch),
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "image_id": command("docker", "image", "inspect", image, "--format", "{{.Id}}"),
        "checksum": checksum(archive),
    }
    (directory / "candidate.json").write_text(json.dumps(manifest) + "\n")


def validate_manifest(manifest: dict, expected: dict, run: dict) -> None:
    github_artifacts.validate_identity(manifest, expected, run, label="candidate")
    if not re.fullmatch(validation_pattern("image_digest"), manifest.get("image_id", "")):
        raise ValueError("invalid candidate image ID")


def check_archive(image_path: Path) -> int:
    expanded = 0
    with gzip.open(image_path, "rb") as stream:
        while chunk := stream.read(8 * 1024**2):
            expanded += len(chunk)
            if expanded > MAX_IMAGE_BYTES:
                raise ValueError("expanded Docker image is too large")
    if not expanded:
        raise ValueError("empty Docker image archive")
    storage = Path(command("docker", "info", "--format", "{{.DockerRootDir}}"))
    if not storage.is_absolute() or not storage.is_dir():
        raise ValueError("Docker storage must be locally accessible for disk checks")
    github_artifacts.require_space(storage, expanded, operation="load Docker image")
    print(f"Expanded Docker archive: {expanded / 1024**3:.1f} GiB", flush=True)
    return expanded


def load_candidate(repository: str, artifact: dict, expected: dict, run: dict, image: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        archive_path = directory / "candidate.zip"
        github_artifacts.download(repository, artifact, archive_path, max_bytes=MAX_BYTES)
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
            github_artifacts.require_space(
                directory,
                archive.getinfo("image.tar.gz").file_size,
                operation="extract candidate archive",
            )
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
        check_archive(image_path)
        print(f"Loading {expected['arch']} image into Docker", flush=True)
        subprocess.run(["docker", "load", "--input", str(image_path)], check=True, timeout=600)
        image_path.unlink()
        image_id = manifest["image_id"]
        arch = command("docker", "image", "inspect", image_id, "--format", "{{.Architecture}}")
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
        if api(f"repos/{repository}/git/commits/{head}")["tree"]["sha"] != expected["tree"]:
            continue
        runs = api(
            f"repos/{repository}/actions/workflows/build.yml/runs"
            f"?event=pull_request&status=success&head_sha={head}&per_page=30"
        )["workflow_runs"]
        for run in runs:
            if not eligible_run(run, repository, head):
                continue
            artifacts = api(f"repos/{repository}/actions/runs/{run['id']}/artifacts?per_page=100")["artifacts"]
            # Both architectures must survive; never promote half of a candidate.
            candidates = {
                artifact["name"]: artifact
                for artifact in artifacts
                if not artifact.get("expired", True) and artifact.get("size_in_bytes", MAX_BYTES + 1) <= MAX_BYTES
            }
            architectures = [item["arch"] for item in load_image_build(ROOT)["platforms"]]
            if not all(f"toolchain-image-{item}" in candidates for item in architectures):
                continue
            load_candidate(repository, candidates[f"toolchain-image-{arch}"], expected, run, image)
            print(f"Reused {arch} candidate from PR #{pull['number']}, run {run['id']}")
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("record", "restore", "publish-pr", "inspect"))
    parser.add_argument("--arch", choices=("amd64", "arm64"))
    parser.add_argument("--image")
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if args.mode == "inspect":
        if not args.archive:
            parser.error("--archive is required for inspect")
        check_archive(args.archive)
        return
    if args.mode == "publish-pr":
        from scripts.toolchain.images import image_pr

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
