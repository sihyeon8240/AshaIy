"""Scoped source reuse must never hide edits from a later check."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.source_reads import read_text, read_yaml, reuse_source_reads


class SourceReadTests(unittest.TestCase):
    def test_reuses_text_and_yaml_only_inside_one_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.yml"
            path.write_text("value: first\n")
            original = Path.read_text
            with patch.object(
                Path, "read_text", autospec=True, side_effect=original
            ) as reader:
                with reuse_source_reads():
                    self.assertEqual(read_text(path), "value: first\n")
                    self.assertEqual(read_yaml(path), {"value": "first"})
                    self.assertEqual(read_yaml(path), {"value": "first"})
                self.assertEqual(reader.call_count, 1)
                path.write_text("value: second\n")
                with reuse_source_reads():
                    self.assertEqual(read_yaml(path), {"value": "second"})
                self.assertEqual(reader.call_count, 2)

    def test_failed_checks_discard_their_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.tex"
            path.write_text("first\n")
            with self.assertRaises(ValueError):
                with reuse_source_reads():
                    read_text(path)
                    raise ValueError("failed check")
            path.write_text("second\n")
            self.assertEqual(read_text(path), "second\n")
