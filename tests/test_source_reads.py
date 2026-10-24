"""Scoped source reuse must never hide edits from a later check."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.contents_manifest import load_sections
from scripts.json_config import parse_json
from scripts.source_reads import parse_yaml, read_text, read_yaml, reuse_source_reads


class SourceReadTests(unittest.TestCase):
    def test_json_rejects_ambiguous_keys_and_nonstandard_constants(self) -> None:
        for text in (
            '{"schema_version": 2, "schema_version": 1}',
            '{"nested": {"enabled": true, "enabled": false}}',
            '{"value": NaN}',
            '{"value": Infinity}',
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_json(text)

    def test_domain_loaders_share_the_invocation_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / "sections.yml"
            first = "schema_version: 1\nsections:\n- slug: one\n  title: First\n"
            path.write_text(first)
            with reuse_source_reads():
                self.assertEqual(load_sections(directory)[0]["title"], "First")
                path.write_text(first.replace("First", "Second"))
                self.assertEqual(load_sections(directory)[0]["title"], "First")
            self.assertEqual(load_sections(directory)[0]["title"], "Second")

    def test_duplicate_keys_and_merges_fail_with_source_positions(self) -> None:
        for source in (
            "book:\n  release: false\n  release: true\n",
            "base: &base {release: false}\nbook: {<<: *base}\n",
        ):
            with (
                self.subTest(source=source),
                self.assertRaises(yaml.YAMLError) as caught,
            ):
                parse_yaml(source)
            self.assertIn("line", str(caught.exception))
        self.assertEqual(
            parse_yaml("first: &value [1, 2]\nsecond: *value\n"),
            {"first": [1, 2], "second": [1, 2]},
        )

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
