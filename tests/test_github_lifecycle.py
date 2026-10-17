"""Consecutive snapshot publication and out-of-order deployment with real Git."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_support import (
    book_record,
    git_environment,
    manifest_document,
    write_executable,
    write_yaml,
)

ROOT = Path(__file__).resolve().parent.parent


class SnapshotLifecycleTests(unittest.TestCase):
    def test_two_publications_pin_distinct_snapshots_and_skip_old_deployment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / "work"
            work.mkdir()
            (root / "tmp").mkdir()
            env = {**git_environment(), "TMPDIR": str(root / "tmp")}

            def git(*args, cwd=work):
                return subprocess.run(
                    ["git", *args],
                    cwd=cwd,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=15,
                ).stdout.strip()

            remote = root / "origin.git"
            git("init", "--bare", "--initial-branch=main", str(remote))
            git("init", "--initial-branch=main")
            git("remote", "add", "origin", str(remote))
            (work / "scripts").mkdir()
            shutil.copy2(
                ROOT / "scripts/publish-snapshot.sh",
                work / "scripts/publish-snapshot.sh",
            )
            for name in ("snapshot_state.py", "book_manifest.py", "source_reads.py"):
                shutil.copy2(ROOT / "scripts" / name, work / "scripts" / name)
            write_yaml(
                work / "config/books.yml", manifest_document([book_record(site=True)])
            )
            (work / "books/sample").mkdir(parents=True)
            (work / "books/sample/book.tex").write_text("test book\n")
            (work / ".github").mkdir()
            (work / ".github/generated-pdfs-README.md").write_text("Snapshot\n")
            git("add", ".")
            git("commit", "-m", "Source A")
            git("push", "origin", "main")
            sources = []
            snapshots = []

            def publish(source, output):
                return subprocess.run(
                    [work / "scripts/publish-snapshot.sh"],
                    cwd=work,
                    env={**env, "GITHUB_SHA": source, "GITHUB_OUTPUT": str(output)},
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )

            for index in range(2):
                if index:
                    (work / "later-source").write_text("Source B")
                    git("add", "later-source")
                    git("commit", "-m", "Source B")
                    git("push", "origin", "main")
                source = git("rev-parse", "HEAD")
                (work / "updated-pdfs").mkdir(exist_ok=True)
                pdf = f"%PDF-1.7\nsnapshot {index}"
                (work / "updated-pdfs/sample.pdf").write_text(pdf)
                hook = remote / "hooks/pre-receive"
                write_executable(hook, "#!/bin/sh\nexit 1\n")
                rejected_output = root / f"rejected-{index}"
                rejected = publish(source, rejected_output)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertFalse(rejected_output.exists())
                self.assertEqual(
                    git("worktree", "list", "--porcelain").count("worktree "), 1
                )
                self.assertEqual(list((root / "tmp").iterdir()), [])
                self.assertEqual(
                    git(
                        "for-each-ref",
                        "--format=%(refname)",
                        "refs/heads/snapshot-bootstrap-*",
                    ),
                    "",
                )
                if snapshots:
                    self.assertEqual(
                        git("rev-parse", "origin/generated-pdfs"), snapshots[-1]
                    )
                hook.unlink()
                output = root / f"publish-{index}"
                result = publish(source, output)
                self.assertEqual(result.returncode, 0, result.stderr)
                fields = dict(
                    line.split("=", 1) for line in output.read_text().splitlines()
                )
                snapshot = fields["snapshot_sha"]
                self.assertEqual(fields["current"], "true")
                self.assertEqual(git("show", f"{snapshot}:.source-sha"), source)
                self.assertEqual(git("show", f"{snapshot}:pdf/sample.pdf"), pdf)
                sources.append(source)
                snapshots.append(snapshot)
                retry_output = root / f"retry-{index}"
                retry = publish(source, retry_output)
                self.assertEqual(retry.returncode, 0, retry.stderr)
                self.assertIn(f"snapshot_sha={snapshot}\n", retry_output.read_text())
                self.assertEqual(
                    git("worktree", "list", "--porcelain").count("worktree "), 1
                )
                self.assertEqual(list((root / "tmp").iterdir()), [])
            self.assertNotEqual(*snapshots)
            self.assertEqual(git("show", f"{snapshots[0]}:.source-sha"), sources[0])
            for index, snapshot in enumerate(snapshots):
                output = root / f"deploy-{index}"
                result = subprocess.run(
                    [ROOT / "scripts/pages-current.sh"],
                    cwd=work,
                    env={**env, "SNAPSHOT_SHA": snapshot, "GITHUB_OUTPUT": str(output)},
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    output.read_text(), f"current={str(index == 1).lower()}\n"
                )
