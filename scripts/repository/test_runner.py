"""Run unittest modules in isolated processes with bounded concurrency."""

from __future__ import annotations

import argparse
import fnmatch
import re
import signal
import sys
import time
import unittest
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.repository.processes import ProcessRunner, run_parallel, worker_count

ROOT = Path(__file__).resolve().parents[2]


def test_cases(suite: unittest.TestSuite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from test_cases(test)
        else:
            yield test


def test_modules(suite: unittest.TestSuite) -> dict[str, int]:
    modules: dict[str, int] = {}
    for test in test_cases(suite):
        module = test.__class__.__module__
        if module == "unittest.loader":
            raise ValueError(
                "test discovery failed:\n" + "\n".join(str(error) for error in unittest.defaultTestLoader.errors)
            )
        modules[module] = modules.get(module, 0) + 1
    return modules


def run_module(module: str) -> int:
    sys.path.insert(0, str(Path.cwd()))
    suite = unittest.defaultTestLoader.loadTestsFromName(module)
    cases = list(test_cases(suite))

    def interrupted(signum, frame) -> None:
        raise KeyboardInterrupt

    for sig in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(sig, interrupted)
    try:
        return int(not unittest.TextTestRunner(verbosity=2, buffer=True).run(suite).wasSuccessful())
    finally:
        # Interrupted TestCase.run may bypass its registered cleanups.
        for test in reversed(cases):
            test.doCleanups()
        for cls in dict.fromkeys(type(test) for test in reversed(cases)):
            cls.doClassCleanups()


def run_tests(directory: str, pattern: str, *, jobs: int | None = None, root: Path = ROOT) -> int:
    count = worker_count(jobs)
    suite = unittest.defaultTestLoader.discover(directory, pattern=pattern, top_level_dir=str(root))
    modules_with_hooks = any(
        callable(getattr(module, "load_tests", None))
        and (filename := getattr(module, "__file__", None))
        and Path(filename).is_relative_to(Path(directory).resolve())
        for module in tuple(sys.modules.values())
    )
    imported_cases = any(
        not fnmatch.fnmatch(
            Path(getattr(sys.modules.get(test.__class__.__module__), "__file__", None) or "").name, pattern
        )
        for test in test_cases(suite)
    )
    if modules_with_hooks or imported_cases:
        print("Custom unittest discovery; running the discovered suite in one process.", flush=True)
        return int(not unittest.TextTestRunner(verbosity=2, buffer=True).run(suite).wasSuccessful())
    modules = test_modules(suite)
    started = time.monotonic()

    def execute(module: str, runner: ProcessRunner):
        return module, runner.run([sys.executable, str(Path(__file__).resolve()), "--module", module], cwd=root)

    results = run_parallel(sorted(modules, key=lambda name: -modules[name]), execute, jobs=count)
    failed = skipped = 0
    for module, result in results:
        output = result.stdout.decode(errors="replace")
        counts = re.findall(r"^Ran (\d+) tests? in ", output, re.MULTILINE)
        complete = bool(counts) and int(counts[-1]) == modules[module]
        if result.returncode or not complete:
            failed += 1
            if not complete:
                output += f"\nTest count differs from discovery: expected {modules[module]}.\n"
            print(f"\n==> Failed: {module}\n{output}", file=sys.stderr)
        else:
            for line in output.splitlines():
                if " ... skipped " in line:
                    print(line)
        match = re.search(r"\bskipped=(\d+)", output)
        if match:
            skipped += int(match[1])
    print(
        f"Ran {sum(modules.values())} tests in {time.monotonic() - started:.3f}s "
        f"({len(modules)} modules, {count} workers; {skipped} skipped)"
    )
    print(f"FAILED ({failed} modules)" if failed else "OK")
    return int(bool(failed))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default="tests")
    parser.add_argument("--pattern", default="test_*.py")
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--module", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    try:
        if arguments.module:
            return run_module(arguments.module)
        return run_tests(arguments.directory, arguments.pattern, jobs=arguments.jobs)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
