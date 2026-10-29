"""Artifact transfer retries, bounded stalls, and integrity enforcement."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ci import github_artifacts as artifacts


class ArtifactDownloadTests(unittest.TestCase):
    def test_retry_discards_partial_response_and_verifies_complete_digest(self):
        data = b"complete archive"
        artifact = {
            "id": 1,
            "expired": False,
            "size_in_bytes": len(data),
            "digest": "sha256:" + artifacts.checksum(data),
        }
        attempts = []

        def transfer(args, target, *unused):
            attempts.append(target.exists())
            target.write_bytes(b"partial" if len(attempts) == 1 else data)
            if len(attempts) == 1:
                raise subprocess.TimeoutExpired(args, 120)

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.zip"
            with patch.object(artifacts, "download_attempt", side_effect=transfer):
                artifacts.download("owner/repo", artifact, target, max_bytes=100)
            self.assertEqual(attempts, [False, False])
            self.assertEqual(target.read_bytes(), data)
            with (
                patch.object(artifacts, "download_attempt", side_effect=transfer),
                self.assertRaisesRegex(ValueError, "digest mismatch"),
            ):
                artifacts.download("owner/repo", {**artifact, "digest": "wrong"}, target, max_bytes=100)
            self.assertFalse(target.exists())

    def test_large_archives_receive_a_bounded_size_dependent_budget(self):
        self.assertEqual(artifacts.download_timeout(0), 600)
        self.assertGreater(artifacts.download_timeout(8 * 1024**3), 14 * 60)
        self.assertEqual(artifacts.download_timeout(100 * 1024**3), 3600)

    def test_insufficient_disk_space_stops_before_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(artifacts.shutil, "disk_usage") as usage,
                patch.object(artifacts, "download_attempt") as transfer,
                self.assertRaisesRegex(ValueError, "insufficient disk space"),
            ):
                usage.return_value.free = 0
                artifacts.download(
                    "owner/repo",
                    {
                        "id": 1,
                        "expired": False,
                        "size_in_bytes": 100,
                    },
                    Path(temporary) / "archive",
                    max_bytes=100,
                )
            transfer.assert_not_called()

    def test_stalled_process_is_killed_and_progress_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.zip"
            output = io.StringIO()
            with (
                patch.object(artifacts, "DOWNLOAD_IDLE_TIMEOUT", 0.15),
                patch.object(artifacts, "DOWNLOAD_POLL_INTERVAL", 0.05),
                patch.object(artifacts, "DOWNLOAD_LOG_INTERVAL", 0),
                contextlib.redirect_stdout(output),
                self.assertRaises(subprocess.TimeoutExpired),
            ):
                artifacts.download_attempt(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    target,
                    10,
                    100,
                    artifacts.time.monotonic() + 5,
                    "test artifact",
                )
            self.assertIn("MiB/s", output.getvalue())
            self.assertIn("without progress", output.getvalue())

    def test_size_limit_is_enforced_during_transfer(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            self.assertRaisesRegex(ValueError, "too large"),
        ):
            artifacts.download_attempt(
                [sys.executable, "-c", "import sys; sys.stdout.write('x' * 100)"],
                Path(temporary) / "artifact.zip",
                10,
                10,
                artifacts.time.monotonic() + 5,
                "test artifact",
            )
