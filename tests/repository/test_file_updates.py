"""Source replacement, interruption recovery, and cooperating writer isolation."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.repository import file_updates as updates
from tests.support.fixtures import stop_process_group

ROOT = Path(__file__).resolve().parents[2]


class FileUpdateTests(unittest.TestCase):
    def test_failure_restores_existing_files_and_removes_new_files(self) -> None:
        for failure in (OSError, KeyboardInterrupt):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                first, created, last = (
                    root / name for name in ("first", "new", "last")
                )
                first.write_bytes(b"old-first")
                first.chmod(0o640)
                last.write_bytes(b"old-last")
                replace = os.replace

                def interrupted(source, destination):
                    if destination == last:
                        raise failure("interrupted install")
                    return replace(source, destination)

                with (
                    self.assertRaises(failure),
                    updates.source_updates(root),
                    patch.object(updates.os, "replace", interrupted),
                ):
                    updates.write_updates(
                        {first: "new-first", created: "created", last: "new-last"}
                    )
                self.assertEqual(first.read_bytes(), b"old-first")
                self.assertEqual(first.stat().st_mode & 0o777, 0o640)
                self.assertEqual(last.read_bytes(), b"old-last")
                self.assertFalse(created.exists())

    def test_failed_recovery_retains_original_bytes_and_reports_location(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, last = root / "first", root / "last"
            first.write_text("old-first")
            last.write_text("old-last")
            replace = os.replace

            def broken(source, destination):
                if destination == last or Path(source).read_bytes() == b"old-first":
                    raise OSError("replacement unavailable")
                return replace(source, destination)

            with (
                self.assertRaisesRegex(OSError, "originals retained"),
                updates.source_updates(root),
                patch.object(updates.os, "replace", broken),
            ):
                updates.write_updates({first: "new-first", last: "new-last"})
            recovery = next((root / "build/recovery").iterdir())
            records = json.loads((recovery / "files.json").read_text())
            self.assertEqual(records[0]["path"], str(first))
            self.assertEqual(
                (recovery / records[0]["backup"]).read_bytes(), b"old-first"
            )
            self.assertEqual(last.read_text(), "old-last")

    def test_edits_after_planning_prevent_all_installation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / "input", root / "output"
            source.write_bytes(b"original\r\n")
            target.write_text("existing")
            with updates.source_updates(root):
                self.assertEqual(updates.read_source(source), "original\n")
                source.write_text("editor change")
                with self.assertRaisesRegex(ValueError, "source changed"):
                    updates.write_updates({target: "generated"})
            self.assertEqual(target.read_text(), "existing")
            self.assertEqual(source.read_text(), "editor change")

    def test_replacement_preserves_symlink_and_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target, link = root / "target", root / "link"
            target.write_text("original")
            target.chmod(0o640)
            link.symlink_to(target.name)
            with updates.source_updates(root):
                updates.write_updates({link: "replacement"}, durable=True)
            self.assertTrue(link.is_symlink())
            self.assertEqual(target.read_text(), "replacement")
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)

    def test_process_interruption_leaves_complete_file_and_releases_lock(self) -> None:
        program = """
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
from scripts.repository.file_updates import source_updates, write_updates

root = Path(sys.argv[1])
replace = os.replace

def paused(source, destination):
    (root / 'ready').write_text(str(source))
    time.sleep(30)
    replace(source, destination)

with source_updates(root), patch('os.replace', paused):
    write_updates({root / 'output': 'B' * 65536})
"""
        for sig in (signal.SIGTERM, signal.SIGKILL):
            with self.subTest(signal=sig), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                target = root / "output"
                target.write_text("A" * 65536)
                process = subprocess.Popen(
                    [sys.executable, "-c", program, str(root)],
                    cwd=ROOT,
                    text=True,
                    start_new_session=True,
                )
                self.addCleanup(stop_process_group, process)
                deadline = time.monotonic() + 5
                while not (root / "ready").exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue((root / "ready").exists())
                staged = Path((root / "ready").read_text())
                self.assertEqual(staged.read_bytes(), b"B" * 65536)
                process.send_signal(sig)
                process.wait(timeout=5)
                self.assertEqual(target.read_bytes(), b"A" * 65536)
                with updates.source_updates(root):
                    updates.write_updates({target: "complete"})
                self.assertEqual(target.read_text(), "complete")

    def test_nested_and_concurrent_commands_preserve_all_updates(self) -> None:
        program = """
import json
from pathlib import Path
import sys
from scripts.repository.file_updates import read_source, source_updates, write_updates

root = Path(sys.argv[1])
for index in range(10):
    with source_updates(root), source_updates(root):
        data = json.loads(read_source(root / 'registry.json'))
        data[f'{sys.argv[2]}-{index}'] = True
        write_updates({root / 'registry.json': json.dumps(data)})
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = root / "registry.json"
            registry.write_text("{}")
            processes = []
            for name in ("first", "second"):
                process = subprocess.Popen(
                    [sys.executable, "-c", program, str(root), name],
                    cwd=ROOT,
                    text=True,
                    start_new_session=True,
                )
                self.addCleanup(stop_process_group, process)
                processes.append(process)
            for process in processes:
                self.assertEqual(process.wait(timeout=10), 0)
            self.assertEqual(len(json.loads(registry.read_text())), 20)

    def test_check_scope_does_not_create_lock_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with updates.source_updates(root, check=True):
                self.assertEqual(
                    updates.changed_files({root / "missing": "value"}),
                    [root / "missing"],
                )
            self.assertFalse((root / "build").exists())
