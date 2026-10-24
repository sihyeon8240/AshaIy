"""Editor diagnostics and Python selection must match checkout commands."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class EditorCommandTests(unittest.TestCase):
    def test_task_uses_selected_interpreter_and_preserves_argument_boundaries(self):
        task = next(
            item
            for item in json.loads((ROOT / ".vscode/tasks.json").read_text())["tasks"]
            if item["label"] == "ashaiy test"
        )
        with tempfile.TemporaryDirectory(prefix="selected python ") as temporary:
            python = Path(temporary) / "python"
            python.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
            python.chmod(0o755)
            command = task["command"].replace(
                "${command:python.interpreterPath}", str(python)
            )
            arguments = [
                value.replace("${workspaceFolder}", str(ROOT)) for value in task["args"]
            ]
            result = subprocess.run(
                [command, *arguments], capture_output=True, text=True, check=True
            )
        self.assertEqual(
            result.stdout.splitlines(), [str(ROOT / "scripts/ashaiy"), "test"]
        )

    def test_located_diagnostics_never_include_line_numbers_in_file_names(self):
        matchers = json.loads((ROOT / ".vscode/tasks.json").read_text())[
            "problemMatcher"
        ]
        for line, expected in (
            (
                "books/sample/section.tex:12: warning: legacy label",
                ("books/sample/section.tex", "12"),
            ),
            (
                "build/sample/book.log: error: unresolved reference",
                ("build/sample/book.log", None),
            ),
        ):
            locations = []
            for matcher in matchers:
                pattern = matcher["pattern"]
                match = re.search(pattern["regexp"], line)
                if match:
                    locations.append(
                        (
                            match[pattern["file"]],
                            match[pattern["line"]] if "line" in pattern else None,
                        )
                    )
            self.assertEqual(locations, [expected])

    def test_workshop_uses_local_python_without_terminal_activation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            shutil.copy2(ROOT / "scripts/run_python.sh", root / "scripts")
            python = root / ".cache/local-venv/bin/python"
            python.parent.mkdir(parents=True)
            python.write_text("#!/bin/sh\nprintf '%s\\n' selected \"$@\"\n")
            python.chmod(0o755)
            environment = {
                key: value
                for key, value in os.environ.items()
                if key not in {"PYTHON", "VIRTUAL_ENV"}
            }
            result = subprocess.run(
                ["bash", str(root / "scripts/run_python.sh"), "script with spaces.py"],
                env=environment,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(
                result.stdout.splitlines(), ["selected", "script with spaces.py"]
            )
