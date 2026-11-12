"""Reproduce repository scaling and resource measurements in disposable workspaces."""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml

ROOT = Path(__file__).resolve().parents[2]


def tree_rss(pid: int) -> int:
    pending = [pid]
    total = 0
    while pending:
        process = pending.pop()
        try:
            status = Path(f"/proc/{process}/status").read_text()
            total += next((int(line.split()[1]) for line in status.splitlines() if line.startswith("VmRSS:")), 0)
            children = Path(f"/proc/{process}/task/{process}/children").read_text()
            pending.extend(int(child) for child in children.split())
        except OSError, ProcessLookupError:
            continue
    return total


def measure(command: list[str], cwd: Path, log: Path, *, env: dict[str, str] | None = None) -> dict:
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    peak = 0
    with (
        log.open("wb") as output,
        subprocess.Popen(
            command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True
        ) as process,
    ):
        try:
            while True:
                peak = max(peak, tree_rss(process.pid))
                try:
                    status = process.wait(timeout=0.02)
                    break
                except subprocess.TimeoutExpired:
                    continue
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if status:
        raise ValueError(f"benchmark command failed ({status}); see {log}")
    return {
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
        "sampled_tree_rss_kib": peak if Path("/proc").is_dir() else None,
    }


def synthetic_repository(root: Path, books: int, sections: int) -> None:
    for directory in ("scripts", "config", "common", ".devcontainer"):
        shutil.copytree(ROOT / directory, root / directory, ignore=shutil.ignore_patterns("__pycache__"))
    records = []
    for index in range(books):
        slug = f"book-{index}"
        directory = root / "books" / slug
        topic = directory / "chapters/topic"
        topic.mkdir(parents=True)
        (directory / "book.tex").touch()
        (directory / "references.bib").touch()
        records.append({"slug": slug, "title": f"Book {index}", "label_prefix": f"b{index}", "order": index})
        (directory / "chapters.yml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "chapters": [{"slug": "topic", "title": "Topic"}],
                }
            )
        )
        (topic / "sections.yml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "sections": [
                        {"slug": f"section-{number}", "title": f"Section {number}"} for number in range(sections)
                    ],
                }
            )
        )
        for number in range(sections):
            (topic / f"section-{number}.tex").write_text(f"\\label{{b{index}:sec:section-{number}}}\n")
    (root / "config/books.yml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "defaults": {
                    "author": "Benchmark",
                    "version": "0.1.0",
                    "status": "draft",
                    "site": True,
                    "build": True,
                    "check": True,
                    "release": False,
                },
                "books": records,
            }
        )
    )
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from scripts.books.contents_generation import generate; raise SystemExit(generate('all'))",
        ],
        cwd=root,
        stdout=subprocess.DEVNULL,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books", type=int, nargs="+", default=[3, 10, 30, 60])
    parser.add_argument("--sections", type=int, default=100)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--include-checks", action="store_true", help="also measure serial/parallel tests and cold/warm formatting"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "build/benchmarks/result.json")
    arguments = parser.parse_args()
    if min(*arguments.books, arguments.sections, arguments.repeats) < 1:
        parser.error("book, section, and repeat counts must be positive")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_version": 1,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.process_cpu_count(),
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "rss_note": "20ms sampled sum of process RSS; shared pages are counted more than once; short peaks may be missed",
        "cases": [],
    }
    cases = result["cases"]
    try:
        with tempfile.TemporaryDirectory(prefix="ashaiy-benchmark-") as temporary:
            for books in arguments.books:
                root = Path(temporary) / str(books)
                synthetic_repository(root, books, arguments.sections)
                operations = {
                    "planning": "from scripts.ci.book_impact import plan; plan(['books/book-0/chapters/topic/section-0.tex'])",
                    "site": "from scripts.site.site_pages import render_site; from scripts.books.book_manifest import load_manifest; render_site(load_manifest())",
                    "macros": "from scripts.latex.macro_generation import generate; raise SystemExit(generate(check=True))",
                }
                for name, operation in operations.items():
                    samples = [
                        measure(
                            [sys.executable, "-c", operation],
                            root,
                            arguments.output.parent / f"{name}-{books}-{repeat}.log",
                        )
                        for repeat in range(arguments.repeats)
                    ]
                    cases.append(
                        {
                            "name": name,
                            "books": books,
                            "sections_per_book": arguments.sections,
                            "samples": samples,
                            "median_seconds": statistics.median(sample["wall_seconds"] for sample in samples),
                        }
                    )
            operation = (
                "import sys,tempfile; from scripts.repository.processes import run_parallel; "
                "output=tempfile.TemporaryFile(); "
                "run_parallel(range(64),lambda _,runner:runner.run([sys.executable,'-c',"
                "\"import sys; sys.stdout.buffer.write(b'x'*1048576)\"],output=output),jobs=4)"
            )
            cases.append(
                {
                    "name": "64-mib-output",
                    "samples": [
                        measure([sys.executable, "-c", operation], ROOT, arguments.output.parent / "output.log")
                    ],
                }
            )
            if arguments.include_checks:
                for jobs in (1, 4):
                    samples = [
                        measure(
                            [sys.executable, "scripts/ashaiy", "test", "--jobs", str(jobs)],
                            ROOT,
                            arguments.output.parent / f"tests-{jobs}-{repeat}.log",
                        )
                        for repeat in range(arguments.repeats)
                    ]
                    cases.append({"name": "tests", "jobs": jobs, "samples": samples})
                    cache = Path(temporary) / f"format-{jobs}"
                    env = {**os.environ, "FORMAT_TEX_CACHE_DIR": str(cache)}
                    for state in ("cold", "warm"):
                        sample = measure(
                            [sys.executable, "scripts/ashaiy", "format", "tex", "--check", "--jobs", str(jobs)],
                            ROOT,
                            arguments.output.parent / f"format-{jobs}-{state}.log",
                            env=env,
                        )
                        cache_bytes = sum(path.stat().st_size for path in cache.rglob("*") if path.is_file())
                        cases.append(
                            {
                                "name": "format",
                                "jobs": jobs,
                                "cache": state,
                                "cache_bytes": cache_bytes,
                                "samples": [sample],
                            }
                        )
        arguments.output.write_text(json.dumps(result, indent=2) + "\n")
        print(f"Saved benchmark measurements: {arguments.output}")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
