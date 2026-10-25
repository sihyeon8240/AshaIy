"""Inspect plans against real independent source and snapshot Git histories."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support.fixtures import (
    book_record,
    git_environment,
    manifest_document,
    write_yaml,
)

ROOT = Path(__file__).resolve().parents[2]


class ImpactPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.environment = {**git_environment(), "PYTHONDONTWRITEBYTECODE": "1"}
        shutil.copytree(
            ROOT / "scripts",
            self.root / "scripts",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        shutil.copytree(ROOT / "config", self.root / "config")
        write_yaml(
            self.root / "config/books.yml",
            manifest_document(
                [
                    book_record("alpha", label_prefix="alpha"),
                    book_record("beta", label_prefix="beta"),
                    book_record(
                        "disabled", label_prefix="disabled", build=False, check=False
                    ),
                ]
            ),
        )
        for slug in ("alpha", "beta", "disabled"):
            source = self.root / "books" / slug / "book.tex"
            source.parent.mkdir(parents=True)
            source.write_text("Original body.\n")
        self.git("init", "-q")
        self.snapshot = self.commit("baseline")

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.root,
            env=self.environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.strip()

    def commit(self, message: str) -> str:
        self.git("add", ".")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def command(self, script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / script), *arguments],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def plan(self, *arguments: str) -> dict:
        result = self.command("cli/repository_cli.py", "plan", *arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_source_and_snapshot_bases_remain_independent(self) -> None:
        (self.root / "books/alpha/book.tex").write_text("Changed body.\n")
        source_base = self.commit("unpublished book change")
        (self.root / "README.md").write_text("Documentation only.\n")
        head = self.commit("documentation")
        result = self.plan("--source-base", source_base, "--pdf-base", self.snapshot)
        self.assertEqual(result["head"], head)
        self.assertFalse(result["working_tree_dirty"])
        self.assertEqual(result["source"]["comparison"]["base"], source_base)
        self.assertEqual(result["pdf"]["comparison"]["base"], self.snapshot)
        self.assertFalse(result["source"]["consumers"]["lean"]["selected"])
        self.assertEqual(result["pdf"]["book"], ["alpha"])
        reasons = result["pdf"]["reasons"]["alpha"]
        self.assertIn("books/alpha/book.tex", reasons[0]["paths"])
        self.assertEqual(result["pdf"]["reasons"]["beta"], [])

        legacy = self.command("ci/affected_books.py", "--base", self.snapshot)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        old = json.loads(legacy.stdout)
        self.assertEqual({key: result["pdf"][key] for key in old}, old)
        scope = self.command(
            "ci/ci_check_scope.py", "--base", source_base, "--format", "github"
        )
        self.assertEqual(scope.returncode, 0, scope.stderr)
        for line in scope.stdout.splitlines():
            name, value = line.split("=")
            self.assertEqual(
                result["source"]["consumers"][name]["selected"], value == "true"
            )

    def test_missing_comparisons_select_all_consumers_and_enabled_books(self) -> None:
        result = self.plan("--source-base", "missing", "--pdf-base", "0" * 40)
        for section in ("source", "pdf"):
            self.assertFalse(result[section]["comparison"]["available"])
            self.assertIsNone(result[section]["comparison"]["paths"])
        self.assertTrue(
            all(
                selection["selected"]
                for selection in result["source"]["consumers"].values()
            )
        )
        self.assertEqual(result["pdf"]["book"], ["alpha", "beta"])
        self.assertIn(
            "comparison unavailable", result["pdf"]["reasons"]["alpha"][0]["reason"]
        )

    def test_unknown_path_explains_conservative_full_build(self) -> None:
        (self.root / "unregistered.cfg").write_text("new input\n")
        self.commit("unknown input")
        result = self.plan("--source-base", self.snapshot, "--pdf-base", self.snapshot)
        self.assertEqual(result["pdf"]["book"], ["alpha", "beta"])
        self.assertEqual(
            result["pdf"]["reasons"]["beta"][0]["paths"], ["unregistered.cfg"]
        )
        self.assertIn(
            "unknown build inputs", result["pdf"]["reasons"]["beta"][0]["reason"]
        )

    def test_unavailable_base_does_not_replace_other_valid_comparison(self) -> None:
        result = self.plan("--pdf-base", "HEAD")
        self.assertTrue(result["source"]["consumers"]["lean"]["selected"])
        self.assertEqual(result["pdf"]["book"], [])
        self.assertTrue(result["pdf"]["comparison"]["available"])

        result = self.plan("--source-base", "HEAD")
        self.assertFalse(result["source"]["consumers"]["lean"]["selected"])
        self.assertEqual(result["pdf"]["book"], ["alpha", "beta"])
        self.assertTrue(result["source"]["comparison"]["available"])

    def test_release_request_forces_build_even_with_empty_diff(self) -> None:
        result = self.plan(
            "--source-base", "HEAD", "--pdf-base", "HEAD", "--release-book", "beta"
        )
        self.assertEqual(result["pdf"]["comparison"]["paths"], [])
        self.assertEqual(result["pdf"]["book"], ["beta"])
        self.assertEqual(result["release"]["requested_books"], ["beta"])
        self.assertEqual(
            result["pdf"]["reasons"]["beta"][0]["reason"],
            "requested release requires a build",
        )
        for slug in ("absent", "disabled"):
            with self.subTest(slug=slug):
                rejected = self.command(
                    "cli/repository_cli.py", "plan", "--release-book", slug
                )
                self.assertEqual(rejected.returncode, 2)
                self.assertEqual(rejected.stdout, "")
                self.assertIn(
                    "release matrix contains a book not enabled for building",
                    rejected.stderr,
                )

    def test_dirty_sources_are_reported_without_becoming_committed_changes(
        self,
    ) -> None:
        (self.root / "books/alpha/book.tex").write_text("Uncommitted body.\n")
        before = self.git("status", "--porcelain")
        result = self.plan("--source-base", "HEAD", "--pdf-base", "HEAD")
        self.assertTrue(result["working_tree_dirty"])
        self.assertEqual(result["pdf"]["book"], [])
        self.assertEqual(before, self.git("status", "--porcelain"))

    def test_ci_outputs_match_explained_plans_for_conservative_and_empty_diffs(self):
        (self.root / "unregistered.cfg").write_text("unknown input\n")
        self.commit("unregistered input")
        for base in (self.snapshot, "HEAD", "missing", "0" * 40):
            with self.subTest(base=base):
                result = self.plan("--source-base", base, "--pdf-base", base)
                source = self.command(
                    "ci/ci_check_scope.py", "--base", base, "--format", "github"
                )
                self.assertEqual(source.returncode, 0, source.stderr)
                actual = dict(line.split("=", 1) for line in source.stdout.splitlines())
                expected = {
                    name: str(selection["selected"]).lower()
                    for name, selection in result["source"]["consumers"].items()
                }
                self.assertEqual(actual, expected)

                pdf = self.command(
                    "ci/affected_books.py", "--base", base, "--format", "github"
                )
                self.assertEqual(pdf.returncode, 0, pdf.stderr)
                fields = dict(line.split("=", 1) for line in pdf.stdout.splitlines())
                self.assertEqual(
                    json.loads(fields.pop("matrix")), {"book": result["pdf"]["book"]}
                )
                self.assertEqual(
                    fields,
                    {
                        "count": str(result["pdf"]["count"]),
                        "site_changed": str(result["pdf"]["site_changed"]).lower(),
                        "snapshot_changed": str(
                            result["pdf"]["snapshot_changed"]
                        ).lower(),
                    },
                )

    def test_source_adapter_runs_before_third_party_dependencies_are_installed(self):
        result = subprocess.run(
            [
                sys.executable,
                "-S",
                "scripts/ci/ci_check_scope.py",
                "--base",
                "HEAD",
                "--format",
                "github",
            ],
            cwd=self.root,
            env=self.environment,
            text=True,
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        selections = dict(line.split("=", 1) for line in result.stdout.splitlines())
        self.assertEqual(
            set(selections),
            {"lean", "image_changed", "structured", "site_changed", "snapshot_changed"},
        )
        self.assertEqual(set(selections.values()), {"false"})


if __name__ == "__main__":
    unittest.main()
