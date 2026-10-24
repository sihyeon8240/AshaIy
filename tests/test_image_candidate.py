"""Candidate provenance, archive integrity, and conservative promotion fallback."""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import image_candidate as CANDIDATE

ROOT = Path(__file__).resolve().parent.parent


class ImageCandidateTests(unittest.TestCase):
    def setUp(self):
        self.expected = {
            "policy": CANDIDATE.POLICY,
            "tree": "tree",
            "arch": "amd64",
            "image_tag": "texlive-0123456789ab",
        }
        self.workflow_run = {
            "id": 123,
            "run_attempt": 2,
            "event": "pull_request",
            "status": "completed",
            "conclusion": "success",
            "head_sha": "head",
            "head_repository": {"full_name": "owner/repo"},
            "path": ".github/workflows/build.yml",
        }
        self.manifest = {
            **self.expected,
            "run_id": "123",
            "run_attempt": "2",
            "image_id": "sha256:" + "a" * 64,
            "checksum": "unused",
        }
        self.pull = {
            "number": 7,
            "merged_at": "today",
            "merge_commit_sha": "merge",
            "base": {"ref": "main"},
            "head": {"sha": "head", "repo": {"full_name": "owner/repo"}},
        }
        self.artifacts = [
            {
                "id": number,
                "name": f"toolchain-image-{arch}",
                "expired": False,
                "size_in_bytes": 100,
            }
            for number, arch in enumerate(("amd64", "arm64"), 1)
        ]

    def test_required_source_gate_rejects_failed_candidate(self):
        import yaml

        workflow = yaml.safe_load((ROOT / ".github/workflows/build.yml").read_text())
        job = workflow["jobs"]["image-validation"]
        self.assertEqual(
            job["permissions"],
            {"contents": "read", "actions": "read", "packages": "read"},
        )
        self.assertIn("needs.source.outputs.image_changed == 'true'", job["if"])
        gate = workflow["jobs"]["check"]
        self.assertIn("image-validation", gate["needs"])
        for image_result in ("success", "skipped", "failure", "cancelled"):
            with self.subTest(image_result=image_result):
                result = subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", gate["steps"][0]["run"]],
                    env={
                        **os.environ,
                        "SOURCE_RESULT": "success",
                        "LATEX_RESULT": "success",
                        "IMAGE_RESULT": image_result,
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(
                    result.returncode == 0, image_result in ("success", "skipped")
                )

    def test_rejects_unsuccessful_foreign_or_unrelated_runs(self):
        self.assertTrue(CANDIDATE.eligible_run(self.workflow_run, "owner/repo", "head"))
        for key, value in (
            ("event", "push"),
            ("status", "in_progress"),
            ("conclusion", "failure"),
            ("head_sha", "old"),
            ("head_repository", {"full_name": "fork/repo"}),
            ("path", ".github/workflows/build-image.yml"),
        ):
            with self.subTest(key=key):
                self.assertFalse(
                    CANDIDATE.eligible_run(
                        {**self.workflow_run, key: value}, "owner/repo", "head"
                    )
                )

    def test_manifest_binds_tree_architecture_policy_and_run_attempt(self):
        CANDIDATE.validate_manifest(self.manifest, self.expected, self.workflow_run)
        for key in (*self.expected, "run_id", "run_attempt", "image_id"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                CANDIDATE.validate_manifest(
                    {**self.manifest, key: "wrong"}, self.expected, self.workflow_run
                )

    def restore(self, *, pull=None, tree="tree", run=None, artifacts=None):
        responses = [
            [self.pull if pull is None else pull],
            {"tree": {"sha": tree}},
            {"workflow_runs": [self.workflow_run if run is None else run]},
            {"artifacts": self.artifacts if artifacts is None else artifacts},
        ]
        with (
            patch.dict(
                os.environ, {"GITHUB_REPOSITORY": "owner/repo", "GITHUB_SHA": "merge"}
            ),
            patch.object(CANDIDATE, "identity", return_value=self.expected),
            patch.object(CANDIDATE, "api", side_effect=responses),
            patch.object(CANDIDATE, "load_candidate") as load,
        ):
            result = CANDIDATE.restore("amd64", "target")
            return result, load.call_count

    def test_matching_successful_candidate_is_loaded(self):
        self.assertEqual(self.restore(), (True, 1))

    def test_fork_wrong_merge_or_base_never_downloads(self):
        for pull in (
            {**self.pull, "head": {"repo": {"full_name": "fork/repo"}}},
            {**self.pull, "merged_at": None},
            {**self.pull, "merge_commit_sha": "other"},
            {**self.pull, "base": {"ref": "other"}},
        ):
            self.assertEqual(self.restore(pull=pull), (False, 0))

    def test_github_tree_mismatch_never_downloads(self):
        self.assertEqual(self.restore(tree="other"), (False, 0))

    def test_failed_run_or_missing_expired_architecture_rebuilds(self):
        self.assertEqual(
            self.restore(run={**self.workflow_run, "conclusion": "failure"}), (False, 0)
        )
        self.assertEqual(self.restore(artifacts=self.artifacts[:1]), (False, 0))
        expired = [self.artifacts[0], {**self.artifacts[1], "expired": True}]
        self.assertEqual(self.restore(artifacts=expired), (False, 0))

    def test_expanded_image_limit_is_checked_before_docker_access(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "image.gz"
            archive.write_bytes(gzip.compress(b"x" * 100))
            with (
                patch.object(CANDIDATE, "MAX_IMAGE_BYTES", 10),
                patch.object(CANDIDATE, "command") as command,
                self.assertRaisesRegex(
                    ValueError, "expanded Docker image is too large"
                ),
            ):
                CANDIDATE.check_archive(archive)
            command.assert_not_called()

    def test_invalid_candidate_archive_is_rejected_before_recording_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "image.tar.gz").write_bytes(b"")
            with (
                patch.object(CANDIDATE, "command") as command,
                self.assertRaisesRegex(ValueError, "empty or too large"),
            ):
                CANDIDATE.record("amd64", "image", directory)
            command.assert_not_called()

    def test_archive_is_verified_before_loading_or_tagging(self):
        for failure in (
            None,
            "github_digest",
            "checksum",
            "tree",
            "files",
            "architecture",
        ):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                image = root / "image.tar.gz"
                image.write_bytes(gzip.compress(b"image bytes"))
                manifest = {**self.manifest, "checksum": CANDIDATE.checksum(image)}
                if failure == "checksum":
                    manifest["checksum"] = "wrong"
                if failure == "tree":
                    manifest["tree"] = "wrong"
                archive_path = root / "source.zip"
                with zipfile.ZipFile(archive_path, "w") as archive:
                    archive.writestr("candidate.json", json.dumps(manifest))
                    archive.write(image, "image.tar.gz")
                    if failure == "files":
                        archive.writestr("../script.sh", "exit 0")
                artifact = {
                    "expired": False,
                    "size_in_bytes": archive_path.stat().st_size,
                    "id": 1,
                    "digest": "sha256:" + CANDIDATE.checksum(archive_path),
                }
                if failure == "github_digest":
                    artifact["digest"] = "wrong"

                def transfer(args, target, *unused):
                    target.write_bytes(archive_path.read_bytes())

                with (
                    patch.object(CANDIDATE.subprocess, "run") as run,
                    patch.object(
                        CANDIDATE.github_artifacts,
                        "download_attempt",
                        side_effect=transfer,
                    ),
                    patch.object(
                        CANDIDATE,
                        "command",
                        side_effect=lambda *args: (
                            str(root)
                            if args[:2] == ("docker", "info")
                            else ("arm64" if failure == "architecture" else "amd64")
                        ),
                    ) as command,
                ):
                    if failure:
                        with self.assertRaises(ValueError):
                            CANDIDATE.load_candidate(
                                "owner/repo",
                                artifact,
                                self.expected,
                                self.workflow_run,
                                "target",
                            )
                    else:
                        CANDIDATE.load_candidate(
                            "owner/repo",
                            artifact,
                            self.expected,
                            self.workflow_run,
                            "target",
                        )
                    loaded = any(
                        call.args[0][0] == "docker" for call in run.call_args_list
                    )
                    self.assertEqual(loaded, failure in (None, "architecture"))
                    tagged = any(
                        call.args[:2] == ("docker", "tag")
                        for call in command.call_args_list
                    )
                    self.assertEqual(tagged, failure is None)


if __name__ == "__main__":
    unittest.main()
