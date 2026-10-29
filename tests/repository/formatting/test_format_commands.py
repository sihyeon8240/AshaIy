"""Formatter argument handling and source preservation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.support.fixtures import copy_script, write_executable

ROOT = Path(__file__).resolve().parents[3]


class SingleFileFormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "scripts").mkdir(exist_ok=True)
        (self.root / "config/generated").mkdir(parents=True)
        for path in [
            "config/authoring.json",
            "config/latexindent.yaml",
            "config/pyproject.toml",
            "scripts/repository/config/repository_config.py",
            "scripts/cli/repository_cli.py",
            "scripts/cli/repository_tasks.py",
            "scripts/cli/task_stages.py",
            "scripts/repository/source_reads.py",
            "scripts/repository/formatting/format_code.py",
            "scripts/latex/format_tex.py",
            "scripts/latex/format_tex_file.sh",
            "scripts/repository/formatting/normalize_eof.py",
        ]:
            copy_script(ROOT / path, self.root / path)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, timeout=30)

    def run_format(
        self, language: str, path: str, check: bool = False
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "scripts/cli/repository_cli.py",
                "format",
                language,
                *(["--check"] if check else []),
                "--file",
                path,
            ],
            cwd=self.root,
            env={**os.environ, "FORMAT_TEX_CACHE_DIR": str(self.root / ".cache/tex")},
            capture_output=True,
            text=True,
            timeout=30,
        )

    @unittest.skipUnless(
        all(shutil.which(tool) for tool in ("ruff", "shfmt", "latexindent")),
        "ruff, shfmt, and latexindent are required",
    )
    def test_untracked_files_with_spaces_match_editor_formatting(self) -> None:
        fixtures = [
            ("py", "ruff", ".py", "value=  1\n\n\n"),
            ("sh", "shfmt", ".sh", "#!/usr/bin/env bash\nif true;then echo ok;fi\n\n"),
            ("tex", "latexindent", ".tex", "\\begin{proof} A fact.\n\\end{proof}\n\n"),
        ]
        for language, tool, suffix, source in fixtures:
            with self.subTest(language=language):
                path = self.root / ("draft $(touch sentinel) `touch sentinel`" + suffix)
                path.write_text(source)
                untouched = self.root / ("other" + suffix)
                untouched.write_text(source)
                check = self.run_format(language, path.name, check=True)
                self.assertNotEqual(check.returncode, 0)
                self.assertEqual(path.read_text(), source)
                if language == "py":
                    self.assertRegex(check.stdout, "draft .*\\.py:\\d+:\\d+: .+")
                formatted = self.run_format(language, path.name)
                self.assertEqual(formatted.returncode, 0, formatted.stderr)
                self.assertNotEqual(path.read_text(), source)
                self.assertEqual(untouched.read_text(), source)
                self.assertFalse((self.root / "sentinel").exists())
                checked = self.run_format(language, str(path), check=True)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                if language == "tex":
                    editor = subprocess.run(
                        [
                            str(self.root / "scripts/latex/format_tex_file.sh"),
                            str(path),
                        ],
                        cwd=self.root,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(editor.stdout, path.read_text())

    def test_invalid_paths_are_rejected_without_modifying_files(self) -> None:
        (self.root / ".gitignore").write_text("ignored.*\n")
        for language, suffix in [("py", ".py"), ("sh", ".sh"), ("tex", ".tex")]:
            ignored = self.root / ("ignored" + suffix)
            ignored.write_text("unchanged\n")
            outside = self.root.parent / (self.root.name + suffix)
            outside.write_text("unchanged\n")
            self.addCleanup(outside.unlink)
            for path in [
                "missing" + suffix,
                ignored.name,
                str(outside),
                "config/authoring.json",
            ]:
                with self.subTest(language=language, path=path):
                    result = self.run_format(language, path)
                    self.assertNotEqual(result.returncode, 0)
            self.assertEqual(ignored.read_text(), "unchanged\n")
            self.assertEqual(outside.read_text(), "unchanged\n")
        result = self.run_format("all", "config/authoring.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("single format scope", result.stderr)


class FormatTexTests(unittest.TestCase):
    def prepare_formatter(self, root: Path) -> Path:
        scripts = root / "scripts"
        scripts.mkdir()
        (root / "config").mkdir()
        copy_script(ROOT / "config/latexindent.yaml", root / "config/latexindent.yaml")
        for name in (
            "latex/format_tex.py",
            "latex/format_tex_file.sh",
            "repository/formatting/normalize_eof.py",
        ):
            copy_script(ROOT / "scripts" / name, scripts / name)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
        return scripts

    def run_formatter(
        self, root: Path, *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(root / "scripts/latex/format_tex.py"), *arguments],
            cwd=root,
            env={**os.environ, "FORMAT_TEX_CACHE_DIR": str(root / "cache")},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_editor_and_cli_brace_math_arguments_and_preserve_literals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = self.prepare_formatter(root)
            path = root / "arguments.tex"
            literal = r"\verb|x^2 \frac12|"
            source = "$\\int_0^1 \\frac12 x^2$ " + literal + "\n"
            path.write_text(source)
            subprocess.run(
                ["git", "add", "arguments.tex"], cwd=root, check=True, timeout=30
            )
            editor = subprocess.run(
                [str(scripts / "latex/format_tex_file.sh"), str(path)],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(editor.returncode, 0, editor.stderr)
            self.assertIn(r"$\int_{0}^{1} \frac{1}{2} x^{2}$", editor.stdout)
            self.assertIn(literal, editor.stdout)
            self.assertEqual(path.read_text(), source)
            checked = self.run_formatter(root, "--check")
            self.assertEqual(checked.returncode, 1, checked.stderr)
            formatted = self.run_formatter(root)
            self.assertEqual(formatted.returncode, 0, formatted.stderr)
            self.assertEqual(path.read_text(), editor.stdout)
            checked = self.run_formatter(root, "--check")
            self.assertEqual(checked.returncode, 0, checked.stderr)

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_multiline_literals_keep_their_bytes_and_formatting_is_idempotent(
        self,
    ) -> None:
        blocks = [
            '\\begin{lean}\ndef ordinary := "first\n\n\n  last"\n'
            'def raw := r##"first "quoted"\n\n\n  last"##\n'
            "/- outer /- nested -/ comment -/\n\\end{lean}",
            "\\begin{verbatim}\nfirst\n\n\n  last % literal\n\\end{verbatim}",
            '\\begin{minted}{python}\nvalue = "literal"\n\n\n  tail\n\\end{minted}',
            r"\verb|% \label{literal}|",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "literals.tex"
            path.write_text(
                "\\begin{proof}\n"
                + "\n\n".join(blocks)
                + "\n\\end{proof}\n"
                + "\\begin{lemma}\\label{sample:lem:result}Result.\\end{lemma}\n"
            )
            command = [str(ROOT / "scripts/latex/format_tex_file.sh"), str(path)]
            formatted = subprocess.check_output(command, text=True, timeout=30)
            for block in blocks:
                self.assertIn(block, formatted)
            self.assertIn(r"\begin{lemma} \label{sample:lem:result}", formatted)
            path.write_text(formatted)
            self.assertEqual(
                subprocess.check_output(command, text=True, timeout=30), formatted
            )

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_preserves_manual_lines_and_aligns_equation_rows(self) -> None:
        source = (
            "\\begin{proof}\n  Keep this short line.\n  Keep this separate line.\n"
            + "  "
            + "A long explanation with several words. " * 8
            + "\n"
            + "  "
            + "Another long explanation to wrap. " * 8
            + (
                "\n"
                "  \\[\n"
                "    \\begin{aligned}\n"
                "      A + B & = (a + b) \\\\\n"
                "      cA & = (ca) \\\\\n"
                "      0 & = (0)\n"
                "    \\end{aligned}\n"
                "  \\]\n"
                "\\end{proof}\n"
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proof.tex"
            path.write_text(source)
            command = [str(ROOT / "scripts/latex/format_tex_file.sh"), str(path)]
            formatted = subprocess.check_output(command, text=True, timeout=30)
            self.assertIn(
                "  Keep this short line.\n  Keep this separate line.\n", formatted
            )
            self.assertTrue(all(len(line) <= 120 for line in formatted.splitlines()))
            rows = [line for line in formatted.splitlines() if line.endswith("\\\\")]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].index("\\\\"), rows[1].index("\\\\"))
            path.write_text(formatted)
            self.assertEqual(
                subprocess.check_output(command, text=True, timeout=30), formatted
            )

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_wraps_prose_to_120_columns_and_preserves_lean(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = self.prepare_formatter(root)
            sentence = (
                "A mathematical explanation "
                + "with enough detail to require several source lines " * 4
                + "and an inline formula $a=qb+r$."
            )
            prose = (sentence + " ") * 3
            lean = "    -- " + "Preserve this long Lean comment. " * 5 + "\n"
            source = (
                "\\begin{proof} \\label{test:proof}\n"
                + "  "
                + prose.rstrip()
                + "\n\n"
                + "  \\begin{lean}\n"
                + lean
                + "    example : True := by\n      trivial\n"
                + "  \\end{lean}\n\\end{proof}\n"
            )
            path = root / "proof.tex"
            path.write_text(source, encoding="utf-8")
            subprocess.run(
                ["git", "add", "proof.tex"], cwd=root, check=True, timeout=30
            )

            editor_result = subprocess.run(
                [str(scripts / "latex/format_tex_file.sh"), str(path)],
                cwd=scripts,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(editor_result.returncode, 0, editor_result.stderr)
            self.assertEqual(path.read_text(), source)
            result = self.run_formatter(root, "--check")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(path.read_text(), source)
            result = self.run_formatter(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            formatted = path.read_text()
            self.assertEqual(editor_result.stdout, formatted)
            paragraph = formatted.split("\n\n")[0].split("\n", 2)[2]
            self.assertEqual(" ".join(paragraph.split()), prose.strip())
            self.assertGreater(len(paragraph.splitlines()), 3)
            self.assertNotIn("\n  A mathematical explanation", paragraph)
            for line in paragraph.splitlines():
                self.assertLessEqual(len(line), 120)
                self.assertTrue(line.startswith("  "))
            self.assertIn(lean, formatted)
            shutil.rmtree(root / "cache")
            result = self.run_formatter(root, "--check")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(), formatted)
            settings = root / "config/latexindent.yaml"
            settings.write_text(
                settings.read_text().replace("columns: 120", "columns: 60")
            )
            result = self.run_formatter(root, "--check")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(path.read_text(), formatted)

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_wraps_comments_but_preserves_metadata_and_display_math(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_formatter(root)
            metadata = (
                (
                    "% !TEX root = book.tex\n"
                    "% BEGIN GENERATED APPENDICES\n"
                    "% END GENERATED APPENDICES\n"
                    "% Lean source: "
                )
                + "Textbooks.LongModule." * 8
                + "result\n%\n"
            )
            comment = "An explanatory comment " + "with useful context " * 12
            display = "  \\[\n    a=qb+r.\n  \\]\n"
            source = (
                metadata
                + "\n\\begin{proof} First sentence. Second sentence.\n% "
                + comment.strip()
                + "\n  The following identity holds:\n"
                + display
                + "\\end{proof}\n"
            )
            path = root / "proof.tex"
            path.write_text(source)
            subprocess.run(
                ["git", "add", "proof.tex"], cwd=root, check=True, timeout=30
            )

            result = self.run_formatter(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            formatted = path.read_text()
            self.assertTrue(formatted.startswith(metadata))
            self.assertIn(
                "\\begin{proof}\n  First sentence. Second sentence.\n", formatted
            )
            self.assertIn(display, formatted)
            body = formatted[len(metadata) :]
            comments = [
                line for line in body.splitlines() if line.lstrip().startswith("%")
            ]
            self.assertGreater(len(comments), 1)
            self.assertEqual(
                " ".join(line.lstrip()[1:].strip() for line in comments),
                comment.strip(),
            )
            self.assertTrue(all(len(line) <= 120 for line in comments))
            shutil.rmtree(root / "cache")
            result = self.run_formatter(root, "--check")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(), formatted)

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_lean_indentation_preserves_relative_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_formatter(root)
            body = "  classical\n  have h : 0 ≤ a := by\n    nlinarith\n"
            source = (
                "\\begin{proof}\n  Since $b$ is positive, $1\\le b$.\n\n  \\begin{lean}\n"
                + body
                + (
                    "\\end{lean} % keep comment\n"
                    "  Already aligned.\n"
                    "\n"
                    "  \\begin{lean}\n"
                    "    exact h\n"
                    "  \\end{lean}\n"
                    "\\end{proof}\n"
                )
            )
            expected = source.replace("\n\\end{lean} %", "\n  \\end{lean} %")
            expected = expected.replace(
                "  classical\n  have h : 0 ≤ a := by\n    nlinarith\n",
                "    classical\n    have h : 0 ≤ a := by\n      nlinarith\n",
            )
            extra = (
                "An $\\{x\\}$ and \\textbf{nested} explanation.\n"
                "\n"
                "\\begin{lean} % code only\n"
                "abbrev neighborhood (p : X) (r : ℝ) : Set X := ball p r\n"
                "\n"
                "example : True := by\n"
                "  trivial\n"
                "\\end{lean}\n"
                "Over-indented.\n"
                "\n"
                "\\begin{lean}\n"
                "        example : True := by\n"
                "          trivial\n"
                "\\end{lean}\n"
                "Empty.\n"
                "\n"
                "\\begin{lean}\n"
                "\\end{lean}\n"
            )
            source += extra
            expected += (
                extra.replace("\nabbrev", "\n  abbrev")
                .replace("\nexample", "\n  example")
                .replace("\n  trivial", "\n    trivial")
                .replace("\n        example", "\n  example")
                .replace("\n          trivial", "\n    trivial")
            )
            path = root / "proof.tex"
            path.write_text(source, encoding="utf-8")
            subprocess.run(
                ["git", "add", "proof.tex"], cwd=root, check=True, timeout=30
            )

            result = self.run_formatter(root, "--check")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), source)
            result = self.run_formatter(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), expected)
            shutil.rmtree(root / "cache")
            result = self.run_formatter(root, "--check")
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_prose_and_code_indentation_are_checked_independently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_formatter(root)
            source = (
                "\\begin{theorem}\n"
                "Suppose $a\\in\\Z$. % unmatched { in a comment\n"
                "Use \\textbf{nested {braces}} and $\\{a\\}$.\n"
                "\\[\n"
                "  a=a.\n"
                "\\]\n"
                "\n"
                "  \\begin{lean}\n"
                "    example (a : ℤ) : a = a := by\n"
                "      rfl\n"
                "  \\end{lean}\n"
                "\\end{theorem}\n"
            )
            expected = source.replace(
                (
                    "Suppose $a\\in\\Z$. % unmatched { in a comment\n"
                    "Use \\textbf{nested {braces}} and $\\{a\\}$.\n"
                    "\\[\n"
                    "  a=a.\n"
                    "\\]\n"
                    "\n"
                ),
                (
                    "  Suppose $a\\in\\Z$. % unmatched { in a comment\n"
                    "  Use \\textbf{nested {braces}} and $\\{a\\}$.\n"
                    "  \\[\n"
                    "    a=a.\n"
                    "  \\]\n"
                    "\n"
                ),
            )
            path = root / "theorem.tex"
            path.write_text(source, encoding="utf-8")
            subprocess.run(
                ["git", "add", "theorem.tex"], cwd=root, check=True, timeout=30
            )

            result = self.run_formatter(root, "--check")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(path.read_text(), source)
            result = self.run_formatter(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(), expected)
            shutil.rmtree(root / "cache")
            result = self.run_formatter(root, "--check")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(), expected)
            path.write_text(expected.replace("  \\end{lean}\n", "\\end{lean}\n"))
            result = self.run_formatter(root, "--check")
            self.assertEqual(result.returncode, 1, result.stderr)

    def test_tracked_selection_and_cache_reuse_observe_source_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = self.prepare_formatter(root)
            (root / "tracked.tex").write_text("tracked\n", encoding="utf-8")
            (root / "draft.tex").write_text("draft\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "tracked.tex"], cwd=root, check=True, timeout=30
            )
            binary = root / "bin"
            binary.mkdir()
            latexindent = binary / "latexindent"
            write_executable(
                latexindent,
                (
                    textwrap.dedent(
                        """\
                        #!/usr/bin/env python3
                        import os
                        import pathlib
                        import sys
                        if "--version" in sys.argv:
                            print("latexindent fake")
                            raise SystemExit(0)
                        capture = pathlib.Path(os.environ["FORMAT_TEX_CAPTURE"])
                        with capture.open("a", encoding="utf-8") as stream:
                            for argument in sys.argv[1:]:
                                if argument.endswith((".tex", ".sty")):
                                    stream.write(argument + "\\n")
                                    print(pathlib.Path(argument).read_text(), end="")
                        """
                    )
                ),
            )
            capture = root / "capture.txt"

            def run(*arguments: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        sys.executable,
                        str(scripts / "latex/format_tex.py"),
                        "--check",
                        *arguments,
                    ],
                    cwd=root,
                    env={
                        **os.environ,
                        "PATH": f"{binary}:{os.environ['PATH']}",
                        "FORMAT_TEX_CAPTURE": str(capture),
                        "FORMAT_TEX_CACHE_DIR": str(root / "cache"),
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )

            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            inputs = capture.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(inputs), 2)
            self.assertEqual(Path(inputs[0]).name, "tracked.tex")
            self.assertEqual(Path(inputs[1]).name, "wrapped.tex")
            for arguments in ((), ("--file", str(root / "tracked.tex"))):
                with self.subTest(arguments=arguments):
                    result = run(*arguments)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("1 cached", result.stdout)
                    self.assertEqual(capture.read_text().splitlines(), inputs)

            source = root / "tracked.tex"
            previous = source.stat()
            source.write_text("changed\n")
            os.utime(source, ns=(previous.st_atime_ns, previous.st_mtime_ns))
            result = run("--file", str(source))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("0 cached", result.stdout)
            self.assertEqual(len(capture.read_text().splitlines()), 4)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1 cached", result.stdout)
            self.assertEqual(len(capture.read_text().splitlines()), 4)

            current = next((root / "cache").iterdir())
            obsolete = root / "cache" / ("0" * 64)
            obsolete.mkdir()
            (obsolete / "entry").write_text("old")
            unrelated = root / "cache" / "keep"
            unrelated.mkdir()
            external = root / "external"
            external.mkdir()
            (external / "keep").write_text("preserved")
            link = root / "cache" / ("1" * 64)
            link.symlink_to(external, target_is_directory=True)
            self.assertEqual(run().returncode, 0)
            self.assertTrue(obsolete.exists())
            result = run("--prune-cache")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1 cached", result.stdout)
            self.assertTrue(current.is_dir())
            self.assertFalse(obsolete.exists())
            self.assertTrue(unrelated.is_dir())
            self.assertTrue(link.is_symlink())
            self.assertEqual((external / "keep").read_text(), "preserved")


class FormatShellTests(unittest.TestCase):
    def test_only_repository_shell_scripts_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            (root / "config").mkdir()
            copy_script(ROOT / "config/authoring.json", root / "config/authoring.json")
            copy_script(
                ROOT / "scripts/repository/config/repository_config.py",
                scripts / "repository/config/repository_config.py",
            )
            copy_script(
                ROOT / "scripts/repository/formatting/format_code.py",
                scripts / "repository/formatting/format_code.py",
            )
            copy_script(
                ROOT / "scripts/repository/formatting/normalize_eof.py",
                scripts / "repository/formatting/normalize_eof.py",
            )
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
            (scripts / "tracked.sh").write_text(
                "#!/usr/bin/env bash\n", encoding="utf-8"
            )
            (scripts / "draft.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            nested = scripts / "nested/tools/draft.sh"
            nested.parent.mkdir(parents=True)
            nested.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (root / "outside.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "scripts/tracked.sh"], cwd=root, check=True, timeout=30
            )
            binary = root / "bin"
            binary.mkdir()
            shfmt = binary / "shfmt"
            write_executable(
                shfmt,
                (
                    textwrap.dedent(
                        """\
                        #!/usr/bin/env python3
                        import os
                        import pathlib
                        import sys
                        capture = pathlib.Path(os.environ["FORMAT_SHELL_CAPTURE"])
                        with capture.open("w", encoding="utf-8") as stream:
                            for argument in sys.argv[1:]:
                                if argument.endswith(".sh"):
                                    stream.write(argument + "\\n")
                        """
                    )
                ),
            )
            capture = root / "capture.txt"
            result = subprocess.run(
                [
                    sys.executable,
                    str(scripts / "repository/formatting/format_code.py"),
                    "sh",
                    "--check",
                ],
                cwd=root,
                env={
                    **os.environ,
                    "PATH": f"{binary}:{os.environ['PATH']}",
                    "FORMAT_SHELL_CAPTURE": str(capture),
                },
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                set(capture.read_text(encoding="utf-8").splitlines()),
                {
                    "scripts/draft.sh",
                    "scripts/nested/tools/draft.sh",
                    "scripts/tracked.sh",
                },
            )


if __name__ == "__main__":
    unittest.main()
