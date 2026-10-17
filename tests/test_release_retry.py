"""Original-package release recovery rejects changed provenance and bytes."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import yaml
from test_support import book_record, manifest_document

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "release_retry", ROOT / "scripts/release-retry.py"
)
RETRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETRY)


class ReleaseRetryTests(unittest.TestCase):
    def setUp(self):
        self.source = "a" * 40
        self.run = {
            "id": 42,
            "run_attempt": 1,
            "event": "push",
            "head_branch": "main",
            "head_sha": self.source,
            "status": "completed",
            "conclusion": "failure",
            "path": ".github/workflows/build.yml",
            "head_repository": {"full_name": "owner/repo"},
        }
        self.expected = {
            "policy": "release-package-v1",
            "book": "alpha",
            "version": "1.0.0",
            "source_sha": self.source,
        }
        self.jobs = [
            {"name": name, "conclusion": "success"}
            for name in ("Check sources", "Verify textbook builds", "Build alpha")
        ]
        self.pdf_name = "alpha-v1.0.0.pdf"
        self.pdf = b"%PDF-original reviewed bytes"
        self.files = {
            self.pdf_name: self.pdf,
            "SHA256SUMS": f"{RETRY.checksum(self.pdf)}  {self.pdf_name}\n".encode(),
        }
        self.manifest = {
            **self.expected,
            "run_id": "42",
            "run_attempt": "1",
            "checksums": {
                name: RETRY.checksum(data) for name, data in self.files.items()
            },
        }

    def archive(self, path, *, manifest=None, files=None):
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in (self.files if files is None else files).items():
                archive.writestr(name, content)
            archive.writestr(
                "release-build.json",
                json.dumps(self.manifest if manifest is None else manifest),
            )

    def test_failed_publication_run_is_eligible_when_its_build_gates_passed(self):
        self.assertEqual(RETRY.validate_run(self.run, "owner/repo"), self.source)
        RETRY.validate_jobs(self.jobs, "alpha")
        for key, value in (
            ("event", "pull_request"),
            ("head_branch", "topic"),
            ("status", "in_progress"),
            ("head_repository", {"full_name": "fork/repo"}),
            ("head_sha", "invalid"),
            ("path", ".github/workflows/release-retry.yml"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                RETRY.validate_run({**self.run, key: value}, "owner/repo")

    def test_failed_missing_or_ambiguous_build_gate_rejects_retry(self):
        for index in range(len(self.jobs)):
            for conclusion in ("failure", "skipped", "cancelled"):
                jobs = [dict(job) for job in self.jobs]
                jobs[index]["conclusion"] = conclusion
                with (
                    self.subTest(index=index, conclusion=conclusion),
                    self.assertRaises(ValueError),
                ):
                    RETRY.validate_jobs(jobs, "alpha")
        for jobs in (self.jobs[:-1], self.jobs + [self.jobs[0]]):
            with self.assertRaises(ValueError):
                RETRY.validate_jobs(jobs, "alpha")

    def test_package_identity_checksums_and_original_pdf_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "release.zip"
            self.archive(path)
            self.assertEqual(
                RETRY.validate_archive(path, self.expected, self.run)[self.pdf_name],
                self.pdf,
            )
            for key in (*self.expected, "run_id", "run_attempt"):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    self.archive(path, manifest={**self.manifest, key: "wrong"})
                    RETRY.validate_archive(path, self.expected, self.run)
            for files in (
                {**self.files, self.pdf_name: b"%PDF-rebuilt later"},
                {**self.files, "SHA256SUMS": b"wrong"},
                {**self.files, "../unexpected": b"script"},
            ):
                with self.assertRaises(ValueError):
                    self.archive(path, files=files)
                    RETRY.validate_archive(path, self.expected, self.run)

    def test_restore_keeps_original_bytes_after_main_and_run_attempt_advance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original.zip"
            self.archive(original)
            artifact = {
                "id": 9,
                "name": "alpha-release",
                "expired": False,
                "size_in_bytes": original.stat().st_size,
                "digest": "sha256:" + RETRY.checksum(original),
            }
            manifest = manifest_document([book_record("alpha", release=True)])

            def execute(*args):
                if args[:2] == ("git", "show"):
                    self.assertEqual(args[2], f"{self.source}:config/books.yml")
                    return yaml.safe_dump(manifest).encode()
                return b""

            def download(repository, selected, target, *, max_bytes):
                self.assertEqual(selected, artifact)
                target.write_bytes(original.read_bytes())

            with (
                patch.dict(
                    os.environ,
                    {"GITHUB_REPOSITORY": "owner/repo", "GITHUB_SHA": "b" * 40},
                ),
                patch.object(
                    RETRY, "api", side_effect=[{**self.run, "run_attempt": 3}, self.run]
                ) as api,
                patch.object(
                    RETRY, "collection", side_effect=[[artifact], self.jobs]
                ) as collection,
                patch.object(RETRY, "command", side_effect=execute) as command,
                patch.object(RETRY, "download", side_effect=download),
            ):
                directory = root / "restored"
                self.assertEqual(
                    RETRY.restore("42", "alpha", "1.0.0", directory), self.source
                )
                self.assertEqual((directory / self.pdf_name).read_bytes(), self.pdf)
                command.assert_any_call(
                    "git", "merge-base", "--is-ancestor", self.source, "origin/main"
                )
                api.assert_any_call("repos/owner/repo/actions/runs/42/attempts/1")
                collection.assert_any_call(
                    "repos/owner/repo/actions/runs/42/attempts/1/jobs", "jobs"
                )
                self.assertFalse(
                    any("build-book" in str(call) for call in command.call_args_list)
                )

    def test_wrong_version_or_unmerged_source_cannot_download(self):
        for unmerged in (False, True):

            def execute(*args):
                if args[:2] == ("git", "merge-base") and unmerged:
                    raise subprocess.CalledProcessError(1, args)
                if args[:2] == ("git", "show"):
                    return yaml.safe_dump(
                        manifest_document([book_record("alpha", release=True)])
                    ).encode()
                return b""

            with (
                self.subTest(unmerged=unmerged),
                patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}),
                patch.object(RETRY, "api", return_value=self.run),
                patch.object(RETRY, "command", side_effect=execute),
                patch.object(RETRY, "download") as download,
                self.assertRaises((ValueError, subprocess.CalledProcessError)),
            ):
                RETRY.restore("42", "alpha", "2.0.0", Path("unused"))
            download.assert_not_called()

    def test_package_recorder_round_trips_into_retry_validation(self):
        spec = importlib.util.spec_from_file_location(
            "release_package", ROOT / "scripts/release-package.py"
        )
        package = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(package)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name, content in self.files.items():
                (directory / name).write_bytes(content)
            with (
                patch.dict(
                    os.environ,
                    {
                        "GITHUB_SHA": self.source,
                        "GITHUB_RUN_ID": "42",
                        "GITHUB_RUN_ATTEMPT": "1",
                    },
                ),
                patch.object(package, "command", return_value=self.source.encode()),
            ):
                package.record("alpha", directory)
            archive_path = directory / "recorded.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name in (*self.files, "release-build.json"):
                    archive.write(directory / name, name)
            self.assertEqual(
                RETRY.validate_archive(archive_path, self.expected, self.run)[
                    self.pdf_name
                ],
                self.pdf,
            )

    def test_expired_or_oversized_artifacts_never_start_a_download(self):
        for artifact in (
            {"expired": True},
            {"expired": False, "size_in_bytes": RETRY.MAX_BYTES + 1},
        ):
            with (
                self.subTest(artifact=artifact),
                patch("github_artifacts.subprocess.run") as execute,
                self.assertRaises(ValueError),
            ):
                RETRY.download(
                    "owner/repo",
                    artifact,
                    Path("unused.zip"),
                    max_bytes=RETRY.MAX_BYTES,
                )
            execute.assert_not_called()

    def test_retry_workflow_validates_without_write_permissions(self):
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/release-retry.yml").read_text()
        )
        self.assertEqual(
            workflow["permissions"], {"contents": "read", "actions": "read"}
        )
        self.assertNotIn("permissions", workflow["jobs"]["restore"])
        self.assertEqual(workflow["jobs"]["publish"]["needs"], "restore")
        self.assertEqual(workflow["jobs"]["publish"]["concurrency"]["queue"], "max")


if __name__ == "__main__":
    unittest.main()
