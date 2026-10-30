"""Contracts tying publication to reviewed main builds and retained packages."""

import itertools
import unittest
from pathlib import Path

import yaml

from tests.support.workflows import condition_allows

ROOT = Path(__file__).resolve().parents[2]


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_condition_accepts_only_reviewed_main_pushes(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/build.yml").read_text())
        condition = workflow["jobs"]["release"]["if"]
        results = ("success", "failure", "cancelled", "skipped")
        for event, branch, count, source, books in itertools.product(
            ("push", "pull_request", "workflow_dispatch"),
            ("refs/heads/main", "refs/heads/local-work"),
            ("0", "1", "2"),
            results,
            results,
        ):
            with self.subTest(event=event, branch=branch, count=count, source=source, books=books):
                context = {
                    "github.event_name": event,
                    "github.ref": branch,
                    "needs.plan.outputs.release_count": count,
                    "needs.check.result": source,
                    "needs.build-check.result": books,
                }
                expected = (
                    event == "push" and branch == "refs/heads/main" and count != "0" and source == books == "success"
                )
                self.assertEqual(condition_allows(condition, context), expected)

    def test_main_runs_preserve_each_version_and_snapshot_writes_are_serial(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/build.yml").read_text())
        self.assertIn("github.sha", workflow["concurrency"]["group"])
        self.assertIn("pull_request", workflow["concurrency"]["cancel-in-progress"])
        self.assertEqual(
            workflow["jobs"]["publish"]["concurrency"]["group"],
            "development-pdf-snapshot",
        )
        release = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
        self.assertEqual(
            release["jobs"]["release"]["concurrency"]["group"],
            "textbook-release-${{ matrix.book }}",
        )
        self.assertEqual(release["jobs"]["release"]["concurrency"]["queue"], "max")


if __name__ == "__main__":
    unittest.main()
