"""Macro ownership, generation, normalization, and editor synchronization."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.latex.macro_generation import (
    BOOK_GENERATED_NAME,
    COMMON_GENERATED_NAME,
    MacroRepository,
    generate,
)
from scripts.latex.macro_manifest import load_macros
from scripts.latex.normalize_braces import normalize_braces
from tests.support.fixtures import (
    book_record,
    copy_file,
    copy_script,
    manifest_document,
    write_yaml,
)

ROOT = Path(__file__).resolve().parents[2]
MATH = {"kind": "mandatory", "mode": "math"}


class MacroManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.shared = {
            "R": {
                "kind": "command",
                "arguments": [],
                "body": r"\mathbb{R}",
                "script_atom": True,
            },
            "Abs": {"kind": "paired_delimiter", "left": r"\lvert", "right": r"\rvert"},
            "Inner": {
                "kind": "paired_delimiter_x",
                "arguments": [MATH, MATH],
                "left": r"\langle",
                "right": r"\rangle",
                "body": "#1,#2",
            },
            "Eval": {
                "kind": "paired_delimiter_x",
                "arguments": [MATH, MATH, MATH],
                "left": ".",
                "right": r"\rvert",
                "body": "#1",
                "after": "_{#2}^{#3}",
            },
            "WithDefault": {
                "kind": "command",
                "arguments": [
                    {"kind": "optional", "mode": "math", "default": "z"},
                    MATH,
                ],
                "body": "#1+#2",
            },
            "Offset": {"kind": "command", "arguments": [MATH], "body": "#1+1"},
            "Mixed": {
                "kind": "command",
                "arguments": [
                    MATH,
                    {"kind": "mandatory", "mode": "text"},
                    {"kind": "mandatory", "mode": "opaque"},
                ],
                "body": "#1#2#3",
            },
        }
        write_yaml(
            self.root / "config/books.yml",
            manifest_document([book_record("alpha"), book_record("beta")]),
        )
        for slug in ("alpha", "beta"):
            source = self.root / "books" / slug / "book.tex"
            source.parent.mkdir(parents=True)
            source.write_text("Fixture.\n")
        self.write_shared()
        self.write_book("alpha", 1)
        self.write_book("beta", 2)
        self.generate()

    def write_shared(self) -> None:
        write_yaml(
            self.root / "common/styles/macros.yml",
            {"schema_version": 1, "macros": self.shared},
        )

    def write_book(self, slug: str, count: int) -> None:
        write_yaml(
            self.root / "books" / slug / "styles/macros.yml",
            {
                "schema_version": 1,
                "macros": {
                    "Local": {
                        "kind": "command",
                        "arguments": [MATH] * count,
                        "body": "+".join(f"#{index}" for index in range(1, count + 1)),
                    }
                },
            },
        )

    def generate(self, **options) -> int:
        with redirect_stdout(io.StringIO()):
            return generate(root=self.root, **options)

    def test_generation_is_idempotent_scoped_and_check_is_read_only(self) -> None:
        targets = sorted(self.root.rglob("generated*-macros.sty"))
        originals = {
            path: (path.read_bytes(), path.stat().st_mtime_ns) for path in targets
        }
        self.assertEqual(self.generate(check=True), 0)
        self.assertEqual(self.generate(), 0)
        self.assertEqual(
            {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in targets},
            originals,
        )
        self.write_book("beta", 3)
        self.assertEqual(self.generate(book="alpha", check=True), 0)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.generate(check=True), 1)
        self.assertEqual(
            {path: path.read_bytes() for path in targets},
            {path: value[0] for path, value in originals.items()},
        )
        self.generate(book="beta")
        self.assertEqual(self.generate(check=True), 0)

    def test_scope_and_argument_modes_control_normalization(self) -> None:
        repository = MacroRepository(self.root)
        alpha = repository.for_source(self.root / "books/alpha/draft.tex")
        beta = repository.for_source(self.root / "books/beta/draft.tex")
        shared = repository.for_source(self.root / "common/templates/draft.tex")
        self.assertEqual(
            normalize_braces(r"$\Local xy$", alpha.commands), r"$\Local{x}y$"
        )
        self.assertEqual(
            normalize_braces(r"$\Local xy$", beta.commands), r"$\Local{x}{y}$"
        )
        self.assertEqual(
            normalize_braces(r"$\Local xy$", shared.commands), r"$\Local xy$"
        )
        examples = {
            r"$x_\R + \Abs*x + \Abs[\Big]x + \Inner xy$": r"$x_{\R} + \Abs*{x} + \Abs[\Big]{x} + \Inner{x}{y}$",
            r"$\WithDefault{x} + \WithDefault[a_i]x$": r"$\WithDefault{x} + \WithDefault[a_{i}]{x}$",
            r"$\Mixed{x_i}{file_name $a^2$}{$x^2$}$": r"$\Mixed{x_{i}}{file_name $a^{2}$}{$x^2$}$",
            r"$x_\Offset a$": r"$x_\Offset{a}$",
            r"$\Abs*[\Big]x$": r"$\Abs*[\Big]x$",
            r"$\Eval*{x^2}{a_i}{b^2}$": r"$\Eval*{x^{2}}{a_{i}}{b^{2}}$",
            r"$\Eval[\Big]xab$": r"$\Eval[\Big]{x}{a}{b}$",
            r"\newcommand\R[1]{$#1^2$}": r"\newcommand\R[1]{$#1^2$}",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(normalize_braces(source, alpha.commands), expected)
                self.assertEqual(normalize_braces(expected, alpha.commands), expected)

    def test_invalid_declarations_fail_before_any_package_is_written(self) -> None:
        invalid = [
            {"kind": "command", "arguments": [MATH], "body": "#2"},
            {"kind": "command", "arguments": [MATH], "body": "{"},
            {"kind": "command", "arguments": [MATH] * 10, "body": "#1"},
            {
                "kind": "command",
                "arguments": [
                    MATH,
                    {"kind": "optional", "mode": "math", "default": "x"},
                ],
                "body": "#1",
            },
            {
                "kind": "command",
                "arguments": [{"kind": "mandatory", "mode": []}],
                "body": "#1",
            },
            {"kind": "command", "arguments": [], "body": "x", "context": []},
            {"kind": "command", "arguments": [], "body": "x", "script_atom": 1},
            {"kind": "operator", "text": "f", "unknown": True},
            *[
                {
                    "kind": "paired_delimiter_x",
                    "arguments": [MATH],
                    "left": ".",
                    "right": r"\rvert",
                    "body": "#1",
                    "after": after,
                }
                for after in ("#2", "{", 1)
            ],
            {"kind": "raw", "body": "anything"},
        ]
        targets = sorted(self.root.rglob("generated*-macros.sty"))
        originals = {path: path.read_bytes() for path in targets}
        self.shared["R"]["body"] = r"\mathbf{R}"
        self.write_shared()
        for entry in invalid:
            with self.subTest(entry=entry):
                write_yaml(
                    self.root / "books/beta/styles/macros.yml",
                    {"schema_version": 1, "macros": {"Broken": entry}},
                )
                with self.assertRaises(ValueError):
                    self.generate()
                self.assertEqual(
                    {path: path.read_bytes() for path in targets}, originals
                )

    def test_duplicate_names_reserved_names_and_owners_are_rejected(self) -> None:
        path = self.root / "books/alpha/styles/macros.yml"
        for name in (
            "R",
            "Gamma",
            "DeclarePairedDelimiterXPP",
            "lowercase",
            "Bad_name",
        ):
            with self.subTest(name=name):
                write_yaml(
                    path,
                    {
                        "schema_version": 1,
                        "macros": {
                            name: {"kind": "command", "arguments": [], "body": "x"}
                        },
                    },
                )
                with self.assertRaises(ValueError):
                    self.generate()
        path.write_text(
            "schema_version: 1\nmacros:\n  A: {kind: operator, text: a}\n  A: {kind: operator, text: b}\n"
        )
        with self.assertRaisesRegex(ValueError, r"macros.yml:4:"):
            load_macros(path)
        self.write_book("alpha", 1)
        path.unlink()
        with self.assertRaisesRegex(ValueError, "no macros.yml owner"):
            self.generate()

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_editor_uses_buffer_and_original_book_and_rejects_stale_packages(
        self,
    ) -> None:
        self.prepare_formatter()
        original = self.root / "books/alpha/draft with spaces.tex"
        original.write_text("Unchanged disk buffer.\n")
        temporary = original.with_name("__latexindent_temp_" + original.name)
        temporary.write_text(r"$\Local xy + x_\R$" + "\n")
        result = self.run_format("--stdout", str(temporary))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(r"$\Local{x}y + x_{\R}$", result.stdout)
        self.assertEqual(original.read_text(), "Unchanged disk buffer.\n")
        external = self.root / "external.tex"
        external.write_text(temporary.read_text())
        explicit = self.run_format("--stdout", str(external), "--source", str(original))
        self.assertEqual(explicit.stdout, result.stdout)
        self.shared["R"]["body"] = r"\mathbf{R}"
        self.write_shared()
        failed = self.run_format("--stdout", str(temporary))
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(failed.stdout, "")
        self.assertIn("macros generate", failed.stderr)
        self.assertEqual(original.read_text(), "Unchanged disk buffer.\n")

    def prepare_formatter(self) -> None:
        copy_script(
            ROOT / "scripts/latex/format_tex.py",
            self.root / "scripts/latex/format_tex.py",
        )
        copy_file(
            ROOT / "config/latexindent.yaml", self.root / "config/latexindent.yaml"
        )
        self.write_shared()
        self.generate()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, timeout=30)

    def run_format(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.root / "scripts/latex/format_tex.py"),
                *arguments,
            ],
            cwd=self.root,
            env={**os.environ, "FORMAT_TEX_CACHE_DIR": str(self.root / ".cache/tex")},
            capture_output=True,
            text=True,
            timeout=30,
        )

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_cache_observes_macro_changes_without_affecting_other_books(self) -> None:
        self.prepare_formatter()
        source = self.root / "books/alpha/draft.tex"
        source.write_text(r"$\Local xy$" + "\n")
        self.assertEqual(self.run_format("--file", str(source)).returncode, 0)
        cached = self.run_format("--file", str(source), "--check")
        self.assertEqual(cached.returncode, 0, cached.stderr)
        self.assertIn("1 cached", cached.stdout)
        self.write_book("beta", 3)
        still_cached = self.run_format("--file", str(source), "--check")
        self.assertEqual(still_cached.returncode, 0, still_cached.stderr)
        self.assertIn("1 cached", still_cached.stdout)
        self.write_book("alpha", 2)
        self.generate()
        original = source.read_bytes()
        changed = self.run_format("--file", str(source), "--check")
        self.assertEqual(changed.returncode, 1, changed.stderr)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(self.run_format("--file", str(source)).returncode, 0)
        self.assertIn(r"\Local{x}{y}", source.read_text())
        generated = self.root / "common/styles" / COMMON_GENERATED_NAME
        before = generated.read_bytes()
        unchanged = self.run_format("--file", str(generated))
        self.assertEqual(unchanged.returncode, 0, unchanged.stderr)
        self.assertEqual(generated.read_bytes(), before)

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_bulk_preflight_preserves_all_sources_when_one_book_is_stale(self) -> None:
        self.prepare_formatter()
        sources = [
            self.root / "books" / slug / "draft.tex" for slug in ("alpha", "beta")
        ]
        for source in sources:
            source.write_text(r"$x^2 + \Local xy$" + "\n")
        subprocess.run(
            ["git", "add", *map(str, sources)], cwd=self.root, check=True, timeout=30
        )
        originals = [source.read_bytes() for source in sources]
        self.write_book("beta", 3)
        result = self.run_format()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([source.read_bytes() for source in sources], originals)

    def test_cli_generation_checks_selected_book_without_rewriting_others(self) -> None:
        shutil.copytree(
            ROOT / "scripts",
            self.root / "scripts",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        copy_file(
            ROOT / "config/validation-patterns.json",
            self.root / "config/validation-patterns.json",
        )
        self.write_book("alpha", 2)
        self.write_book("beta", 3)
        beta = self.root / "books/beta/styles" / BOOK_GENERATED_NAME
        original = beta.read_bytes()
        command = [sys.executable, str(self.root / "scripts/ashaiy"), "macros"]
        generated = subprocess.run(
            [*command, "generate", "--book", "alpha"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        checked = subprocess.run(
            [*command, "check", "--book", "alpha"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        all_books = subprocess.run(
            [*command, "check"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(all_books.returncode, 1, all_books.stderr)
        self.assertEqual(beta.read_bytes(), original)

    @unittest.skipUnless(shutil.which("lualatex"), "lualatex is required")
    def test_generated_declarations_preserve_native_tex_and_script_binding(
        self,
    ) -> None:
        self.shared["TestOp"] = {"kind": "operator", "text": "Op", "limits": True}
        self.shared["Commented"] = {
            "kind": "command",
            "arguments": [MATH],
            "body": "#1 % preserve trailing comment",
        }
        self.write_shared()
        self.generate()
        commands = MacroRepository(self.root).registry("alpha").commands
        local_package = Path(BOOK_GENERATED_NAME).stem
        lines = [
            r"\documentclass{article}",
            r"\usepackage{amsmath,amssymb,mathtools,generated-common-macros}",
            rf"\usepackage{{styles/{local_package}}}",
            r"\DeclarePairedDelimiter{\OldAbs}{\lvert}{\rvert}",
            r"\DeclarePairedDelimiterX{\OldInner}[2]{\langle}{\rangle}{#1,#2}",
            r"\newcommand{\OldWithDefault}[2][z]{#1+#2}",
            r"\newcommand{\OldOffset}[1]{#1+1}",
            r"\DeclareMathOperator*{\OldOp}{Op}",
            r"\begin{document}",
        ]
        examples = [
            (r"X_\mathbb{R}", r"X_\R"),
            (r"\OldAbs x", r"\Abs x"),
            (r"\OldAbs*{\frac12}", r"\Abs*{\frac12}"),
            (r"\OldAbs[\Big]x", r"\Abs[\Big]x"),
            (r"\OldInner xy", r"\Inner xy"),
            (r"x\rvert_a^b", r"\Eval xab"),
            (r"x\rvert_{a_i}^{b^2}", r"\Eval{x}{a_i}{b^2}"),
            (r"x\rvert_a", r"\Eval{x}{a}{}"),
            (
                r"\mathopen{\Bigl.}x\mathclose{\Bigr\rvert}_a^b",
                r"\Eval[\Big]xab",
            ),
            (
                r"\mathopen{}\mathclose{\left.\frac{x^2}{2}\right\rvert}_a^b",
                r"\Eval*{\frac{x^2}{2}}{a}{b}",
            ),
            (
                r"\mathopen{}\mathclose{\left.x\right\rvert}_{\frac12}^{\frac34}",
                r"\Eval*{x}{\frac12}{\frac34}",
            ),
            (r"\OldWithDefault x", r"\WithDefault x"),
            (r"\OldWithDefault[2]x", r"\WithDefault[2]x"),
            (r"X_\OldOffset a", r"X_\Offset a"),
            (r"\OldOp_n", r"\TestOp_n"),
            (r"x", r"\Commented x"),
            (r"x", r"\Local x"),
        ]
        for index, (legacy, source) in enumerate(examples):
            formatted = normalize_braces("$" + source + "$", commands)
            lines.extend(
                [
                    r"\setbox0=\hbox{$" + legacy + "$}",
                    r"\setbox1=\hbox{" + formatted + "}",
                    *[
                        rf"\ifdim\{dimension}0=\{dimension}1\else"
                        rf"\errmessage{{Changed macro {index}: {dimension}}}\fi"
                        for dimension in ("wd", "ht", "dp")
                    ],
                ]
            )
        lines.append(r"\end{document}")
        source = self.root / "macros.tex"
        source.write_text("\n".join(lines) + "\n")
        result = subprocess.run(
            ["lualatex", "-interaction=nonstopmode", "-halt-on-error", str(source)],
            cwd=self.root / "books/alpha",
            env={**os.environ, "TEXINPUTS": str(self.root / "common/styles") + "//:"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("You have requested package", result.stdout)


if __name__ == "__main__":
    unittest.main()
