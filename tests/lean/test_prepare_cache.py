"""Dependency cache preparation preserves sources and unrelated cached artifacts."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.lean import prepare_cache as CACHE


def elf_header(machine: int) -> bytes:
    header = bytearray(20)
    header[:6] = b"\x7fELF\x02\x01"
    header[18:20] = machine.to_bytes(2, "little")
    return bytes(header)


class PrepareCacheTests(unittest.TestCase):
    def test_cache_fingerprint_follows_reachable_imports_without_tracking_proof_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "lean/Textbooks").mkdir(parents=True)
            (root / "lean/Textbooks.lean").write_text("import Textbooks.Topic\n")
            source = root / "lean/Textbooks/Topic.lean"
            source.write_text("import Mathlib.One\n/- import Mathlib.Unused -/\ndef value := 1\n")
            original = CACHE.import_fingerprint(root)
            source.write_text("import Mathlib.One\nimport Mathlib.One\ndef value := 2\n")
            (root / "lean/Textbooks/Unreachable.lean").write_text("import Mathlib.Other\n")
            self.assertEqual(CACHE.import_fingerprint(root), original)
            source.write_text("import Mathlib.One\nimport Mathlib.Two\n")
            self.assertNotEqual(CACHE.import_fingerprint(root), original)

    def test_prepares_only_import_closure_and_repairs_restored_native_tool(self):
        for stale_trace in (False, True):
            with self.subTest(stale_trace=stale_trace), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                sources = {
                    "lean/Textbooks.lean": "public import Textbooks.Book.A\n",
                    "lean/Textbooks/Book/A.lean": (
                        "import Textbooks.Book.B\nimport Mathlib.Algebra.Basic\n/- import Mathlib.DoNotDownload -/\n"
                    ),
                    "lean/Textbooks/Book/B.lean": "import Textbooks.Book.A\nimport Mathlib.Tactic\n",
                    "lean/Textbooks/Unused.lean": "import Mathlib.Unreachable\n",
                    "lean/lake-manifest.json": '{"pinned": true}\n',
                    ".cache/mathlib/preserve.ltar": "downloaded cache",
                }
                for relative, content in sources.items():
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
                binary = root / "lean/.lake/packages/batteries/.lake/build/bin/runLinter"
                trace = binary.with_name(binary.name + ".trace")
                calls = []
                builds = 0

                def execute(command, **options):
                    nonlocal builds
                    calls.append(command)
                    self.assertEqual(options["cwd"], root / "lean")
                    if command[:4] == ["lake", "exe", "cache", "get"]:
                        self.assertEqual(command[4:], ["Mathlib.Algebra.Basic", "Mathlib.Tactic"])
                        self.assertEqual(options["env"]["MATHLIB_NO_CACHE_ON_UPDATE"], "1")
                        binary.parent.mkdir(parents=True)
                        binary.write_bytes(elf_header(62))
                        trace.write_text("restored trace")
                    else:
                        self.assertEqual(command, ["lake", "--no-cache", "build", "@batteries/runLinter"])
                        builds += 1
                        if not stale_trace or builds == 2:
                            if stale_trace:
                                self.assertFalse(binary.exists())
                                self.assertFalse(trace.exists())
                            binary.write_bytes(elf_header(183))
                    return subprocess.CompletedProcess(command, 0)

                with (
                    patch.object(CACHE, "host_architecture", return_value="arm64"),
                    patch.object(CACHE.subprocess, "run", side_effect=execute),
                ):
                    CACHE.prepare(root)
                self.assertEqual(len(calls), 3 if stale_trace else 2)
                self.assertEqual(binary.read_bytes(), elf_header(183))
                for relative, content in sources.items():
                    self.assertEqual((root / relative).read_text(), content)

    def test_unknown_or_external_native_tools_are_preserved(self):
        for symlink in (False, True):
            with self.subTest(symlink=symlink), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                relative = "packages/batteries/.lake/build/bin/runLinter" if symlink else "build/bin/custom"
                binary = root / "lean/.lake" / relative
                binary.parent.mkdir(parents=True)
                external = root / "external"
                external.write_bytes(elf_header(62))
                if symlink:
                    binary.symlink_to(external)
                else:
                    binary.write_bytes(elf_header(62))
                with (
                    patch.object(CACHE, "host_architecture", return_value="arm64"),
                    patch.object(CACHE.subprocess, "run") as execute,
                    self.assertRaisesRegex(ValueError, "preserved"),
                ):
                    CACHE.repair_native_executables(root)
                execute.assert_not_called()
                self.assertEqual(binary.read_bytes(), elf_header(62))
                self.assertEqual(external.read_bytes(), elf_header(62))


if __name__ == "__main__":
    unittest.main()
