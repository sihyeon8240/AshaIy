"""Stage failures and source-snapshot lifetimes across integrated operations."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from scripts.books import contents_generation as contents
from scripts.cli import repository_tasks as tasks
from scripts.cli import task_stages as stages
from scripts.lean import lean_generation as lean
from scripts.repository.file_updates import write_updates
from scripts.repository.source_reads import read_yaml
from scripts.site import site_pages as site
from tests.support.fixtures import write_executable


class RepositoryTaskTests(unittest.TestCase):
    def check_fixture(self, root: Path, *, failure: int = 0, rendezvous: bool = False) -> None:
        for relative in (
            "repository/checks/check_repository.sh",
            "repository/formatting/format_code.py",
            "latex/format_tex.py",
            "repository/formatting/normalize_eof.py",
            "lean/check_lean.sh",
            "latex/build_all.py",
        ):
            code = "from pathlib import Path\nimport os, sys, time\n"
            if relative.endswith("check_repository.sh"):
                code += "Path('source-started').touch()\n"
                if rendezvous:
                    code += (
                        "deadline = time.monotonic() + 5\n"
                        "while not Path('lean-started').exists():\n"
                        "    assert time.monotonic() < deadline, 'Lean did not overlap source checks'\n"
                        "    time.sleep(0.01)\n"
                    )
                code += f"sys.exit({failure})\n"
            elif relative.endswith("check_lean.sh"):
                code += "Path('lean-started').touch()\nPath('lean-finished').touch()\n"
            elif relative.endswith("build_all.py"):
                code += (
                    "assert Path('lean-finished').exists()\n"
                    "assert os.environ['CHECK_LOG_STRICT'] == '1'\n"
                    "Path('books-built').touch()\n"
                )
            write_executable(root / "scripts" / relative, f"#!{sys.executable}\n" + code)

    def test_full_checks_overlap_sources_and_lean_before_building_books(self) -> None:
        with tempfile.TemporaryDirectory(prefix="parallel checks ") as temporary:
            root = Path(temporary)
            self.check_fixture(root, rendezvous=True)
            with contextlib.redirect_stdout(io.StringIO()):
                result = tasks.check_all(strict=True, jobs=2, root=root)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.completed[-2:], ("lean", "books"))
            self.assertTrue((root / "books-built").exists())

    def test_failed_full_checks_preserve_status_and_never_reuse_success(self) -> None:
        for jobs in (1, 2):
            with self.subTest(jobs=jobs), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.check_fixture(root, failure=7)
                with contextlib.redirect_stdout(io.StringIO()):
                    result = tasks.check_all(strict=True, jobs=jobs, root=root)
                    self.assertEqual(result.failed, "repository-sources")
                    self.assertEqual(result.returncode, 7)
                    self.assertFalse((root / "books-built").exists())
                    self.check_fixture(root)
                    self.assertEqual(tasks.check_all(strict=True, jobs=jobs, root=root).returncode, 0)
                self.assertTrue((root / "books-built").exists())

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
                    write_updates({source: "value: updated\n"})
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
