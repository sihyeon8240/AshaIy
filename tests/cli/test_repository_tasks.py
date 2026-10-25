"""Stage failures and source-snapshot lifetimes across integrated operations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from scripts.books import contents_generation as contents
from scripts.cli import repository_tasks as tasks
from scripts.cli import task_stages as stages
from scripts.lean import lean_generation as lean
from scripts.repository.source_reads import read_yaml
from scripts.site import site_pages as site


class RepositoryTaskTests(unittest.TestCase):
    def test_failure_preserves_status_and_prevents_following_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "unexpected"
            result = stages.run_stages(
                (
                    stages.Stage("prepare", lambda: 0),
                    stages.Stage("failed-check", lambda: 7),
                    stages.Stage("publish", lambda: output.write_text("must not run")),
                )
            )
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.completed, ("prepare",))
            self.assertEqual(result.failed, "failed-check")
            self.assertFalse(output.exists())

    def test_generation_observes_writes_and_later_checks_observe_edits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "manifest.yml"
            observed = []

            def lean_stage(**options):
                observed.append(cast(dict[str, str], read_yaml(source))["value"])
                if not options["check"]:
                    source.write_text("value: updated\n")
                return 0

            def contents_stage(scope, **options):
                observed.append(cast(dict[str, str], read_yaml(source))["value"])
                return 0

            with (
                patch.object(lean, "generate", side_effect=lean_stage),
                patch.object(contents, "generate", side_effect=contents_stage),
                patch.object(site, "generate", return_value=0),
            ):
                source.write_text("value: original\n")
                self.assertEqual(tasks.generate().returncode, 0)
                self.assertEqual(observed, ["original", "updated"])
                observed.clear()
                self.assertEqual(tasks.generate(check=True).returncode, 0)
                self.assertEqual(observed, ["updated", "updated"])
                source.write_text("value: later\n")
                observed.clear()
                self.assertEqual(tasks.generate(check=True).returncode, 0)
                self.assertEqual(observed, ["later", "later"])

    def test_failed_generation_does_not_run_site_or_reuse_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"

            def write_site(**options):
                output.write_text("generated")
                return 0

            with (
                patch.object(lean, "generate", return_value=0),
                patch.object(contents, "generate", side_effect=[1, 0]),
                patch.object(site, "generate", side_effect=write_site),
            ):
                failed = tasks.generate(check=True)
                self.assertEqual(failed.failed, "contents")
                self.assertFalse(output.exists())
                self.assertEqual(tasks.generate(check=True).returncode, 0)
                self.assertEqual(output.read_text(), "generated")
