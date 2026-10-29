"""Shared transport and provenance checks for GitHub Actions artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
DOWNLOAD_TIMEOUT = 600
DOWNLOAD_MAX_TIMEOUT = 3600
DOWNLOAD_MIN_BYTES_PER_SECOND = 8 * 1024**2
DISK_RESERVE = 2 * 1024**3
DOWNLOAD_IDLE_TIMEOUT = 120
DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_POLL_INTERVAL = 1
DOWNLOAD_LOG_INTERVAL = 15


def command(*args: str) -> bytes:
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, timeout=60).stdout


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
    if manifest.get("run_id") != str(run["id"]) or manifest.get("run_attempt") != str(run["run_attempt"]):
        raise ValueError(f"{label} belongs to a different run or attempt")


def verify_digest(artifact: dict, data: bytes | Path) -> None:
    if artifact.get("digest") != f"sha256:{checksum(data)}":
        raise ValueError("GitHub artifact digest mismatch")


def require_space(path: Path, size: int, *, operation: str) -> None:
    free = shutil.disk_usage(path).free
    required = size + DISK_RESERVE
    print(
        f"{operation}: {free / 1024**3:.1f} GiB free; {required / 1024**3:.1f} GiB required including reserve",
        flush=True,
    )
    if free < required:
        raise ValueError(f"insufficient disk space for {operation}")


def download_timeout(size: int) -> float:
    return min(
        DOWNLOAD_MAX_TIMEOUT,
        DOWNLOAD_TIMEOUT + size / DOWNLOAD_MIN_BYTES_PER_SECOND,
    )


def download(repository: str, artifact: dict, target: Path, *, max_bytes: int) -> None:
    if artifact.get("expired", True) or artifact.get("size_in_bytes", max_bytes + 1) > max_bytes:
        raise ValueError("artifact is expired or too large")
    label = artifact.get("name", str(artifact["id"]))
    expected_size = artifact["size_in_bytes"]
    require_space(target.parent, expected_size, operation=f"download {label}")
    budget = download_timeout(expected_size)
    deadline = time.monotonic() + budget
    print(f"{label}: total download budget {budget:.0f}s", flush=True)
    args = ["gh", "api", f"repos/{repository}/actions/artifacts/{artifact['id']}/zip"]
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        print(
            f"Downloading {label}: attempt {attempt}/{DOWNLOAD_ATTEMPTS}, expected {expected_size / 1024**2:.1f} MiB",
            flush=True,
        )
        try:
            download_attempt(args, target, expected_size, max_bytes, deadline, label)
            print(f"Verifying GitHub digest for {label}", flush=True)
            verify_digest(artifact, target)
            print(f"Downloaded and verified {label}", flush=True)
            return
        except (subprocess.SubprocessError, ValueError) as error:
            target.unlink(missing_ok=True)
            print(f"Download failed for {label}: {error}", flush=True)
            if attempt == DOWNLOAD_ATTEMPTS or time.monotonic() >= deadline:
                raise
            # Start from zero: never append a fresh response to a partial ZIP.
            print(f"Retrying {label} with a fresh authenticated request", flush=True)


def download_attempt(
    args: list[str],
    target: Path,
    expected_size: int,
    max_bytes: int,
    deadline: float,
    label: str,
) -> None:
    started = last_progress = last_log = time.monotonic()
    previous_size = 0
    with (
        target.open("wb") as output,
        subprocess.Popen(args, cwd=ROOT, stdout=output) as process,
    ):
        try:
            while True:
                try:
                    process.wait(timeout=DOWNLOAD_POLL_INTERVAL)
                except subprocess.TimeoutExpired:
                    pass
                now = time.monotonic()
                size = target.stat().st_size
                if size > max_bytes:
                    raise ValueError("artifact is too large")
                if size != previous_size:
                    last_progress = now
                    previous_size = size
                if now - last_log >= DOWNLOAD_LOG_INTERVAL or process.returncode is not None:
                    elapsed = max(now - started, 0.001)
                    percent = 100 * size / max(expected_size, 1)
                    print(
                        f"{label}: {size / 1024**2:.1f}/{expected_size / 1024**2:.1f} "
                        f"MiB ({percent:.1f}%), {size / 1024**2 / elapsed:.2f} MiB/s, "
                        f"{now - last_progress:.0f}s without progress",
                        flush=True,
                    )
                    last_log = now
                if process.returncode is not None:
                    if process.returncode:
                        raise subprocess.CalledProcessError(process.returncode, args)
                    return
                if now >= deadline:
                    raise subprocess.TimeoutExpired(args, max(0, deadline - started))
                if now - last_progress >= DOWNLOAD_IDLE_TIMEOUT:
                    raise subprocess.TimeoutExpired(args, DOWNLOAD_IDLE_TIMEOUT)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
