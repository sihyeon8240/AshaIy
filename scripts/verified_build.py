#!/usr/bin/env python3
"""Record strict PDF builds and conservatively reuse merged PR artifacts."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

import github_artifacts
from github_artifacts import checksum, eligible_run

ROOT = Path(__file__).resolve().parent.parent
POLICY = "strict-pdf-v1"
FILES = ("book.pdf", "book.log")
MAX_BYTES = 100 * 1024 * 1024


def command(*args: str) -> bytes:
    return github_artifacts.command(*args)


def api(endpoint: str):
    return github_artifacts.api(endpoint, command)


def identity(book: str, image: str, *, candidate: bool = False) -> dict:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", book):
        raise ValueError("invalid book slug")
    pattern = (
        r"sha256:[0-9a-f]{64}"
        if candidate
        else r"ghcr\.io/[a-z0-9/_.-]+@sha256:[0-9a-f]{64}"
    )
    if not re.fullmatch(pattern, image):
        raise ValueError(
            "a candidate image ID or immutable registry digest is required"
        )
    return {
        "policy": "strict-candidate-pdf-v1" if candidate else POLICY,
        "book": book,
        "image_id" if candidate else "image": image,
        "platform": "linux/amd64",
        "tree": command("git", "rev-parse", "HEAD^{tree}").decode().strip(),
    }


def record(expected: dict, directory: Path) -> None:
    command("python3", "scripts/check_log.py", "--strict", str(directory / "book.log"))
    files = {name: (directory / name).read_bytes() for name in FILES}
    if not files["book.pdf"].startswith(b"%PDF-"):
        raise ValueError("build did not produce a PDF")
    manifest = {
        **expected,
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "checksums": {name: checksum(data) for name, data in files.items()},
    }
    (directory / "verified-build.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
    )


def verify_archive(data: bytes, expected: dict, run: dict) -> dict[str, bytes]:
    if len(data) > MAX_BYTES:
        raise ValueError("artifact is too large")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [*FILES, "verified-build.json"]
        if sorted(archive.namelist()) != sorted(names):
            raise ValueError("unexpected artifact files")
        if sum(info.file_size for info in archive.infolist()) > MAX_BYTES:
            raise ValueError("expanded artifact is too large")
        manifest = json.loads(archive.read("verified-build.json"))
        if not isinstance(manifest, dict):
            raise ValueError("invalid build manifest")
        github_artifacts.validate_identity(manifest, expected, run, label="build")
        files = {name: archive.read(name) for name in FILES}
        if manifest.get("checksums") != {
            name: checksum(content) for name, content in files.items()
        }:
            raise ValueError("artifact checksum mismatch")
        if not files["book.pdf"].startswith(b"%PDF-") or not files["book.log"]:
            raise ValueError("missing PDF or build log")
        return files


def restore_artifact(
    repository: str, artifact: dict, expected: dict, run: dict, directory: Path
) -> None:
    data = command(
        "gh",
        "api",
        f"repos/{repository}/actions/artifacts/{artifact['id']}/zip",
    )
    github_artifacts.verify_digest(artifact, data)
    files = verify_archive(data, expected, run)
    install(files, directory)


def install(files: dict[str, bytes], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (directory / name).write_bytes(content)
    command(
        "python3",
        "scripts/check_log.py",
        "--strict",
        str(directory / "book.log"),
    )


def record_candidate(expected: dict, directory: Path, archive: Path) -> None:
    record(expected, directory)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name in (*FILES, "verified-build.json"):
            output.write(directory / name, name)


def restore_candidate(expected: dict, directory: Path, archive: Path) -> bool:
    if archive.stat().st_size > MAX_BYTES:
        raise ValueError("artifact is too large")
    run = {
        "id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
    }
    files = verify_archive(archive.read_bytes(), expected, run)
    install(files, directory)
    print(f"Reused candidate PDF for {expected['book']} from this run and attempt")
    return True


def restore(expected: dict, directory: Path) -> bool:
    repository = os.environ["GITHUB_REPOSITORY"]
    commit = os.environ["GITHUB_SHA"]
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
            for artifact in artifacts:
                if (
                    artifact["name"] != f"{expected['book']}-verified-build"
                    or artifact.get("expired", True)
                    or artifact.get("size_in_bytes", MAX_BYTES + 1) > MAX_BYTES
                ):
                    continue
                try:
                    restore_artifact(repository, artifact, expected, run, directory)
                    print(
                        f"Reused verified PDF from PR #{pull['number']}, run {run['id']}"
                    )
                    return True
                except (
                    ValueError,
                    KeyError,
                    OSError,
                    zipfile.BadZipFile,
                    subprocess.SubprocessError,
                ) as error:
                    print(f"Artifact cannot be reused; rebuilding: {error}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("record", "restore", "record-candidate", "restore-candidate")
    )
    parser.add_argument("--book", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument(
        "--candidate-directory", type=Path, default=ROOT / "build/candidate-pdfs"
    )
    args = parser.parse_args()
    candidate = args.mode.endswith("-candidate")
    expected = (
        identity(args.book, args.image, candidate=True)
        if candidate
        else identity(args.book, args.image)
    )
    directory = ROOT / "build" / args.book
    archive = args.candidate_directory / f"{args.book}.zip"
    if args.mode == "record-candidate":
        record_candidate(expected, directory, archive)
        return
    if args.mode == "record":
        record(expected, directory)
        return
    reused = False
    try:
        reused = (
            restore_candidate(expected, directory, archive)
            if candidate
            else restore(expected, directory)
        )
    except (
        ValueError,
        KeyError,
        OSError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as error:
        print(f"Verified artifact unavailable; rebuilding: {error}")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"reused={str(reused).lower()}\n")


if __name__ == "__main__":
    main()
