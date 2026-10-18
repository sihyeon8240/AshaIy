"""Shared transport and provenance checks for GitHub Actions artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent


def command(*args: str) -> bytes:
    return subprocess.run(
        args, cwd=ROOT, check=True, capture_output=True, timeout=60
    ).stdout


def api(endpoint: str, execute: Callable = command):
    return json.loads(execute("gh", "api", endpoint))


def checksum(data: bytes | Path) -> str:
    if isinstance(data, Path):
        with data.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    return hashlib.sha256(data).hexdigest()


def eligible_run(
    run: dict,
    repository: str,
    head: str,
    *,
    workflow: str = ".github/workflows/build.yml",
    event: str = "pull_request",
) -> bool:
    return (
        run.get("event") == event
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and run.get("head_sha") == head
        and (run.get("head_repository") or {}).get("full_name") == repository
        and run.get("path") == workflow
    )


def validate_identity(manifest: dict, expected: dict, run: dict, *, label: str) -> None:
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"{label} identity differs: {key}")
    if manifest.get("run_id") != str(run["id"]) or manifest.get("run_attempt") != str(
        run["run_attempt"]
    ):
        raise ValueError(f"{label} belongs to a different run or attempt")


def verify_digest(artifact: dict, data: bytes | Path) -> None:
    if artifact.get("digest") != f"sha256:{checksum(data)}":
        raise ValueError("GitHub artifact digest mismatch")


def download(repository: str, artifact: dict, target: Path, *, max_bytes: int) -> None:
    if (
        artifact.get("expired", True)
        or artifact.get("size_in_bytes", max_bytes + 1) > max_bytes
    ):
        raise ValueError("artifact is expired or too large")
    with target.open("wb") as output:
        subprocess.run(
            ["gh", "api", f"repos/{repository}/actions/artifacts/{artifact['id']}/zip"],
            cwd=ROOT,
            stdout=output,
            check=True,
            timeout=1800,
        )
    if target.stat().st_size > max_bytes:
        raise ValueError("artifact is too large")
    verify_digest(artifact, target)
