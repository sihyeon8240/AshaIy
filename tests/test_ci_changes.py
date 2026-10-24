"""One conservative path classification contract for CI consumers."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts import ci_changes as CI

ROOT = Path(__file__).resolve().parent.parent


class CiChangeTests(unittest.TestCase):
    def test_missing_comparison_selects_every_consumer(self):
        self.assertIsNone(CI.changed_paths(""))
        self.assertTrue(all(CI.classify(None).values()))

    def test_every_canonical_image_input_selects_image_validation(self):
        for path in CI.image_inputs():
            with self.subTest(path=path):
                self.assertTrue(CI.classify([path])["image_changed"])

    def test_runtime_image_policy_and_loader_select_image_validation(self):
        for path in (
            "scripts/image_policy.py",
            "scripts/repository_config.py",
            "config/validation-patterns.json",
            "scripts/validation_patterns.py",
            "scripts/validation_sync.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(CI.classify([path])["image_changed"])

    def test_documentation_does_not_select_build_or_structured_consumers(self):
        self.assertFalse(any(CI.classify(["docs/maintainer-guide.md"]).values()))

    def test_site_snapshot_and_workflow_changes_are_distinct(self):
        self.assertTrue(CI.classify(["site/index.html"])["site_changed"])
        self.assertTrue(
            CI.classify(["scripts/publish_snapshot.sh"])["snapshot_changed"]
        )
        result = CI.classify([".github/workflows/release-retry.yml"])
        self.assertTrue(result["structured"])
        self.assertFalse(result["site_changed"])
