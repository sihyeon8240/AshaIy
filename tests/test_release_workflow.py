"""Contracts tying publication to reviewed main builds and retained packages."""

import itertools
import unittest
from pathlib import Path

import yaml
from workflow_support import condition_allows

ROOT = Path(__file__).resolve().parent.parent


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
            with self.subTest(
                event=event, branch=branch, count=count, source=source, books=books
            ):
                context = {
                    "github.event_name": event,
                    "github.ref": branch,
                    "needs.plan.outputs.release_count": count,
                    "needs.check.result": source,
                    "needs.build-check.result": books,
                }
                expected = (
                    event == "push"
                    and branch == "refs/heads/main"
                    and count != "0"
                    and source == books == "success"
                )
                self.assertEqual(condition_allows(condition, context), expected)

    def test_plan_checks_remote_tags_only_for_pull_requests_and_writes_summary(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/build.yml").read_text())
        step = next(
            step
            for step in workflow["jobs"]["plan"]["steps"]
            if step.get("id") == "releases"
        )
        self.assertIn('--summary "$GITHUB_STEP_SUMMARY"', step["run"])
        self.assertIn(
            'if [[ "$GITHUB_EVENT_NAME" == pull_request ]]; then\n'
            "    options+=(--check-remote-tags)",
            step["run"],
        )

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
