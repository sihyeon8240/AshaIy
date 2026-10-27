#!/usr/bin/env python3
"""Measure CI build phases without changing their commands or exit statuses."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.repository.config.validation_patterns import validation_pattern

ROOT = Path(__file__).resolve().parents[2]
STAGES = (
    "job",
    "pre-build",
    "reuse",
    "cache",
    "image",
    "compile",
    "log",
    "publication",
)
POLICY = "book-metrics-v1"


def start(directory: Path, stage: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stage}.start.json").write_text(
        json.dumps({"monotonic_ns": time.monotonic_ns(), "unix_ns": time.time_ns()})
        + "\n",
        encoding="utf-8",
    )
    (directory / f"{stage}.json").unlink(missing_ok=True)


def finish(directory: Path, stage: str, status: int = 0) -> None:
    started = json.loads((directory / f"{stage}.start.json").read_text())
    seconds = (time.monotonic_ns() - started["monotonic_ns"]) / 1_000_000_000
    if seconds < 0:
        raise ValueError("measurement must finish on the same runner")
    (directory / f"{stage}.json").write_text(
        json.dumps({"seconds": seconds, "exit_code": status}) + "\n", encoding="utf-8"
    )


def measure(directory: Path, stage: str, command: list[str]) -> int:
    start(directory, stage)
    status = 127
    try:
        result = subprocess.run(command, check=False)
        status = (
            result.returncode if result.returncode >= 0 else 128 - result.returncode
        )
    except KeyboardInterrupt:
        status = 130
    finally:
        try:
            finish(directory, stage, status)
        except (OSError, ValueError, KeyError) as error:
            print(f"Measurement incomplete: {error}", file=sys.stderr)
    return status


def report(directory: Path, book: str, environ: dict[str, str]) -> dict:
    stages = {}
    for stage in STAGES:
        path = directory / f"{stage}.json"
        if path.is_file():
            stages[stage] = json.loads(path.read_text())
        elif (directory / f"{stage}.start.json").exists():
            stages[stage] = {"seconds": None, "exit_code": None}
    reused = environ.get("METRICS_REUSED", "") == "true"
    cache = environ.get("METRICS_CACHE_HIT", "")
    cache_state = {"true": "exact-hit", "false": "prefix-hit"}.get(cache, "miss")
    result = {
        "policy": POLICY,
        "book": book,
        "run_id": environ.get("GITHUB_RUN_ID", "local"),
        "run_attempt": environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "selected_books": int(environ.get("METRICS_BOOK_COUNT", "0")),
        "job_status": environ.get("METRICS_JOB_STATUS", "unknown"),
        "incremental_cache": "skipped" if reused else cache_state,
        "verified_reuse": reused,
        "reuse_reason": environ.get("METRICS_REUSE_REASON", "") or "not-requested",
        "stages": stages,
    }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        lines = [
            f"### Build measurements: {book}",
            "",
            f"Cache: `{result['incremental_cache']}`; PDF reuse: `{result['reuse_reason']}`.",
            "",
            "| Phase | Seconds | Exit status |",
            "| --- | ---: | ---: |",
        ]
        for stage, measurement in stages.items():
            duration = measurement["seconds"]
            rendered = "incomplete" if duration is None else f"{duration:.3f}"
            lines.append(f"| {stage} | {rendered} | {measurement['exit_code']} |")
        lines.extend(
            [
                "",
                "Job time starts after checkout; nested phases must not be summed.",
                "",
            ]
        )
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("\n".join(lines))
    return result


def assess(records: list[dict]) -> dict:
    if not records:
        raise ValueError("no measurements supplied")
    runs = {(record["run_id"], record["run_attempt"]) for record in records}
    if len(runs) != 1 or len({record["book"] for record in records}) != len(records):
        raise ValueError("use unique books from one run and attempt")
    selected = {record["selected_books"] for record in records}
    if len(selected) != 1 or selected != {len(records)}:
        raise ValueError("supply every selected book from that run")
    total = setup = 0.0
    for record in records:
        if (
            record["policy"] != POLICY
            or record["job_status"] != "success"
            or record["verified_reuse"]
        ):
            raise ValueError("only successful, freshly built jobs can be compared")
        for stage in ("job", "pre-build", "image", "compile", "log", "publication"):
            measurement = record["stages"].get(stage, {})
            seconds = measurement.get("seconds")
            if (
                not isinstance(seconds, (int, float))
                or not 0 <= seconds < float("inf")
                or measurement.get("exit_code") != 0
            ):
                raise ValueError(f"missing or unsuccessful phase: {stage}")
        job = record["stages"]["job"]["seconds"]
        overhead = sum(
            record["stages"][name]["seconds"] for name in ("pre-build", "image")
        )
        if job <= 0 or overhead > job:
            raise ValueError("invalid phase durations")
        total += job
        setup += overhead
    share = setup / total
    return {
        "books": len(records),
        "measured_runner_seconds": total,
        "setup_share": share,
        "recommend_grouping_experiment": len(records) >= 20 and share >= 0.30,
        "candidate_group_sizes": [2, 4],
        "adoption_requires": "measure >=20% runner-time saving and <=5% wall-time regression",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for mode in ("start", "finish", "run", "report"):
        command = subparsers.add_parser(mode)
        command.add_argument("--book", required=True)
        command.add_argument("--root", type=Path, default=ROOT)
        if mode != "report":
            command.add_argument("--stage", choices=STAGES, required=True)
        if mode == "run":
            command.add_argument("command", nargs=argparse.REMAINDER)
    comparison = subparsers.add_parser("assess")
    comparison.add_argument("records", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "assess":
            print(
                json.dumps(
                    assess([json.loads(path.read_text()) for path in args.records])
                )
            )
            return
        # Book identifiers are also directory names; do not accept arbitrary paths.
        if not re.fullmatch(validation_pattern("book_slug"), args.book):
            raise ValueError("invalid book slug")
        directory = args.root / "build/ci-metrics" / args.book
        if args.mode == "start":
            start(directory, args.stage)
        elif args.mode == "finish":
            finish(directory, args.stage)
        elif args.mode == "report":
            report(directory, args.book, dict(os.environ))
        else:
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                raise ValueError("a command is required")
            parser.exit(measure(directory, args.stage, command))
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
