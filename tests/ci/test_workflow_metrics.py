"""Workflow resource totals distinguish overlapping jobs from elapsed time."""

from __future__ import annotations

import unittest

from scripts.ci.workflow_metrics import summarize


class WorkflowMetricsTests(unittest.TestCase):
    def test_overlapping_jobs_and_incomplete_attempts_are_reported_separately(self):
        run = {
            "id": 1,
            "run_attempt": 2,
            "event": "pull_request",
            "head_sha": "a" * 40,
            "created_at": "2026-11-12T00:00:00Z",
            "conclusion": "failure",
        }
        jobs = [
            {"name": "first", "started_at": "2026-11-12T00:00:10Z", "completed_at": "2026-11-12T00:00:40Z"},
            {"name": "second", "started_at": "2026-11-12T00:00:20Z", "completed_at": "2026-11-12T00:00:50Z"},
            {"name": "interrupted", "started_at": "2026-11-12T00:00:30Z"},
        ]
        result = summarize(run, jobs, [{"name": "pdf", "size_in_bytes": 123}])
        self.assertEqual(result["runner_seconds"], 60)
        self.assertEqual(result["observed_wall_seconds"], 50)
        self.assertEqual(result["incomplete_jobs"], 1)
        self.assertEqual(result["artifact_bytes"], 123)
