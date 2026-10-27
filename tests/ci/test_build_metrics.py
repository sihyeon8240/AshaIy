"""Check measurement failure semantics and evidence required for CI grouping."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ci import build_metrics as METRICS


class BuildMetricsTests(unittest.TestCase):
    def test_command_failure_and_measurement_failure_preserve_exit_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            command = [sys.executable, "-c", "raise SystemExit(17)"]
            self.assertEqual(METRICS.measure(directory, "compile", command), 17)
            measured = json.loads((directory / "compile.json").read_text())
            self.assertEqual(measured["exit_code"], 17)
            self.assertGreaterEqual(measured["seconds"], 0)
            with patch.object(METRICS, "finish", side_effect=OSError("disk full")):
                self.assertEqual(METRICS.measure(directory, "compile", command), 17)

    def test_incomplete_or_failed_phases_remain_visible_in_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            METRICS.start(directory, "job")
            METRICS.start(directory, "image")
            METRICS.start(directory, "compile")
            METRICS.finish(directory, "compile", 17)
            summary = directory / "summary.md"
            result = METRICS.report(
                directory,
                "sample",
                {"GITHUB_STEP_SUMMARY": str(summary), "METRICS_JOB_STATUS": "failure"},
            )
            self.assertIsNone(result["stages"]["image"]["seconds"])
            self.assertEqual(result["stages"]["compile"]["exit_code"], 17)
            self.assertEqual(
                json.loads((directory / "result.json").read_text()), result
            )
            self.assertIn("incomplete", summary.read_text())

    def records(self, count=20, overhead=35):
        return [
            {
                "policy": METRICS.POLICY,
                "book": f"book-{index}",
                "run_id": "123",
                "run_attempt": "1",
                "selected_books": count,
                "job_status": "success",
                "verified_reuse": False,
                "stages": {
                    name: {"seconds": seconds, "exit_code": 0}
                    for name, seconds in (
                        ("job", 100),
                        ("pre-build", 10),
                        ("image", overhead - 10),
                        ("compile", 50),
                        ("log", 1),
                        ("publication", 5),
                    )
                },
            }
            for index in range(count)
        ]

    def test_grouping_requires_both_scale_and_measured_setup_cost(self):
        for count, overhead, recommended in (
            (3, 35, False),
            (20, 29, False),
            (20, 35, True),
        ):
            with self.subTest(count=count, overhead=overhead):
                result = METRICS.assess(self.records(count, overhead))
                self.assertEqual(result["recommend_grouping_experiment"], recommended)
                self.assertAlmostEqual(result["setup_share"], overhead / 100)

    def test_comparison_rejects_partial_mixed_failed_or_reused_jobs(self):
        baseline = self.records()
        mutations = [
            ("run_id", "other"),
            ("run_attempt", "2"),
            ("selected_books", 21),
            ("job_status", "failure"),
            ("verified_reuse", True),
            ("policy", "old"),
            ("book", baseline[1]["book"]),
        ]
        for key, value in mutations:
            with self.subTest(key=key), self.assertRaises(ValueError):
                records = copy.deepcopy(baseline)
                records[0][key] = value
                METRICS.assess(records)
        for phase in (
            None,
            {"seconds": None, "exit_code": None},
            {"seconds": 1, "exit_code": 17},
        ):
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                records = copy.deepcopy(baseline)
                if phase is None:
                    del records[0]["stages"]["image"]
                else:
                    records[0]["stages"]["image"] = phase
                METRICS.assess(records)
        with self.assertRaises(ValueError):
            METRICS.assess(baseline[:-1])


if __name__ == "__main__":
    unittest.main()
