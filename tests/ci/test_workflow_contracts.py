"""Source gates, workflow wiring, and inline shell syntax."""

from __future__ import annotations

import itertools
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.support.fixtures import git_environment
from tests.support.workflows import build_workflow

ROOT = Path(__file__).resolve().parents[2]


class WorkflowContractTests(unittest.TestCase):
    def test_filtered_source_history_keeps_ancestry_without_snapshot_blobs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            origin = root / "origin"
            origin.mkdir()
            environment = git_environment()

            def git(directory, *arguments):
                return subprocess.check_output(
                    ["git", *arguments], cwd=directory, env=environment, stderr=subprocess.PIPE, text=True
                )

            git(origin, "init", "-q")
            git(origin, "config", "uploadpack.allowFilter", "true")
            (origin / "README").write_text("source\n")
            git(origin, "add", ".")
            git(origin, "commit", "-qm", "source")
            previous = git(origin, "rev-parse", "HEAD").strip()
            (origin / "README").write_text("updated source\n")
            git(origin, "commit", "-qam", "updated source")
            git(origin, "switch", "--orphan", "generated-pdfs")
            (origin / "book.pdf").write_bytes(b"%PDF historical snapshot\n" * 10000)
            git(origin, "add", ".")
            git(origin, "commit", "-qm", "snapshot")
            blob = git(origin, "rev-parse", "HEAD:book.pdf").strip()
            git(origin, "switch", "main")
            checkout = root / "checkout"
            git(root, "clone", "--filter=blob:none", "--no-checkout", origin.as_uri(), str(checkout))
            git(checkout, "checkout", "main")
            git(checkout, "merge-base", "--is-ancestor", previous, "HEAD")
            missing = git(checkout, "rev-list", "--objects", "--missing=print", "--all")
            self.assertIn("?" + blob, missing.splitlines())
            self.assertEqual((checkout / "README").read_text(), "updated source\n")

    def test_external_actions_are_pinned_to_full_commit_shas(self):
        reference = re.compile(r"^[^/@]+/[^/@]+(?:/[^/@]+)*@[0-9a-f]{40}$")
        paths = sorted((ROOT / ".github/workflows").glob("*.yml"))
        paths += sorted((ROOT / ".github/actions").rglob("action.yml"))
        for path in paths:
            workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
            pending = [workflow]
            while pending:
                value = pending.pop()
                if isinstance(value, dict):
                    uses = value.get("uses")
                    if isinstance(uses, str) and not uses.startswith("./"):
                        self.assertRegex(uses, reference, f"{path}: {uses}")
                    pending.extend(value.values())
                elif isinstance(value, list):
                    pending.extend(value)

    def test_source_gate_rejects_unsuccessful_dependencies(self):
        job = build_workflow()["jobs"]["check"]
        self.assertEqual(job["if"], "always()")
        for source, latex, lean in itertools.product(("success", "failure", "cancelled", "skipped"), repeat=3):
            with self.subTest(source=source, latex=latex, lean=lean):
                result = subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", job["steps"][0]["run"]],
                    env={
                        **os.environ,
                        "SOURCE_RESULT": source,
                        "LATEX_RESULT": latex,
                        "IMAGE_RESULT": "skipped",
                        "LEAN_RESULT": lean,
                        "LEAN_REQUIRED": "true",
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(result.returncode == 0, source == latex == lean == "success")


if __name__ == "__main__":
    unittest.main()
