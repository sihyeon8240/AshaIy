"""Bound external work and reap process groups before restoring signal handlers."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable, Generator, Iterable
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from pathlib import Path
from typing import BinaryIO, TypeVar

Item = TypeVar("Item")
Result = TypeVar("Result")


def worker_count(jobs: int | None = None) -> int:
    if jobs is not None and jobs < 1:
        raise ValueError("jobs must be a positive integer")
    return jobs if jobs is not None else min(4, os.process_cpu_count() or 2)


class ProcessRunner:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.processes: set[subprocess.Popen] = set()
        self.cancelled = False

    def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        stderr: int | None = subprocess.STDOUT,
        output: BinaryIO | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        with self.lock:
            if self.cancelled:
                raise InterruptedError("work cancelled")
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE if output is None else output,
                stderr=stderr,
                start_new_session=True,
            )
            self.processes.add(process)
        try:
            captured, errors = process.communicate()
            return subprocess.CompletedProcess(command, process.returncode, captured or b"", errors)
        finally:
            with self.lock:
                self.processes.discard(process)

    def check_output(self, command: list[str]) -> bytes:
        result = self.run(command, stderr=None)
        result.check_returncode()
        return result.stdout

    def cancel(self) -> None:
        with self.lock:
            self.cancelled = True
            processes = tuple(self.processes)
        for process in processes:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 7
        for process in processes:
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                pass
        for process in processes:
            # A descendant may still be alive after its group leader exits.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()


def iter_parallel(
    items: Iterable[Item], operation: Callable[[Item, ProcessRunner], Result], *, jobs: int | None = None
) -> Generator[Result, None, None]:
    runner = ProcessRunner()

    def interrupted(signum, frame) -> None:
        raise KeyboardInterrupt

    signals = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    previous = {sig: signal.signal(sig, interrupted) for sig in signals}
    try:
        count = worker_count(jobs)
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = deque()
            pending = iter(items)
            try:
                for item in islice(pending, count * 2):
                    futures.append(executor.submit(operation, item, runner))
                while futures:
                    yield futures.popleft().result()
                    for item in islice(pending, 1):
                        futures.append(executor.submit(operation, item, runner))
            except BaseException:
                for sig in signals:
                    signal.signal(sig, signal.SIG_IGN)
                for future in futures:
                    future.cancel()
                runner.cancel()
                raise
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def run_parallel(
    items: Iterable[Item], operation: Callable[[Item, ProcessRunner], Result], *, jobs: int | None = None
) -> list[Result]:
    return list(iter_parallel(items, operation, jobs=jobs))
