"""Source gates, workflow wiring, and inline shell syntax."""

from __future__ import annotations

import itertools
import os
import re
import subprocess
import unittest
from pathlib import Path

import yaml
from workflow_support import build_workflow

ROOT = Path(__file__).resolve().parent.parent


class WorkflowContractTests(unittest.TestCase):
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
        for source, latex in itertools.product(
            ("success", "failure", "cancelled", "skipped"), repeat=2
        ):
            with self.subTest(source=source, latex=latex):
                result = subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", job["steps"][0]["run"]],
                    env={
                        **os.environ,
                        "SOURCE_RESULT": source,
                        "LATEX_RESULT": latex,
                        "IMAGE_RESULT": "skipped",
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(result.returncode == 0, source == latex == "success")


if __name__ == "__main__":
    unittest.main()
