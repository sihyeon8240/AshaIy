"""Regression tests for validated PR PDF reuse and cache boundaries."""

from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import verified_build as BUILD

ROOT = Path(__file__).resolve().parent.parent


class VerifiedBuildTests(unittest.TestCase):
    def setUp(self):
        self.expected = {
            "policy": BUILD.POLICY,
            "book": "linear-algebra",
            "image": "ghcr.io/example/math@sha256:" + "a" * 64,
            "platform": "linux/amd64",
            "tree": "b" * 40,
        }
        self.workflow_run = {
            "id": 123,
            "run_attempt": 2,
            "event": "pull_request",
            "status": "completed",
            "conclusion": "success",
            "head_sha": "c" * 40,
            "head_repository": {"full_name": "example/math"},
            "path": ".github/workflows/build.yml",
        }
        self.files = {"book.pdf": b"%PDF-1.5\nverified", "book.log": b"clean log\n"}

    def archive(self, *, identity=None, files=None, extra=None, manifest_update=None):
        files = self.files if files is None else files
        manifest = {
            **(self.expected if identity is None else identity),
            "run_id": "123",
            "run_attempt": "2",
            "checksums": {name: BUILD.checksum(data) for name, data in files.items()},
            **(manifest_update or {}),
        }
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for name, data in {**files, **(extra or {})}.items():
                archive.writestr(name, data)
            archive.writestr("verified-build.json", json.dumps(manifest))
        return stream.getvalue()

    def test_matching_verified_archive_is_accepted(self):
        self.assertEqual(
            BUILD.verify_archive(self.archive(), self.expected, self.workflow_run),
            self.files,
        )

    def test_every_build_identity_field_must_match(self):
        for key in self.expected:
            with self.subTest(key=key):
                changed = {**self.expected, key: "changed"}
                with self.assertRaisesRegex(ValueError, "identity differs"):
                    BUILD.verify_archive(
                        self.archive(identity=changed), self.expected, self.workflow_run
                    )

    def test_run_and_attempt_must_match(self):
        for key in ("run_id", "run_attempt"):
            with (
                self.subTest(key=key),
                self.assertRaisesRegex(ValueError, "different run"),
            ):
                BUILD.verify_archive(
                    self.archive(manifest_update={key: "999"}),
                    self.expected,
                    self.workflow_run,
                )

    def test_file_checksums_are_checked(self):
        checksums = {name: BUILD.checksum(data) for name, data in self.files.items()}
        cases = {"missing": {}}
        for name in self.files:
            cases[name] = {**checksums, name: "0" * 64}

        for name, changed in cases.items():
            with (
                self.subTest(case=name),
                self.assertRaisesRegex(ValueError, "checksum"),
            ):
                BUILD.verify_archive(
                    self.archive(manifest_update={"checksums": changed}),
                    self.expected,
                    self.workflow_run,
                )

    def test_changed_file_contents_do_not_match_original_checksums(self):
        checksums = {name: BUILD.checksum(data) for name, data in self.files.items()}
        for name, original in self.files.items():
            with (
                self.subTest(file=name),
                self.assertRaisesRegex(ValueError, "checksum"),
            ):
                BUILD.verify_archive(
                    self.archive(
                        files={**self.files, name: original + b"tampered"},
                        manifest_update={"checksums": checksums},
                    ),
                    self.expected,
                    self.workflow_run,
                )

    def test_unexpected_paths_and_missing_files_are_rejected(self):
        for data in (
            self.archive(extra={"../../outside": b"bad"}),
            self.archive(files={"book.pdf": self.files["book.pdf"]}),
        ):
            with self.assertRaisesRegex(ValueError, "unexpected artifact files"):
                BUILD.verify_archive(data, self.expected, self.workflow_run)

    def test_empty_log_and_non_pdf_are_rejected(self):
        for files in (
            {**self.files, "book.log": b""},
            {**self.files, "book.pdf": b"not PDF"},
        ):
            with self.assertRaises(ValueError):
                BUILD.verify_archive(
                    self.archive(files=files), self.expected, self.workflow_run
                )

    def test_artifact_size_limit(self):
        with patch.object(BUILD, "MAX_BYTES", 1), self.assertRaises(ValueError):
            BUILD.verify_archive(self.archive(), self.expected, self.workflow_run)

    def test_only_successful_same_repository_pr_runs_are_eligible(self):
        self.assertTrue(BUILD.eligible_run(self.workflow_run, "example/math", "c" * 40))
        for field, value in (
            ("event", "push"),
            ("status", "in_progress"),
            ("conclusion", "failure"),
            ("head_sha", "d" * 40),
            ("path", ".github/workflows/other.yml"),
            ("head_repository", {"full_name": "fork/math"}),
        ):
            with self.subTest(field=field):
                self.assertFalse(
                    BUILD.eligible_run(
                        {**self.workflow_run, field: value}, "example/math", "c" * 40
                    )
                )

    def restore(
        self,
        *,
        pull_update=None,
        artifact_update=None,
        archive=None,
        run_update=None,
        log_fails=False,
        tree=None,
    ):
        data = archive if archive is not None else self.archive()
        pull = {
            "number": 42,
            "merged_at": "2026-09-07",
            "merge_commit_sha": "d" * 40,
            "base": {"ref": "main"},
            "head": {"sha": "c" * 40, "repo": {"full_name": "example/math"}},
            **(pull_update or {}),
        }
        artifact = {
            "id": 789,
            "name": "linear-algebra-verified-build",
            "expired": False,
            "size_in_bytes": len(data),
            "digest": "sha256:" + BUILD.checksum(data),
            **(artifact_update or {}),
        }
        responses = [
            [pull],
            {"tree": {"sha": tree or self.expected["tree"]}},
            {"workflow_runs": [{**self.workflow_run, **(run_update or {})}]},
            {"artifacts": [artifact]},
        ]

        def command(*args):
            if args[0] == "gh":
                return data
            if log_fails:
                raise subprocess.CalledProcessError(1, args)
            return b""

        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "example/math",
                    "GITHUB_SHA": "d" * 40,
                },
            ),
            patch.object(BUILD, "api", side_effect=responses) as api,
            patch.object(BUILD, "command", side_effect=command) as cmd,
        ):
            directory = Path(temporary)
            reused = BUILD.restore(self.expected, directory)
            pdf = (
                (directory / "book.pdf").read_bytes()
                if (directory / "book.pdf").exists()
                else None
            )
            return reused, pdf, api.call_count, cmd.call_args_list

    def test_restore_downloads_and_rechecks_matching_pdf(self):
        reused, pdf, calls, commands = self.restore()
        self.assertTrue(reused)
        self.assertEqual(pdf, self.files["book.pdf"])
        self.assertEqual(calls, 4)
        self.assertIn("--strict", commands[-1].args)

    def test_unmerged_unrelated_and_fork_prs_never_download(self):
        for change in (
            {"merged_at": None},
            {"merge_commit_sha": "e" * 40},
            {"base": {"ref": "other"}},
            {"head": {"repo": {"full_name": "fork/math"}}},
            {"head": {"repo": None}},
        ):
            with self.subTest(change=change):
                reused, pdf, calls, commands = self.restore(pull_update=change)
                self.assertFalse(reused)
                self.assertIsNone(pdf)
                self.assertEqual(calls, 1)
                self.assertEqual(commands, [])

    def test_missing_expired_or_wrong_artifacts_fall_back(self):
        for change in (
            {"expired": True},
            {"name": "other-book-verified-build"},
            {"size_in_bytes": BUILD.MAX_BYTES + 1},
            {"digest": "sha256:wrong"},
        ):
            with self.subTest(change=change):
                self.assertFalse(self.restore(artifact_update=change)[0])

    def test_failed_run_invalid_archive_and_bad_log_fall_back(self):
        self.assertFalse(self.restore(run_update={"conclusion": "failure"})[0])
        self.assertFalse(self.restore(archive=b"not zip")[0])
        self.assertFalse(self.restore(log_fails=True)[0])

    def test_changed_commit_tree_skips_artifact_lookup_and_download(self):
        reused, pdf, calls, commands = self.restore(tree="e" * 40)
        self.assertFalse(reused)
        self.assertIsNone(pdf)
        self.assertEqual(calls, 2)
        self.assertEqual(commands, [])

    def test_changed_source_tree_falls_back(self):
        changed = {**self.expected, "tree": "e" * 40}
        self.assertFalse(self.restore(archive=self.archive(identity=changed))[0])

    def test_lookup_failure_emits_rebuild_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            with (
                patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}),
                patch(
                    "sys.argv",
                    [
                        "verified_build.py",
                        "restore",
                        "--book",
                        "linear-algebra",
                        "--image",
                        self.expected["image"],
                    ],
                ),
                patch.object(BUILD, "identity", return_value=self.expected),
                patch.object(
                    BUILD, "restore", side_effect=subprocess.CalledProcessError(1, "gh")
                ),
            ):
                BUILD.main()
            self.assertEqual(output.read_text(), "reused=false\n")

    def test_candidate_reuse_checks_identity_attempt_and_log(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2"}),
            patch.object(
                BUILD,
                "command",
                side_effect=lambda *args: (
                    b"b" * 40
                    if args[0] == "git"
                    else subprocess.check_output(args, cwd=ROOT)
                ),
            ),
        ):
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            files = {
                **self.files,
                "book.log": b"Output written on book.pdf (1 page, 100 bytes).\n",
            }
            for name, data in files.items():
                (source / name).write_bytes(data)
            expected = BUILD.identity(
                "linear-algebra", "sha256:" + "a" * 64, candidate=True
            )
            archive = root / "candidate.zip"
            BUILD.record_candidate(expected, source, archive)
            target = root / "target"
            self.assertTrue(BUILD.restore_candidate(expected, target, archive))
            self.assertEqual((target / "book.pdf").read_bytes(), self.files["book.pdf"])

            for key in ("tree", "image_id", "policy", "book", "platform"):
                with (
                    self.subTest(key=key),
                    self.assertRaisesRegex(ValueError, "identity differs"),
                ):
                    BUILD.restore_candidate(
                        {**expected, key: "changed"}, target, archive
                    )
            with (
                patch.dict(os.environ, {"GITHUB_RUN_ATTEMPT": "3"}),
                self.assertRaisesRegex(ValueError, "different run"),
            ):
                BUILD.restore_candidate(expected, target, archive)
            with (
                patch.object(
                    BUILD,
                    "command",
                    side_effect=subprocess.CalledProcessError(1, "check-log"),
                ),
                self.assertRaises(subprocess.CalledProcessError),
            ):
                BUILD.restore_candidate(expected, target, archive)

    def test_missing_candidate_emits_rebuild_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            with (
                patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}),
                patch(
                    "sys.argv",
                    [
                        "verified_build.py",
                        "restore-candidate",
                        "--book",
                        "linear-algebra",
                        "--image",
                        "sha256:" + "a" * 64,
                        "--candidate-directory",
                        str(root),
                    ],
                ),
                patch.object(BUILD, "command", return_value=b"b" * 40),
            ):
                BUILD.main()
            self.assertEqual(output.read_text(), "reused=false\n")

    def test_record_requires_strict_log_check(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(
                BUILD,
                "command",
                side_effect=subprocess.CalledProcessError(1, "check-log"),
            ),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                BUILD.record(self.expected, Path(temporary))
            self.assertFalse((Path(temporary) / "verified-build.json").exists())

    def test_record_round_trip(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(
                os.environ,
                {
                    "GITHUB_RUN_ID": "123",
                    "GITHUB_RUN_ATTEMPT": "2",
                },
            ),
            patch.object(BUILD, "command", return_value=b""),
        ):
            directory = Path(temporary)
            for name, data in self.files.items():
                (directory / name).write_bytes(data)
            BUILD.record(self.expected, directory)
            manifest = json.loads((directory / "verified-build.json").read_text())
            self.assertEqual(manifest["tree"], self.expected["tree"])
            self.assertEqual(
                manifest["checksums"]["book.pdf"],
                BUILD.checksum(self.files["book.pdf"]),
            )


if __name__ == "__main__":
    unittest.main()
