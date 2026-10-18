"""Task checks must work without unrelated container dependencies."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "local_environment", ROOT / "scripts/check_local_environment.py"
)
assert SPEC and SPEC.loader
LOCAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOCAL)


class LocalEnvironmentTests(unittest.TestCase):
    def run_pdf(self, missing=None):
        tools = []

        def locate(name):
            tools.append(name)
            return None if name == missing else f"/tools/{name}"

        with (
            patch.object(sys, "argv", ["doctor", "pdf"]),
            patch.object(LOCAL.platform, "system", return_value="Linux"),
            patch.object(LOCAL.sys, "version_info", (3, 14)),
            patch.object(LOCAL.shutil, "which", side_effect=locate),
            patch.object(LOCAL.importlib.metadata, "version", return_value="6.0.3"),
            patch.object(
                LOCAL.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
            ),
        ):
            status = LOCAL.main()
        return status, tools

    def test_pdf_does_not_require_lean_site_or_debian_package_tools(self):
        status, tools = self.run_pdf()
        self.assertEqual(status, 0)
        for name in ("lean", "jekyll", "chromium", "dpkg-query", "ruff"):
            self.assertNotIn(name, tools)

    def test_missing_pdf_tool_fails(self):
        status, _ = self.run_pdf("latexmk")
        self.assertEqual(status, 1)


if __name__ == "__main__":
    unittest.main()
