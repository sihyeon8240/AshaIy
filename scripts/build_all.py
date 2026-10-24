"""Schedule bounded textbook builds and collect output and failures by book."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validation_patterns import validation_pattern

ROOT = Path(__file__).resolve().parent.parent


class BuildInterrupted(Exception):
    """Request termination of every active build process group."""


@dataclass
class Worker:
    process: subprocess.Popen
    output: BinaryIO
    log: Path
    checking: bool = False


def job_count() -> int:
    configured = os.environ.get("BOOK_BUILD_JOBS")
    if configured is None:
        return min(4, os.cpu_count() or 2)
    if not re.fullmatch(validation_pattern("positive_integer"), configured):
        raise ValueError(
            "BOOK_BUILD_JOBS must be a positive integer (for example, BOOK_BUILD_JOBS=2)"
        )
    return int(configured)


def stop_workers(workers: dict[str, Worker]) -> None:
    for worker in workers.values():
        try:
            os.killpg(worker.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 2
    for worker in workers.values():
        try:
            worker.process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for worker in workers.values():
        # Descendants may outlive their group leader; stop the complete group.
        try:
            os.killpg(worker.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        worker.process.wait()


def build_all(purpose: str) -> int:
    jobs = job_count()
    python = os.environ.get("PYTHON", sys.executable)
    targets = subprocess.check_output(
        [
            python,
            str(ROOT / "scripts/books.py"),
            "list",
            "--for",
            purpose,
            "--warnings",
        ],
        text=True,
        cwd=ROOT,
    ).splitlines()
    books = iter(slug for slug in targets if slug)
    print("config/books.yml is valid", flush=True)
    workers: dict[str, Worker] = {}
    succeeded = []
    failed = []
    exhausted = False

    def interrupted(signum, frame) -> None:
        raise BuildInterrupted

    previous_handlers = {
        sig: signal.signal(sig, interrupted)
        for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    }
    try:
        with (
            tempfile.TemporaryDirectory(prefix="book-build-all.") as temporary,
            ExitStack() as stack,
        ):
            try:
                while workers or not exhausted:
                    while len(workers) < jobs and not exhausted:
                        slug = next(books, None)
                        if slug is None:
                            exhausted = True
                            break
                        log = Path(temporary) / f"{slug}.console.log"
                        output = stack.enter_context(log.open("wb"))
                        print(f"==> Starting {slug}", flush=True)
                        process = subprocess.Popen(
                            [str(ROOT / "scripts/build_book.sh"), slug],
                            cwd=ROOT,
                            stdout=output,
                            stderr=subprocess.STDOUT,
                            start_new_session=True,
                        )
                        workers[slug] = Worker(process, output, log)
                    for slug, worker in list(workers.items()):
                        status = worker.process.poll()
                        if status is None:
                            continue
                        if status == 0 and purpose == "check" and not worker.checking:
                            options = (
                                ["--strict"]
                                if os.environ.get("CHECK_LOG_STRICT") == "1"
                                else []
                            )
                            worker.process = subprocess.Popen(
                                [
                                    python,
                                    str(ROOT / "scripts/check_log.py"),
                                    *options,
                                    str(ROOT / "build" / slug / "book.log"),
                                ],
                                cwd=ROOT,
                                stdout=worker.output,
                                stderr=subprocess.STDOUT,
                                start_new_session=True,
                            )
                            worker.checking = True
                            continue
                        del workers[slug]
                        worker.output.close()
                        print(f"\n==> Output: {slug}", flush=True)
                        with worker.log.open("rb") as source:
                            shutil.copyfileobj(source, sys.stdout.buffer)
                        sys.stdout.flush()
                        if status == 0:
                            print(f"==> Built {slug}", flush=True)
                            succeeded.append(slug)
                        else:
                            status = 128 - status if status < 0 else status
                            print(f"==> FAILED {slug} (exit {status})", flush=True)
                            failed.append(slug)
                    if workers:
                        time.sleep(0.02)
            finally:
                # Ignore repeated termination while reaping children and cleaning logs.
                for sig in previous_handlers:
                    signal.signal(sig, signal.SIG_IGN)
                stop_workers(workers)
    except BuildInterrupted:
        return 130
    finally:
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)

    if not succeeded and not failed:
        print(f"No books are enabled for {purpose} in config/books.yml.")
        return 0
    print(f"\nBuild summary:\n  succeeded: {len(succeeded)}\n  failed: {len(failed)}")
    if failed:
        print("\nFailed books:")
        for slug in failed:
            print(f"  - {slug}")
    return int(bool(failed))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "purpose", choices=("build", "check"), nargs="?", default="build"
    )
    args = parser.parse_args()
    try:
        return build_all(args.purpose)
    except subprocess.CalledProcessError as error:
        return error.returncode
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2 if isinstance(error, ValueError) else 1


if __name__ == "__main__":
    raise SystemExit(main())
