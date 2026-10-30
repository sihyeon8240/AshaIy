"""Regression tests for manifest-owned Lean aggregation."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.lean import lean_generation as GENERATOR
from scripts.lean.lean_manifest import expected_files
from tests.support.fixtures import book_record, manifest_document, write_yaml

ROOT = Path(__file__).resolve().parents[2]


class LeanManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.write_yaml(
            "config/books.yml",
            manifest_document(
                [
                    book_record(version="0.1.0", label_prefix="sa", lean_module="Sample"),
                    book_record(
                        "empty",
                        version="0.1.0",
                        label_prefix="em",
                        lean_module="Empty",
                        order=20,
                    ),
                ]
            ),
        )
        for slug in ("sample", "empty"):
            self.write_yaml(
                f"books/{slug}/chapters.yml",
                {
                    "schema_version": 1,
                    "chapters": [
                        {"slug": "first", "title": "First", "lean_namespace": "First"},
                        {
                            "slug": "second",
                            "title": "Second",
                            "lean_namespace": "Second",
                        },
                    ],
                    "appendices": [
                        {
                            "slug": "background",
                            "title": "Background",
                            "lean_namespace": "Background",
                        }
                    ],
                },
            )
            (self.root / "books" / slug / "book.tex").touch()
        self.topic("First", "VectorSpaces")
        self.topic("First", "Bases")
        self.manifest("First", ["VectorSpaces", "Bases"])

    def write_yaml(self, name: str, data: object) -> None:
        write_yaml(self.root / name, data)

    def topic(self, chapter: str, name: str) -> Path:
        path = self.root / "lean/Textbooks/Sample" / chapter / f"{name}.lean"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("-- Mathematical source\n", encoding="utf-8")
        return path

    def manifest(self, chapter: str, modules: object) -> None:
        self.write_yaml(
            f"lean/Textbooks/Sample/{chapter}/modules.yml",
            {"schema_version": 1, "modules": modules},
        )

    def test_reading_order_chapters_appendices_and_empty_book(self) -> None:
        self.topic("Second", "Matrices")
        self.manifest("Second", ["Matrices"])
        self.topic("Appendices/Background", "Background")
        self.manifest("Appendices/Background", ["Background"])
        outputs = expected_files(self.root)
        text = outputs[self.root / "lean/Textbooks/Sample/All.lean"]
        imports = [line for line in text.splitlines() if line.startswith("import ")]
        self.assertEqual(
            imports,
            [
                "import Textbooks.Sample.First.VectorSpaces",
                "import Textbooks.Sample.First.Bases",
                "import Textbooks.Sample.Second.Matrices",
                "import Textbooks.Sample.Appendices.Background.Background",
            ],
        )
        self.assertNotIn("import ", outputs[self.root / "lean/Textbooks/Empty/All.lean"])
        self.assertIn("import Textbooks.Empty.All", outputs[self.root / "lean/Textbooks.lean"])

    def test_invalid_module_lists(self) -> None:
        for modules, diagnostic in [
            (["Bases", "Bases"], "duplicate module"),
            (["Missing"], "declared Lean source is missing"),
            (["../Bases"], "invalid topic name"),
            (["01-Bases"], "invalid topic name"),
            (["All"], "invalid topic name"),
            ([None], "invalid topic name"),
            ("Bases", "modules must be a list"),
        ]:
            with self.subTest(modules=modules):
                self.manifest("First", modules)
                with self.assertRaisesRegex(ValueError, diagnostic):
                    expected_files(self.root)

    def test_missing_manifest(self) -> None:
        (self.root / "lean/Textbooks/Sample/First/modules.yml").unlink()
        with self.assertRaisesRegex(ValueError, "cannot read YAML"):
            expected_files(self.root)

    def test_reordering_chapters_preserves_module_paths(self) -> None:
        self.topic("Second", "Matrices")
        self.manifest("Second", ["Matrices"])
        target = self.root / "lean/Textbooks/Sample/All.lean"
        before = expected_files(self.root)[target]
        path = self.root / "books/sample/chapters.yml"
        data = yaml.safe_load(path.read_text())
        data["chapters"].reverse()
        write_yaml(path, data)
        after = expected_files(self.root)[target]
        self.assertEqual(set(before.splitlines()), set(after.splitlines()))
        self.assertLess(after.index("Sample.Second."), after.index("Sample.First."))

    def test_invalid_and_duplicate_namespaces(self) -> None:
        path = self.root / "books/sample/chapters.yml"
        original = path.read_text()
        for namespace in (
            None,
            "../First",
            "lowercase",
            "All",
            "Appendices",
            "Chapter01",
            "Second",
        ):
            with self.subTest(namespace=namespace):
                data = yaml.safe_load(original)
                data["chapters"][0]["lean_namespace"] = namespace
                write_yaml(path, data)
                with self.assertRaisesRegex(ValueError, "lean_namespace"):
                    expected_files(self.root)

    def test_missing_namespace_leaves_sources_unregistered(self) -> None:
        path = self.root / "books/sample/chapters.yml"
        data = yaml.safe_load(path.read_text())
        del data["chapters"][0]["lean_namespace"]
        write_yaml(path, data)
        with self.assertRaisesRegex(ValueError, "unregistered Lean source"):
            expected_files(self.root)

    def test_unregistered_source(self) -> None:
        self.topic("First", "Forgotten")
        with self.assertRaisesRegex(ValueError, "Forgotten.lean.*unregistered"):
            expected_files(self.root)

    def test_chapter_outside_contents(self) -> None:
        self.manifest("Third", [])
        with self.assertRaisesRegex(ValueError, "Third/modules.yml.*unregistered"):
            expected_files(self.root)

    def test_unregistered_book(self) -> None:
        self.write_yaml(
            "lean/Textbooks/Unknown/First/modules.yml",
            {"schema_version": 1, "modules": []},
        )
        with self.assertRaisesRegex(ValueError, "unregistered Lean book"):
            expected_files(self.root)

    def test_schema_validation(self) -> None:
        for data in (
            [],
            {"schema_version": True, "modules": []},
            {"schema_version": 2, "modules": []},
            {"schema_version": 1, "modules": [], "extra": []},
        ):
            with self.subTest(data=data):
                self.write_yaml("lean/Textbooks/Sample/First/modules.yml", data)
                with self.assertRaises(ValueError):
                    expected_files(self.root)

    def test_check_is_read_only_and_generation_is_idempotent(self) -> None:
        target = self.root / "lean/Textbooks/Sample/All.lean"
        target.write_text("old assembly\n", encoding="utf-8")
        source = self.root / "lean/Textbooks/Sample/First/Bases.lean"
        original = source.read_bytes()
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(GENERATOR.generate(root=self.root, check=True), 1)
            self.assertEqual(target.read_text(), "old assembly\n")
            self.assertEqual(GENERATOR.generate(root=self.root), 0)
            timestamp = target.stat().st_mtime_ns
            self.assertEqual(GENERATOR.generate(root=self.root), 0)
            self.assertEqual(target.stat().st_mtime_ns, timestamp)
            self.assertEqual(GENERATOR.generate(root=self.root, check=True), 0)
        self.assertEqual(source.read_bytes(), original)

    def test_selection_preserves_other_book_and_complete_root(self) -> None:
        outputs = expected_files(self.root, "sample")
        self.assertNotIn(self.root / "lean/Textbooks/Empty/All.lean", outputs)
        self.assertIn("Textbooks.Empty.All", outputs[self.root / "lean/Textbooks.lean"])
        with self.assertRaisesRegex(ValueError, "book is not registered"):
            expected_files(self.root, "unknown")


if __name__ == "__main__":
    unittest.main()
