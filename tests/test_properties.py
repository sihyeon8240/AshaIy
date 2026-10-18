"""Generated edge cases for parsing and canonical book metadata."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.database import DirectoryBasedExampleDatabase
from test_support import book_record, manifest_document

from scripts.book_manifest import normalize_manifest, version_key
from scripts.latex_scan import braced_argument, has_balanced_braces, without_comments

settings.register_profile(
    "repository",
    max_examples=150,
    deadline=None,
    database=DirectoryBasedExampleDatabase(
        Path(__file__).resolve().parent.parent / ".cache/hypothesis/examples"
    ),
)
settings.load_profile("repository")

TEX_TEXT = st.text(alphabet="abc XYZ012%\n한글", max_size=30)
BALANCED_TEX = st.recursive(
    st.one_of(TEX_TEXT, st.sampled_from([r"\{", r"\}", r"\\", r"\%"])),
    lambda children: st.lists(children, max_size=5).map(
        lambda parts: "{" + "".join(parts) + "}"
    ),
    max_leaves=20,
)
VERSION = st.tuples(*(st.integers(min_value=0, max_value=10000) for _ in range(3)))


class CorePropertyTests(unittest.TestCase):
    @given(BALANCED_TEX)
    def test_braced_arguments_preserve_nested_and_escaped_content(self, content):
        source = " \n{" + content + "}trailing"
        argument, end = braced_argument(source, 0)
        self.assertEqual(argument, content)
        self.assertEqual(source[end:], "trailing")
        self.assertTrue(has_balanced_braces(content))
        with self.assertRaises(ValueError):
            braced_argument(source[: end - 1], 0)

    @given(st.text(alphabet="ab%\\{}\r\n한글", max_size=300))
    def test_comment_removal_preserves_source_positions(self, source):
        clean = without_comments(source)
        self.assertEqual(len(clean), len(source))
        self.assertEqual(without_comments(clean), clean)
        for original, scanned in zip(source, clean, strict=True):
            if original in "\r\n":
                self.assertEqual(scanned, original)
            else:
                self.assertIn(scanned, (original, " "))

    @given(VERSION, VERSION)
    def test_release_versions_follow_numeric_precedence(self, first, second):
        left = version_key(".".join(map(str, first)))
        right = version_key(".".join(map(str, second)))
        self.assertEqual(left < right, first < second)
        self.assertEqual(left == right, first == second)

    @given(
        st.lists(st.integers(min_value=0, max_value=100), max_size=15),
        st.booleans(),
        st.booleans(),
    )
    def test_manifest_normalization_is_stable_and_preserves_overrides(
        self, orders, default_check, override_check
    ):
        records = [
            book_record(
                f"book-{index}",
                label_prefix=f"b{index}",
                order=order,
                **({"check": override_check} if index % 2 else {}),
            )
            for index, order in enumerate(orders)
        ]
        source = manifest_document(records, check=default_check)
        original = copy.deepcopy(source)
        normalized = normalize_manifest(source)
        self.assertEqual(source, original)
        self.assertEqual(normalize_manifest(normalized), normalized)
        self.assertEqual(
            [book["slug"] for book in normalized["books"]],
            [
                book["slug"]
                for book in sorted(records, key=lambda b: (b["order"], b["slug"]))
            ],
        )
        actual = {book["slug"]: book["check"] for book in normalized["books"]}
        self.assertEqual(
            actual,
            {book["slug"]: book.get("check", default_check) for book in records},
        )
