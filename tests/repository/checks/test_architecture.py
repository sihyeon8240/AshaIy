"""Regression tests for architecture policy validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

from scripts.repository.checks import architecture_checks as MODULE
from tests.support.fixtures import book_record, manifest_document, write_yaml

ROOT = Path(__file__).resolve().parents[3]


class ArchitectureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.book = self.root / "books/sample"
        chapter = self.book / "chapters/start"
        front = self.book / "overrides"
        chapter.mkdir(parents=True)
        front.mkdir()
        (self.root / "docs").mkdir()
        (self.root / "docs" / "ARCHITECTURE.md").write_text(
            "contract\n", encoding="utf-8"
        )
        self.write_manifest()
        self.entry(
            r"\addbibresource{references.bib}"
            "\n"
            r"\include{overrides/cover}"
            "\n"
            r"\include{overrides/preface}"
            "\n"
            r"\include{chapters/start/index}"
            "\n"
            r"\nocite{*}"
            "\n"
        )
        (chapter / "index.tex").write_text(
            r"\chapter{Start}" "\n" r"\input{section}" "\n",
            encoding="utf-8",
        )
        (chapter / "section.tex").write_text(r"\section{One}" "\n", encoding="utf-8")
        (self.book / "chapters.yml").write_text(
            "schema_version: 1\nchapters:\n  - slug: start\n    title: Start\n",
            encoding="utf-8",
        )
        (chapter / "sections.yml").write_text(
            "schema_version: 1\nsections:\n  - slug: section\n    title: One\n",
            encoding="utf-8",
        )
        (self.book / "references.bib").write_text(
            "@book{one, title={One}}\n", encoding="utf-8"
        )
        (front / "cover.tex").write_text(
            r"\input{cover}" "\n",
            encoding="utf-8",
        )
        (front / "preface.tex").write_text(
            r"\input{preface}" "\n",
            encoding="utf-8",
        )

    def write_manifest(self, **book_overrides: Any) -> None:
        book = book_record(**book_overrides)
        write_yaml(
            self.root / "config/books.yml",
            manifest_document([book], author="Sample Author"),
        )

    def entry(self, text: str) -> None:
        (self.book / "book.tex").write_text(text, encoding="utf-8")

    def findings(self):
        return MODULE.validate_repository(self.root)

    def assert_error(self, fragment: str) -> None:
        errors = self.findings().errors
        self.assertTrue(any(fragment in error for error in errors), "\n".join(errors))

    def add_chapter(self, name: str, title: str = "Next") -> None:
        chapter = self.book / "chapters" / name
        chapter.mkdir()
        (chapter / "index.tex").write_text(
            rf"\chapter{{{title}}}" + "\n" + r"\input{placeholder}" + "\n",
            encoding="utf-8",
        )
        (chapter / "placeholder.tex").write_text("body\n", encoding="utf-8")
        manifest_path = self.book / "chapters.yml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["chapters"].append({"slug": name, "title": title})
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        (chapter / "sections.yml").write_text(
            "schema_version: 1\nsections:\n  - slug: placeholder\n    title: Placeholder\n",
            encoding="utf-8",
        )

    def rename_first_chapter(self, name: str) -> None:
        old = self.book / "chapters/start"
        old.rename(self.book / "chapters" / name)
        entry = (self.book / "book.tex").read_text(encoding="utf-8")
        self.entry(entry.replace("chapters/start", f"chapters/{name}"))

    def restore_first_chapter(self, name: str) -> None:
        current = self.book / "chapters" / name
        current.rename(self.book / "chapters/start")
        entry = (self.book / "book.tex").read_text(encoding="utf-8")
        self.entry(entry.replace(f"chapters/{name}", "chapters/start"))

    def test_minimal_fixture_complies(self) -> None:
        self.assertEqual(self.findings().errors, [])

    def test_invalid_chapter_name_characters_are_errors(self) -> None:
        for name in ("01-Start", "vector_spaces", "vector--spaces"):
            with self.subTest(name=name):
                self.rename_first_chapter(name)
                self.assert_error("chapter directory name must match")
                self.restore_first_chapter(name)

    def test_directory_must_match_manifest_slug(self) -> None:
        self.rename_first_chapter("renamed")
        self.assert_error("chapter includes do not match canonical chapters.yml")

    def test_duplicate_chapter_slug_is_error(self) -> None:
        path = self.book / "chapters.yml"
        data = yaml.safe_load(path.read_text())
        data["chapters"].append(data["chapters"][0])
        write_yaml(path, data)
        self.assert_error("duplicate chapter slug")

    def test_reversed_chapter_include_order_is_error(self) -> None:
        self.add_chapter("next")
        self.entry(
            r"\addbibresource{references.bib}"
            "\n"
            r"\include{chapters/next/index}"
            "\n"
            r"\include{chapters/start/index}"
            "\n"
            r"\nocite{*}"
            "\n"
        )
        self.assert_error("chapter includes do not match canonical chapters.yml")

    def test_manifest_validation_error_is_reported(self) -> None:
        self.write_manifest(unexpected_field="value")
        self.assert_error("unknown field(s): unexpected_field")

    def test_orphan_section_is_error(self) -> None:
        (self.book / "chapters/start/orphan.tex").write_text("", encoding="utf-8")
        self.assert_error("orphan section file")

    def test_orphan_chapter_directory_is_error(self) -> None:
        self.add_chapter("orphan", "Orphan")
        self.assert_error("orphan chapter directory")

    def test_chapter_target_must_be_index(self) -> None:
        self.entry(
            r"\addbibresource{references.bib}"
            "\n"
            r"\include{chapters/start/section}"
            "\n"
        )
        self.assert_error("chapter target is not index.tex")

    def test_chapter_requires_exactly_one_declaration(self) -> None:
        (self.book / "chapters/start/index.tex").write_text(
            r"\chapter{One}"
            "\n"
            r"\chapter{Two}"
            "\n"
            r"\input{section}"
            "\n",
            encoding="utf-8",
        )
        self.assert_error("expected one chapter declaration")

    def test_missing_required_bibliography_is_error(self) -> None:
        (self.book / "references.bib").unlink()
        self.assert_error("required bibliography is missing")

    def test_missing_configured_bibliography_is_error(self) -> None:
        self.entry(
            r"\addbibresource{missing.bib}"
            "\n"
            r"\include{chapters/start/index}"
            "\n"
        )
        self.assert_error("configured bibliography does not exist")

    def test_duplicate_bibliography_key_is_error(self) -> None:
        (self.book / "second.bib").write_text(
            "@book{one, title={Again}}\n", encoding="utf-8"
        )
        self.entry(
            r"\addbibresource{references.bib}"
            "\n"
            r"\addbibresource{second.bib}"
            "\n"
            r"\include{chapters/start/index}"
            "\n"
        )
        self.assert_error("duplicate bibliography key 'one'")

    def set_sections(
        self, filenames: list[str], inputs: list[str] | None = None
    ) -> None:
        chapter = self.book / "chapters/start"
        for path in chapter.glob("*.tex"):
            if path.name != "index.tex":
                path.unlink()
        for filename in filenames:
            (chapter / filename).write_text("body\n", encoding="utf-8")
        targets = inputs if inputs is not None else filenames
        lines = [r"\chapter{Start}"] + [rf"\input{{{target}}}" for target in targets]
        (chapter / "index.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
        findings = MODULE.Findings()
        MODULE.parse_section_sources(
            [chapter / filename for filename in filenames], chapter.name, findings
        )
        if not findings.errors:
            sections = []
            for filename in filenames:
                slug = Path(filename).stem
                item = {"slug": slug, "title": slug.replace("-", " ").title()}
                sections.append(item)
            (chapter / "sections.yml").write_text(
                yaml.safe_dump(
                    {"schema_version": 1, "sections": sections}, sort_keys=False
                ),
                encoding="utf-8",
            )

    def test_generated_appendix_paths_pass_architecture_checks(self) -> None:
        appendix = self.book / "appendices/tables"
        appendix.mkdir(parents=True)
        manifest = self.book / "chapters.yml"
        manifest.write_text(
            manifest.read_text() + "appendices:\n  - slug: tables\n    title: Tables\n"
        )
        (appendix / "sections.yml").write_text(
            "schema_version: 1\nsections:\n  - slug: values\n    title: Values\n"
        )
        source = appendix / "values.tex"
        source.write_text("Body.\n")
        entry = self.book / "book.tex"
        entry.write_text(
            entry.read_text() + "\\appendix\n\\include{appendices/tables/index}\n"
        )
        (appendix / "index.tex").write_text(
            "\\chapter{Tables}\n\\section{Values}\n"
            "\\input{appendices/tables/values.tex}\n"
        )
        self.assertEqual(self.findings().errors, [])
        source.unlink()
        self.assert_error("target does not exist")

    def test_manifest_order_can_differ_from_filename_order(self) -> None:
        self.set_sections(["third.tex", "first.tex"])
        self.assertEqual(self.findings().errors, [])

    def test_logical_sections_must_be_in_manifest_order(self) -> None:
        self.set_sections(["first.tex", "second.tex"], ["second", "first"])
        self.assert_error(
            "section inputs do not match the canonical sections.yml order"
        )

    def test_missing_orphan_and_duplicate_inputs_are_errors(self) -> None:
        cases = [
            (
                ["topic.tex", "other.tex"],
                ["topic"],
                "orphan section file",
            ),
            (
                ["topic.tex", "other.tex"],
                ["topic", "other", "missing-c"],
                "target does not exist",
            ),
            (
                ["topic.tex", "other.tex"],
                ["topic", "topic", "other"],
                "duplicate include/input target",
            ),
        ]
        for files, inputs, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic):
                self.set_sections(files, inputs)
                self.assert_error(diagnostic)

    def test_invalid_section_filename_forms_are_errors(self) -> None:
        invalid_names = (
            "topic-A.tex",
            "topic--name.tex",
            "1-topic.tex",
            "section-part-2.tex",
        )
        for filename in invalid_names:
            with self.subTest(filename=filename):
                self.set_sections([filename])
                self.assertTrue(self.findings().errors)


if __name__ == "__main__":
    unittest.main()
