"""Parallel work preserves failures and reaps descendants on interruption."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path

from scripts.repository.benchmark import tree_rss
from scripts.repository.processes import ProcessRunner, iter_parallel
from scripts.repository.test_runner import run_tests
from tests.support.fixtures import stop_process_group

ROOT = Path(__file__).resolve().parents[2]


class ParallelCommandsTests(unittest.TestCase):
    @unittest.skipUnless(Path("/proc/self/status").exists(), "Linux process accounting is required")
    def test_memory_measurement_includes_children_started_by_worker_threads(self) -> None:
        ready = threading.Event()
        finished = threading.Event()
        processes = []

        def execute():
            with subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import sys; data = bytearray(33554432); print('ready', flush=True); sys.stdin.read()",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            ) as process:
                processes.append(process)
                assert process.stdout is not None
                process.stdout.readline()
                ready.set()
                finished.wait(timeout=10)
                process.communicate(input=b"done", timeout=5)

        thread = threading.Thread(target=execute)
        thread.start()
        try:
            self.assertTrue(ready.wait(timeout=5), "child did not start")

            def rss(pid):
                return next(
                    int(line.split()[1])
                    for line in Path(f"/proc/{pid}/status").read_text().splitlines()
                    if line.startswith("VmRSS:")
                )

            expected = rss(os.getpid()) + rss(processes[0].pid)
            self.assertGreaterEqual(tree_rss(os.getpid()), expected - 4096)
        finally:
            finished.set()
            thread.join(timeout=10)
        self.assertFalse(thread.is_alive())

    def test_worker_temporary_bytecode_is_removed_after_the_suite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "bytecode_cases"
            package.mkdir()
            (package / "__init__.py").touch()
            (package / "test_cache.py").write_text(
                "import json, py_compile, tempfile, unittest\nfrom pathlib import Path\n"
                "class Example(unittest.TestCase):\n"
                "    def test_temporary_import(self):\n"
                "        with tempfile.TemporaryDirectory() as directory:\n"
                "            source = Path(directory) / 'fixture.py'\n"
                "            source.write_text('value = 1\\n')\n"
                "            cache = py_compile.compile(str(source), doraise=True)\n"
                "            Path('cache-path.json').write_text(json.dumps(cache))\n"
                "            self.assertTrue(Path(cache).is_file())\n"
            )
            original_path = sys.path[:]
            self.addCleanup(setattr, sys, "path", original_path)
            self.assertEqual(run_tests(str(package), "test_*.py", jobs=2, root=root), 0)
            cache = Path(json.loads((root / "cache-path.json").read_text()))
            self.assertIn("test-logs-", str(cache))
            self.assertFalse(cache.exists())

    def test_bounded_submission_preserves_order_and_accepts_none_items(self) -> None:
        submitted = []

        def items():
            for value in [None, *range(100)]:
                submitted.append(value)
                yield value

        with closing(iter_parallel(items(), lambda value, runner: value, jobs=2)) as results:
            self.assertIsNone(next(results))
            self.assertEqual(len(submitted), 4)
            self.assertEqual(list(results), list(range(100)))

    def test_large_output_can_be_written_without_retaining_result_bytes(self) -> None:
        with tempfile.TemporaryFile() as output:
            result = ProcessRunner().run(
                [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 2097152)"], output=output
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"")
            self.assertEqual(output.tell(), 2097152)

    def test_custom_discovery_executes_function_cases_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "custom_cases"
            package.mkdir()
            (package / "__init__.py").touch()
            marker = root / "executions"
            (package / "test_custom.py").write_text(
                "import unittest\nfrom pathlib import Path\n"
                "def load_tests(loader, tests, pattern):\n"
                "    def action():\n"
                f"        path = Path({str(marker)!r})\n"
                "        path.write_text(path.read_text() + 'x' if path.exists() else 'x')\n"
                "    return unittest.TestSuite([unittest.FunctionTestCase(action)])\n"
            )
            original_path = sys.path[:]
            self.addCleanup(setattr, sys, "path", original_path)
            self.assertEqual(run_tests(str(package), "test_*.py", jobs=4, root=root), 0)
            self.assertEqual(marker.read_text(), "x")

    def test_test_failures_do_not_hide_independent_results_or_skips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "specimens"
            package.mkdir()
            (package / "__init__.py").touch()
            (package / "test_failure.py").write_text(
                "import unittest\n"
                "class Example(unittest.TestCase):\n"
                "    def test_failure(self): self.fail('observable failure')\n"
            )
            (package / "test_success.py").write_text(
                "import unittest\nfrom pathlib import Path\n"
                "class Example(unittest.TestCase):\n"
                "    def test_success(self): Path('finished').write_text('done')\n"
                "    @unittest.skip('explicit reason')\n"
                "    def test_skip(self): pass\n"
            )
            original_path = sys.path[:]
            self.addCleanup(setattr, sys, "path", original_path)
            self.assertEqual(run_tests(str(package), "test_*.py", jobs=2, root=root), 1)
            self.assertEqual((root / "finished").read_text(), "done")

    def test_interruption_reaps_a_descendant_that_ignores_termination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            descendant = (
                "import os, signal, time\nfrom pathlib import Path\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                f"Path({str(root / 'child')!r}).write_text(str(os.getpid()))\n"
                "time.sleep(60)\n"
            )
            command = (
                "import subprocess, sys, time\n"
                f"subprocess.Popen([sys.executable, '-c', {descendant!r}])\n"
                "time.sleep(60)\n"
            )
            script = (
                "import sys\n"
                f"sys.path.insert(0, {str(ROOT)!r})\n"
                "from scripts.repository.processes import run_parallel\n"
                "try:\n"
                f"    run_parallel([1], lambda _, runner: runner.run([sys.executable, '-c', {command!r}]))\n"
                "except KeyboardInterrupt:\n"
                "    sys.exit(130)\n"
            )
            process = subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                text=True,
            )
            self.addCleanup(stop_process_group, process)
            deadline = time.monotonic() + 10
            while not (root / "child").exists():
                self.assertIsNone(process.poll())
                if time.monotonic() >= deadline:
                    self.fail("descendant did not start")
                time.sleep(0.01)
            pid = int((root / "child").read_text())
            process.send_signal(signal.SIGTERM)
            output, errors = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 130, (output, errors))
            status = Path(f"/proc/{pid}/stat")
            if status.exists():
                self.assertEqual(status.read_text().split()[2], "Z", f"descendant {pid} survived")
