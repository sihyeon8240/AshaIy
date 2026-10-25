"""Tests for declarative contents loading and LaTeX generation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.books.contents_manifest import (
    expected_files,
    load_sections,
    render_metadata,
    section_filenames,
)
from tests.support.fixtures import copy_file


class ContentsManifestTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("lualatex"), "lualatex is required")
    def test_plain_registry_text_compiles_with_tex_special_characters(self) -> None:
        record = {
            **self.RECORD,
            "title": r"Probability & Statistics 100% #1_{x} $5 ~ ^ \ naïve",
            "author": "A & B",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tex = root / "metadata.tex"
            tex.write_text(
                "\\documentclass{article}\n\\usepackage{hyperref}\n"
                + render_metadata(record)
                + "\n\\begin{document}\\displaytitle\\quad\\name\\end{document}\n"
            )
            result = subprocess.run(
                ["lualatex", "-interaction=nonstopmode", "-halt-on-error", str(tex)],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((root / "metadata.pdf").read_bytes().startswith(b"%PDF-"))

    def test_percent_sign_requires_escape_in_latex_titles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            path = book / "chapters/start/sections.yml"
            path.write_text(
                "schema_version: 1\nsections:\n- slug: first\n  title: 100% complete\n"
            )
            with self.assertRaisesRegex(ValueError, "unescaped percent"):
                load_sections(path.parent)
            path.write_text(path.read_text().replace("100%", r"100\%"))
            self.assertEqual(load_sections(path.parent)[0]["title"], r"100\% complete")

    RECORD = {
        "slug": "sample",
        "title": "Sample Book",
        "author": "Sample Author",
        "version": "1.2.3",
    }

    def fixture(self, root: Path) -> Path:
        book = root / "book"
        chapter = book / "chapters/start"
        chapter.mkdir(parents=True)
        (book / "chapters.yml").write_text(
            "schema_version: 1\nchapters:\n  - slug: start\n    title: Start\n",
            encoding="utf-8",
        )
        (chapter / "sections.yml").write_text(
            "schema_version: 1\nsections:\n  - slug: first\n    title: First\n",
            encoding="utf-8",
        )
        (book / "book.tex").write_text(
            "before\n% BEGIN GENERATED METADATA\nold metadata\n"
            "% END GENERATED METADATA\n% BEGIN GENERATED CHAPTERS\nold\n"
            "% END GENERATED CHAPTERS\n\\backmatter\n"
            "% BEGIN GENERATED APPENDICES\nold appendix\n"
            "% END GENERATED APPENDICES\nafter\n",
            encoding="utf-8",
        )
        (chapter / "first.tex").write_text("body\n", encoding="utf-8")
        return book

    def test_render_and_validation_share_section_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            reads = []
            original = Path.read_text

            def tracked(path, *args, **kwargs):
                if path.name == "sections.yml":
                    reads.append(path)
                return original(path, *args, **kwargs)

            with patch.object(Path, "read_text", tracked):
                rendered = expected_files(book, book=self.RECORD)
            self.assertEqual(reads, [book / "chapters/start/sections.yml"])
            self.assertIn(
                "\\section{First}", rendered[book / "chapters/start/index.tex"]
            )

    def test_render_uses_manifest_titles_and_single_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            rendered = expected_files(book, book=self.RECORD)
            self.assertIn(
                r"\include{chapters/start/index}", rendered[book / "book.tex"]
            )
            self.assertNotIn(r"\appendix", rendered[book / "book.tex"])
            index = rendered[book / "chapters/start/index.tex"]
            self.assertIn(r"\chapter{Start}", index)
            self.assertEqual(index.count(r"\section{First}"), 1)
            self.assertEqual(index.count(r"\input{"), 1)
            self.assertIn("first.tex", index)

    def test_generator_initializes_proof_indexes_without_overwriting(self) -> None:
        repository = Path(__file__).resolve().parents[2]
        from scripts.books import contents_generation as generator

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            book = self.fixture(root)
            (root / "books").mkdir()
            book = book.rename(root / "books/sample")
            manifest = book / "chapters.yml"
            manifest.write_text(
                manifest.read_text()
                + "appendices:\n  - slug: tables\n    title: Tables\n"
            )
            appendix = book / "appendices/tables"
            appendix.mkdir(parents=True)
            (appendix / "sections.yml").write_text(
                "schema_version: 1\nsections:\n  - slug: values\n    title: Values\n"
            )
            (appendix / "values.tex").write_text("body\n")
            template = root / "common/templates/proofs.yml"
            template.parent.mkdir(parents=True)
            copy_file(repository / "common/templates/proofs.yml", template)
            indexes = [book / "chapters/start/proofs.yml", appendix / "proofs.yml"]
            with (
                patch.object(generator, "ROOT", root),
                patch.object(
                    generator, "load_manifest", return_value={"books": [self.RECORD]}
                ),
            ):
                self.assertEqual(generator.generate("all", check=True), 1)
                self.assertTrue(all(not path.exists() for path in indexes))
                self.assertEqual(generator.generate("all"), 0)
                for path in indexes:
                    self.assertEqual(path.read_text(), "proofs: []\n")
                entries = "proofs:\n  - id: sa:thm:result\n    declaration: Sample.Start.result\n"
                indexes[0].write_text(entries)
                self.assertEqual(generator.generate("all"), 0)
                self.assertEqual(generator.generate("all", check=True), 0)
                self.assertEqual(indexes[0].read_text(), entries)

    def test_metadata_is_rendered_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book_dir = self.fixture(Path(temporary))
            entry = expected_files(book_dir, book=self.RECORD)[book_dir / "book.tex"]

            self.assertIn(r"\newcommand{\name}{Sample Author}", entry)
            self.assertIn(r"\newcommand{\displaytitle}{Sample Book}", entry)
            self.assertIn(r"\newcommand{\version}{1.2.3}", entry)
            self.assertIn(r"\newcommand{\slug}{sample}", entry)

    def test_appendices_render_before_backmatter_with_appendix_numbering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            appendix = book / "appendices/tables"
            appendix.mkdir(parents=True)
            (book / "chapters.yml").write_text(
                (book / "chapters.yml").read_text()
                + "appendices:\n  - slug: tables\n    title: Tables\n"
            )
            (appendix / "sections.yml").write_text(
                "schema_version: 1\nsections:\n  - slug: values\n    title: Values\n"
            )
            (appendix / "values.tex").write_text("body\n")

            rendered = expected_files(book, book=self.RECORD)
            entry = rendered[book / "book.tex"]
            self.assertLess(entry.index(r"\appendix"), entry.index("appendices/tables"))
            self.assertLess(
                entry.index("appendices/tables"), entry.index(r"\backmatter")
            )
            index = rendered[appendix / "index.tex"]
            self.assertIn("chapter{Tables}", index)
            self.assertIn("appendices/tables/values.tex", index)

    @unittest.skipUnless(
        all(shutil.which(tool) for tool in ("latexmk", "lualatex", "latexminted")),
        "appendix rendering requires the supported LaTeX toolchain",
    )
    def test_rendered_appendices_reset_section_and_theorem_numbers(self) -> None:
        repository = Path(__file__).resolve().parents[2]
        output = repository / "build/appendix-check"
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            manifest = book / "chapters.yml"
            manifest.write_text(
                manifest.read_text()
                + "appendices:\n  - slug: tables\n    title: Tables\n"
                + "  - slug: details\n    title: Details\n"
            )
            body = (
                r"\begin{theorem}A rendering specimen."
                r"\typeout{APPENDIX-CHECK=\thechapter|\thesection|\thetheorem}"
                r"\end{theorem}" + "\n"
            )
            (book / "chapters/start/first.tex").write_text(body)
            for name in ("tables", "details"):
                appendix = book / "appendices" / name
                appendix.mkdir(parents=True)
                (appendix / "sections.yml").write_text(
                    "schema_version: 1\nsections:\n  - slug: result\n    title: Result\n"
                )
                (appendix / "result.tex").write_text(body)
            rendered = expected_files(book, book=self.RECORD)
            for path, text in rendered.items():
                path.write_text(text)
                (output / path.parent.relative_to(book)).mkdir(
                    parents=True, exist_ok=True
                )
            entry = rendered[book / "book.tex"]
            # Exercise the generated assembly with the actual shared style.
            assembly = entry[entry.index(r"\mainmatter") : entry.index(r"\nocite")]
            (book / "book.tex").write_text(
                "\\documentclass[oneside]{book}\n\\usepackage{textbook}\n"
                "\\begin{document}\n" + assembly + "\\end{document}\n"
            )
            result = subprocess.run(
                [
                    "latexmk",
                    "-r",
                    str(repository / "config/latexmkrc"),
                    f"-outdir={output}",
                    "book.tex",
                ],
                cwd=book,
                env={**os.environ, "TEXINPUTS": f"{repository}/common/styles//:"},
                capture_output=True,
                text=True,
                timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        log = output / "book.log"
        checked = subprocess.run(
            [
                sys.executable,
                str(repository / "scripts/latex/check_log.py"),
                "--strict",
                str(log),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        for number in ("1|1.1|1.1.1", "A|A.1|A.1.1", "B|B.1|B.1.1"):
            self.assertIn("APPENDIX-CHECK=" + number, log.read_text())

    def test_existing_entry_contents_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            path = book / "book.tex"
            path.write_text("hand-edited entry\n", encoding="utf-8")
            rendered = expected_files(book, book=self.RECORD)[path]
            self.assertNotIn("hand-edited entry", rendered)
            self.assertTrue(rendered.startswith("% Generated from"))

    def test_one_filename_per_section(self) -> None:
        self.assertEqual(section_filenames({"slug": "topic"}), ["topic.tex"])

    def test_apostrophe_section_slug_and_reserved_assembly_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            chapter = book / "chapters/start"
            path = chapter / "sections.yml"
            original = path.read_text()
            path.write_text(original.replace("slug: first", "slug: wilson's-theorem"))
            (chapter / "first.tex").rename(chapter / "wilson's-theorem.tex")
            rendered = expected_files(book, book=self.RECORD)
            self.assertIn("wilson's-theorem.tex", rendered[chapter / "index.tex"])
            path.write_text(original.replace("slug: first", "slug: index"))
            with self.assertRaisesRegex(ValueError, "reserved"):
                load_sections(chapter)

    def test_split_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            path = book / "chapters/start/sections.yml"
            path.write_text(path.read_text() + "    split: 2\n")
            with self.assertRaisesRegex(ValueError, "unknown field.*split"):
                load_sections(path.parent)

    def test_titles_must_be_single_line_with_balanced_braces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            path = book / "chapters/start/sections.yml"
            original = path.read_text()
            for title in ("Broken } title", r'"two\nlines"'):
                with self.subTest(title=title):
                    path.write_text(original.replace("title: First", f"title: {title}"))
                    with self.assertRaisesRegex(ValueError, "balanced single-line"):
                        load_sections(path.parent)

    def test_non_string_contents_fields_have_located_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            manifest = book / "chapters/start/sections.yml"
            for source in (
                "schema_version: 1\n7: wrong\nsections: []\n",
                "schema_version: 1\nsections:\n- slug: first\n  title: First\n  7: wrong\n",
            ):
                manifest.write_text(source)
                with self.assertRaisesRegex(
                    ValueError, "sections.yml.*field names must be strings"
                ):
                    load_sections(manifest.parent)

    def test_orphan_section_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            orphan = book / "chapters/start/orphan.tex"
            orphan.write_text("body\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "orphan section source"):
                expected_files(book, book=self.RECORD)

    def test_manual_chapter_and_section_declarations_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            source = book / "chapters/start/first.tex"
            for command, manifest in (
                ("chapter", "chapters.yml"),
                ("section", "sections.yml"),
            ):
                for suffix in ("{Wrong}", "*{Wrong}", "[Short]{Wrong}"):
                    with self.subTest(command=command, suffix=suffix):
                        source.write_text(f"\\{command}{suffix}\n", encoding="utf-8")
                        with self.assertRaisesRegex(
                            ValueError, rf"{command} declarations belong in {manifest}"
                        ):
                            expected_files(book, book=self.RECORD)

    def test_literal_and_escaped_sectioning_commands_are_allowed(self) -> None:
        examples = [
            r"\verb|\section{sample}|",
            r"\verb*+\chapter{sample}+",
            "\n".join((r"\begin{verbatim}", r"\chapter{sample}", r"\end{verbatim}")),
            "\n".join(
                (r"\begin{lean}", r'def note := "\\section{sample}"', r"\end{lean}")
            ),
            r"First\\section{sample}",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            source = book / "chapters/start/first.tex"
            for example in examples:
                with self.subTest(example=example):
                    source.write_text(example + "\n")
                    rendered = expected_files(book, book=self.RECORD)
                    self.assertIn(source.name, rendered[source.parent / "index.tex"])

    def test_commented_chapter_and_section_declarations_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            book = self.fixture(Path(temporary))
            source = book / "chapters/start/first.tex"
            source.write_text(
                "% \\chapter{Comment}\n% \\section{Comment}\nbody\n",
                encoding="utf-8",
            )
            expected_files(book, book=self.RECORD)


if __name__ == "__main__":
    unittest.main()
