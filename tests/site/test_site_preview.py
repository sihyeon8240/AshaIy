"""Local preview PDF selection, tool requirements, and Make command routing."""

from __future__ import annotations

import contextlib
import os
import queue
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from scripts.site import site_preview as preview

ROOT = Path(__file__).resolve().parents[2]


class SitePreviewTests(unittest.TestCase):
    def test_preview_serves_files_on_the_selected_interface(self) -> None:
        for host in ("127.0.0.1", "0.0.0.0"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "index.html").write_text("preview response", encoding="utf-8")
                ready = queue.Queue()

                def create_server(address, handler):
                    server = ThreadingHTTPServer(address, handler)
                    ready.put(server)
                    return server

                with mock.patch.object(
                    preview, "ThreadingHTTPServer", side_effect=create_server
                ):
                    worker = threading.Thread(
                        target=preview.serve, args=(root, 0, host), daemon=True
                    )
                    worker.start()
                    server = ready.get(timeout=5)
                    try:
                        self.assertEqual(server.server_address[0], host)
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{server.server_port}/", timeout=5
                        ) as response:
                            self.assertEqual(response.read(), b"preview response")
                    finally:
                        server.shutdown()
                        worker.join(timeout=5)
                    self.assertFalse(worker.is_alive())

    def test_build_failures_preserve_the_previous_complete_preview(self):
        for failure in ("render", "copy", "validate", "install"):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                destination = root / "build/site-preview"
                (destination / "pdf").mkdir(parents=True)
                (destination / "index.html").write_text("previous preview")
                (destination / "pdf/alpha.pdf").write_bytes(b"previous PDF")
                source = root / "build/alpha/book.pdf"
                source.parent.mkdir()
                source.write_bytes(b"%PDF-1.7\nnew PDF")
                replace = os.replace

                def fail_install(source, target):
                    if Path(source).name == "next":
                        raise OSError("installation failed")
                    return replace(source, target)

                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(preview, "ROOT", root))
                    stack.enter_context(
                        mock.patch.object(
                            preview, "require_tool", return_value="jekyll"
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(
                            preview,
                            "load_manifest",
                            return_value={"books": [{"slug": "alpha", "site": True}]},
                        )
                    )
                    stack.enter_context(mock.patch.object(preview.subprocess, "run"))
                    stack.enter_context(mock.patch.object(preview, "check_output"))
                    if failure == "render":
                        stack.enter_context(
                            mock.patch.object(
                                preview, "render", side_effect=OSError("render failed")
                            )
                        )
                    elif failure == "copy":
                        stack.enter_context(
                            mock.patch.object(
                                preview.shutil,
                                "copyfile",
                                side_effect=OSError("copy failed"),
                            )
                        )
                    elif failure == "validate":
                        stack.enter_context(
                            mock.patch.object(
                                preview,
                                "check_output",
                                side_effect=ValueError("validation failed"),
                            )
                        )
                    else:
                        stack.enter_context(
                            mock.patch.object(
                                preview.os, "replace", side_effect=fail_install
                            )
                        )
                    with self.assertRaises((ValueError, OSError)):
                        preview.build()
                self.assertEqual(
                    (destination / "index.html").read_text(), "previous preview"
                )
                self.assertEqual(
                    (destination / "pdf/alpha.pdf").read_bytes(), b"previous PDF"
                )
                self.assertEqual(list((root / "build").glob(".site-preview-*")), [])

    def test_missing_tool_fails_before_tests_can_skip(self) -> None:
        with (
            mock.patch.object(preview.shutil, "which", return_value=None),
            self.assertRaisesRegex(ValueError, "required tool not found: jekyll"),
        ):
            preview.test()

    def test_missing_and_empty_pdfs_leave_existing_site_intact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "build/site-preview/index.html"
            output.parent.mkdir(parents=True)
            output.write_text("previous preview")
            pdf = root / "build/alpha/book.pdf"
            pdf.parent.mkdir(parents=True)
            books = {"books": [{"slug": "alpha", "site": True}]}
            with (
                mock.patch.object(preview, "ROOT", root),
                mock.patch.object(preview, "require_tool", return_value="jekyll"),
                mock.patch.object(preview, "load_manifest", return_value=books),
                mock.patch.object(preview.subprocess, "run") as run,
            ):
                for empty in (False, True):
                    if empty:
                        pdf.touch()
                    with self.assertRaisesRegex(
                        ValueError, "ashaiy book build --book alpha"
                    ):
                        preview.build()
                    self.assertEqual(output.read_text(), "previous preview")
                run.assert_not_called()

    def test_build_stages_only_site_books_and_removes_stale_pdfs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "build/site-preview/pdf"
            output.mkdir(parents=True)
            (output / "old.pdf").write_bytes(b"old")
            pdf = root / "build/alpha/book.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"local PDF")
            books = {
                "books": [
                    {"slug": "alpha", "site": True},
                    {"slug": "beta", "site": False},
                ]
            }
            with (
                mock.patch.object(preview, "ROOT", root),
                mock.patch.object(preview, "require_tool", return_value="jekyll"),
                mock.patch.object(preview, "load_manifest", return_value=books),
                mock.patch.object(preview.subprocess, "run"),
                mock.patch.object(preview, "check_output"),
            ):
                preview.build()
            self.assertEqual([path.name for path in output.iterdir()], ["alpha.pdf"])
            self.assertEqual((output / "alpha.pdf").read_bytes(), pdf.read_bytes())
