#!/usr/bin/env python3
"""Restore an original release package after verifying its main CI gates."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path

import yaml
from book_manifest import SLUG_PATTERN, normalize_manifest, version_key
from github_artifacts import api, checksum, command, download, validate_identity

try:
    from scripts.validation_patterns import validation_pattern
except ModuleNotFoundError:
    from validation_patterns import validation_pattern

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 100 * 1024**2


def validate_run(run: dict, repository: str) -> str:
    source = run.get("head_sha", "")
    if (
        run.get("event") != "push"
        or run.get("head_branch") != "main"
        or run.get("status") != "completed"
        or run.get("path") != ".github/workflows/build.yml"
        or (run.get("head_repository") or {}).get("full_name") != repository
        or not re.fullmatch(validation_pattern("git_commit"), source)
    ):
        raise ValueError("retry requires a completed main textbook CI run")
    return source


def validate_jobs(jobs: list[dict], book: str) -> None:
    for name in ("Check sources", "Verify textbook builds", f"Build {book}"):
        matches = [job for job in jobs if job.get("name") == name]
        if len(matches) != 1 or matches[0].get("conclusion") != "success":
            raise ValueError(f"source run did not pass {name}")


def archive_manifest(path: Path, names: set[str]) -> dict:
    with zipfile.ZipFile(path) as archive:
        if sorted(archive.namelist()) != sorted(names):
            raise ValueError("unexpected release package files")
        if sum(info.file_size for info in archive.infolist()) > MAX_BYTES:
            raise ValueError("expanded release package is too large")
        if archive.getinfo("release-build.json").file_size > 16384:
            raise ValueError("release manifest is too large")
        manifest = json.loads(archive.read("release-build.json"))
    if not isinstance(manifest, dict):
        raise ValueError("invalid release manifest")
    return manifest


def validate_archive(path: Path, expected: dict, run: dict) -> dict[str, bytes]:
    pdf = f"{expected['book']}-v{expected['version']}.pdf"
    names = {pdf, "SHA256SUMS", "release-build.json"}
    manifest = archive_manifest(path, names)
    validate_identity(manifest, expected, run, label="release")
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in names}
    checksums = {name: checksum(files[name]) for name in (pdf, "SHA256SUMS")}
    if manifest.get("checksums") != checksums:
        raise ValueError("release package checksum mismatch")
    if not files[pdf].startswith(b"%PDF-"):
        raise ValueError("release package lacks a PDF")
    if files["SHA256SUMS"] != f"{checksums[pdf]}  {pdf}\n".encode():
        raise ValueError("release PDF differs from SHA256SUMS")
    return files


def collection(endpoint: str, key: str) -> list[dict]:
    result = []
    page = 1
    while True:
        batch = api(f"{endpoint}?per_page=100&page={page}")[key]
        result.extend(batch)
        if len(batch) < 100:
            return result
        page += 1


def restore(run_id: str, book: str, version: str, directory: Path) -> str:
    if not re.fullmatch(
        validation_pattern("positive_integer"), run_id
    ) or not SLUG_PATTERN.fullmatch(book):
        raise ValueError("invalid source run or book")
    version_key(version)
    repository = os.environ["GITHUB_REPOSITORY"]
    run = api(f"repos/{repository}/actions/runs/{run_id}")
    if str(run.get("id")) != run_id:
        raise ValueError("source run ID mismatch")
    source = validate_run(run, repository)
    command("git", "fetch", "--no-tags", "origin", "main")
    command("git", "merge-base", "--is-ancestor", source, "origin/main")
    manifest = normalize_manifest(
        yaml.safe_load(command("git", "show", f"{source}:config/books.yml").decode())
    )
    entry = next((item for item in manifest["books"] if item["slug"] == book), None)
    if not entry or not entry["release"] or entry["version"] != version:
        raise ValueError("requested release differs from the original source manifest")
    artifacts = collection(
        f"repos/{repository}/actions/runs/{run_id}/artifacts", "artifacts"
    )
    matches = [
        artifact for artifact in artifacts if artifact["name"] == f"{book}-release"
    ]
    if len(matches) != 1:
        raise ValueError("original release artifact is missing or ambiguous")
    expected = {
        "policy": "release-package-v1",
        "book": book,
        "version": version,
        "source_sha": source,
    }
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "release.zip"
        download(repository, matches[0], archive, max_bytes=MAX_BYTES)
        names = {f"{book}-v{version}.pdf", "SHA256SUMS", "release-build.json"}
        recorded = archive_manifest(archive, names)
        attempt = recorded.get("run_attempt", "")
        if (
            recorded.get("run_id") != run_id
            or not isinstance(attempt, str)
            or not re.fullmatch(validation_pattern("positive_integer"), attempt)
            or int(attempt) > run["run_attempt"]
        ):
            raise ValueError("invalid original package run attempt")
        original = api(f"repos/{repository}/actions/runs/{run_id}/attempts/{attempt}")
        if (
            str(original.get("id")) != run_id
            or original.get("run_attempt") != int(attempt)
            or validate_run(original, repository) != source
        ):
            raise ValueError("original package attempt differs from its source run")
        files = validate_archive(archive, expected, original)
        jobs = collection(
            f"repos/{repository}/actions/runs/{run_id}/attempts/{attempt}/jobs", "jobs"
        )
        validate_jobs(jobs, book)
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (directory / name).write_bytes(data)
    return source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--book", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    source = restore(args.run_id, args.book, args.version, ROOT / "build/release-retry")
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"source_sha={source}\n")


if __name__ == "__main__":
    main()
