"""Collect read-only workflow timing, artifact size, and cache usage evidence."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.github_artifacts import api, collection


def seconds(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    first = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
    last = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
    duration = (last - first).total_seconds()
    if duration < 0:
        raise ValueError("workflow timestamps are out of order")
    return duration


def summarize(run: dict, jobs: list[dict], artifacts: list[dict]) -> dict:
    records = [
        {
            "name": job["name"],
            "conclusion": job.get("conclusion"),
            "runner_seconds": seconds(job.get("started_at"), job.get("completed_at")),
            "start_delay_seconds": seconds(run.get("created_at"), job.get("started_at")),
        }
        for job in jobs
    ]
    completed = [job["completed_at"] for job in jobs if job.get("completed_at")]
    return {
        "run_id": run["id"],
        "attempt": run["run_attempt"],
        "event": run["event"],
        "revision": run["head_sha"],
        "conclusion": run.get("conclusion"),
        "observed_wall_seconds": seconds(run.get("created_at"), max(completed) if completed else None),
        "runner_seconds": sum(item["runner_seconds"] or 0 for item in records),
        "incomplete_jobs": sum(item["runner_seconds"] is None for item in records),
        "artifact_bytes": sum(item["size_in_bytes"] for item in artifacts),
        "artifacts": [{"name": item["name"], "bytes": item["size_in_bytes"]} for item in artifacts],
        "jobs": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--run-id", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=Path("build/ci-metrics/workflows.json"))
    arguments = parser.parse_args()
    if not arguments.repository or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", arguments.repository):
        parser.error("--repository must be owner/name")
    if min(arguments.run_id) < 1:
        parser.error("run IDs must be positive")
    records = []
    try:
        for identifier in arguments.run_id:
            endpoint = f"repos/{arguments.repository}/actions/runs/{identifier}"
            run = api(endpoint)
            jobs = collection(f"{endpoint}/attempts/{run['run_attempt']}/jobs", "jobs")
            artifacts = collection(f"{endpoint}/artifacts", "artifacts")
            records.append(summarize(run, jobs, artifacts))
        try:
            cache = api(f"repos/{arguments.repository}/actions/cache/usage")
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            cache = {"unavailable": str(error)}
        result = {
            "schema_version": 1,
            "repository": arguments.repository,
            "notes": [
                "Runner seconds are observed job durations, not billed minutes.",
                "Start delay includes dependency waiting and provisioning, not queueing alone.",
                "Artifact bytes are stored archive sizes; cache usage is a repository-wide snapshot.",
                "Use repeated runs per change category before changing grouping or retention.",
            ],
            "runs": records,
            "cache_usage": cache,
        }
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(result, indent=2) + "\n")
        print(f"Saved workflow measurements: {arguments.output}")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
