"""Formatter argument handling and source preservation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_support import write_executable

ROOT = Path(__file__).resolve().parent.parent


class FormatterArgumentsTests(unittest.TestCase):
    def test_extra_check_arguments_are_rejected_before_running_tools(self) -> None:
        for name in ("python", "shell", "tex"):
            with self.subTest(formatter=name):
                result = subprocess.run(
                    [str(ROOT / f"scripts/format-{name}.sh"), "--check", "extra"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("usage:", result.stderr)


class FormatCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(
            ROOT / "scripts",
            self.root / "scripts",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        for name in (
            "config/authoring.json",
            "config/authoring.json",
            "config/authoring.json",
            "scripts/repository_cli.py",
            "scripts/repository_tasks.py",
            "scripts/task_stages.py",
            "scripts/source_reads.py",
        ):
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        for name in (
            "format-tex.sh",
            "format-python.sh",
            "format-shell.sh",
            "normalize-eof.sh",
        ):
            write_executable(
                self.root / "scripts" / name,
                "#!/usr/bin/env python3\nimport json, os, sys\nfrom pathlib import Path\nname = Path(__file__).name\nwith open('calls', 'a') as output:\n    output.write(json.dumps([name, *sys.argv[1:]]) + '\\n')\nraise SystemExit(7 if os.environ.get('FAIL_FORMAT') == name else 0)\n",
            )

    def run_format(self, entry, scope, *, check=False, file=None, fail=""):
        arguments = [sys.executable, "scripts/repository_cli.py", "format", scope]
        if check:
            arguments.append("--check")
        if file is not None:
            arguments.extend(["--file", file])
        (self.root / "calls").unlink(missing_ok=True)
        result = subprocess.run(
            arguments,
            cwd=self.root,
            env={
                **os.environ,
                "PYTHON": sys.executable,
                "FILE": "",
                "FAIL_FORMAT": fail,
            },
            text=True,
            capture_output=True,
            timeout=15,
        )
        capture = self.root / "calls"
        calls = (
            [json.loads(line) for line in capture.read_text().splitlines()]
            if capture.exists()
            else []
        )
        return (result, calls)

    def test_all_formats_in_order_and_stops_at_each_failure(self) -> None:
        scripts = [
            "format-tex.sh",
            "format-python.sh",
            "format-shell.sh",
            "normalize-eof.sh",
        ]
        for entry in ("python",):
            for check in (False, True):
                for failure in ("", *scripts):
                    with self.subTest(entry=entry, check=check, failure=failure):
                        result, calls = self.run_format(
                            entry, "all", check=check, fail=failure
                        )
                        status = 7 if failure else 0
                        self.assertEqual(result.returncode, status, result.stderr)
                        selected = (
                            scripts[: scripts.index(failure) + 1]
                            if failure
                            else scripts
                        )
                        options = ["--check"] if check else []
                        self.assertEqual(calls, [[name, *options] for name in selected])

    def test_single_file_is_passed_literally_and_all_rejects_it(self) -> None:
        for entry in ("python",):
            for scope, script in (("tex", "tex"), ("py", "python"), ("sh", "shell")):
                with self.subTest(entry=entry, scope=scope):
                    file = "draft $(touch sentinel) `touch sentinel`"
                    result, calls = self.run_format(entry, scope, check=True, file=file)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        calls,
                        [
                            [
                                f"format-{script}.sh",
                                "--check",
                                "--file",
                                str(self.root / file),
                            ]
                        ],
                    )
                    self.assertFalse((self.root / "sentinel").exists())
            result, calls = self.run_format(entry, "all", file="draft.py")
            self.assertEqual(result.returncode, 2)
            self.assertIn("single format scope", result.stderr)
            self.assertEqual(calls, [])


class SingleFileFormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "scripts").mkdir(exist_ok=True)
        (self.root / "config/generated").mkdir(parents=True)
        for path in [
            "config/authoring.json",
            "config/authoring.json",
            "config/authoring.json",
            "config/latexindent.yaml",
            "config/authoring.json",
            "config/pyproject.toml",
            "scripts/repository_config.py",
            "scripts/repository_cli.py",
            "scripts/repository_tasks.py",
            "scripts/task_stages.py",
            "scripts/source_reads.py",
            "scripts/format-code.py",
            "scripts/format-python.sh",
            "scripts/format-shell.sh",
            "scripts/format-tex.sh",
            "scripts/format-tex-file.sh",
            "scripts/normalize-eof.sh",
        ]:
            shutil.copy2(ROOT / path, self.root / path)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, timeout=30)

    def run_format(
        self, language: str, path: str, check: bool = False
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "scripts/repository_cli.py",
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
        all((shutil.which(tool) for tool in ("ruff", "shfmt", "latexindent"))),
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
                        [str(self.root / "scripts/format-tex-file.sh"), str(path)],
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
    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_preserves_manual_lines_and_aligns_equation_rows(self) -> None:
        source = (
            "\\begin{proof}\n  Keep this short line.\n  Keep this separate line.\n"
            + "  "
            + "A long explanation with several words. " * 8
            + "\n"
            + "  "
            + "Another long explanation to wrap. " * 8
            + "\n  \\[\n    \\begin{aligned}\n      A + B & = (a + b) \\\\\n      cA & = (ca) \\\\\n      0 & = (0)\n    \\end{aligned}\n  \\]\n\\end{proof}\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proof.tex"
            path.write_text(source)
            command = [str(ROOT / "scripts/format-tex-file.sh"), str(path)]
            formatted = subprocess.check_output(command, text=True, timeout=30)
            self.assertIn(
                "  Keep this short line.\n  Keep this separate line.\n", formatted
            )
            self.assertTrue(all((len(line) <= 88 for line in formatted.splitlines())))
            rows = [line for line in formatted.splitlines() if line.endswith("\\\\")]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].index("\\\\"), rows[1].index("\\\\"))
            path.write_text(formatted)
            self.assertEqual(
                subprocess.check_output(command, text=True, timeout=30), formatted
            )

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_wraps_prose_to_88_columns_and_preserves_lean(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir(exist_ok=True)
            (root / "config").mkdir()
            shutil.copy2(
                ROOT / "config/latexindent.yaml", root / "config/latexindent.yaml"
            )
            for name in ("format-tex.sh", "format-tex-file.sh", "normalize-eof.sh"):
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
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

            def run(*arguments: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [str(scripts / "format-tex.sh"), *arguments],
                    cwd=root,
                    env={**os.environ, "FORMAT_TEX_CACHE_DIR": str(root / "cache")},
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )

            editor_result = subprocess.run(
                [str(scripts / "format-tex-file.sh"), str(path)],
                cwd=scripts,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(editor_result.returncode, 0, editor_result.stderr)
            self.assertEqual(path.read_text(), source)
            result = run("--check")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(path.read_text(), source)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            formatted = path.read_text()
            self.assertEqual(editor_result.stdout, formatted)
            paragraph = formatted.split("\n\n")[0].split("\n", 2)[2]
            self.assertEqual(" ".join(paragraph.split()), prose.strip())
            self.assertGreater(len(paragraph.splitlines()), 3)
            self.assertNotIn("\n  A mathematical explanation", paragraph)
            for line in paragraph.splitlines():
                self.assertLessEqual(len(line), 88)
                self.assertTrue(line.startswith("  "))
            self.assertIn(lean, formatted)
            for arguments in [("--check",), ()]:
                shutil.rmtree(root / "cache")
                result = run(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(path.read_text(), formatted)
            settings = root / "config/latexindent.yaml"
            settings.write_text(
                settings.read_text().replace("columns: 88", "columns: 60")
            )
            result = run("--check")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(path.read_text(), formatted)

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_wraps_comments_but_preserves_metadata_and_display_math(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            (root / "config").mkdir()
            shutil.copy2(
                ROOT / "config/latexindent.yaml", root / "config/latexindent.yaml"
            )
            for name in ("format-tex.sh", "format-tex-file.sh", "normalize-eof.sh"):
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
            metadata = (
                "% !TEX root = book.tex\n% BEGIN GENERATED APPENDICES\n% END GENERATED APPENDICES\n% Lean source: "
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

            def run(*arguments: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [str(scripts / "format-tex.sh"), *arguments],
                    cwd=root,
                    env={**os.environ, "FORMAT_TEX_CACHE_DIR": str(root / "cache")},
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )

            result = run()
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
                " ".join((line.lstrip()[1:].strip() for line in comments)),
                comment.strip(),
            )
            self.assertTrue(all((len(line) <= 88 for line in comments)))
            shutil.rmtree(root / "cache")
            result = run("--check")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(), formatted)

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_lean_indentation_preserves_relative_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            (root / "config").mkdir()
            shutil.copy2(
                ROOT / "config/latexindent.yaml", root / "config/latexindent.yaml"
            )
            for name in ("format-tex.sh", "format-tex-file.sh", "normalize-eof.sh"):
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
            body = "  classical\n  have h : 0 ≤ a := by\n    nlinarith\n"
            source = (
                "\\begin{proof}\n  Since $b$ is positive, $1\\le b$.\n\n  \\begin{lean}\n"
                + body
                + "\\end{lean} % keep comment\n  Already aligned.\n\n  \\begin{lean}\n    exact h\n  \\end{lean}\n\\end{proof}\n"
            )
            expected = source.replace("\n\\end{lean} %", "\n  \\end{lean} %")
            expected = expected.replace(
                "  classical\n  have h : 0 ≤ a := by\n    nlinarith\n",
                "    classical\n    have h : 0 ≤ a := by\n      nlinarith\n",
            )
            extra = "An $\\{x\\}$ and \\textbf{nested} explanation.\n\n\\begin{lean} % code only\nabbrev neighborhood (p : X) (r : ℝ) : Set X := ball p r\n\nexample : True := by\n  trivial\n\\end{lean}\nOver-indented.\n\n\\begin{lean}\n        example : True := by\n          trivial\n\\end{lean}\nEmpty.\n\n\\begin{lean}\n\\end{lean}\n"
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

            def run(*arguments: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [str(scripts / "format-tex.sh"), *arguments],
                    cwd=root,
                    env={**os.environ, "FORMAT_TEX_CACHE_DIR": str(root / "cache")},
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )

            result = run("--check")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), source)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), expected)
            shutil.rmtree(root / "cache")
            result = run("--check")
            self.assertEqual(result.returncode, 0, result.stderr)
            shutil.rmtree(root / "cache")
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), expected)

    @unittest.skipUnless(shutil.which("latexindent"), "latexindent is required")
    def test_prose_and_code_indentation_are_checked_independently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            (root / "config").mkdir()
            shutil.copy2(
                ROOT / "config/latexindent.yaml", root / "config/latexindent.yaml"
            )
            for name in ("format-tex.sh", "format-tex-file.sh", "normalize-eof.sh"):
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
            source = "\\begin{theorem}\nSuppose $a\\in\\Z$. % unmatched { in a comment\nUse \\textbf{nested {braces}} and $\\{a\\}$.\n\\[\n  a=a.\n\\]\n\n  \\begin{lean}\n    example (a : ℤ) : a = a := by\n      rfl\n  \\end{lean}\n\\end{theorem}\n"
            expected = source.replace(
                "Suppose $a\\in\\Z$. % unmatched { in a comment\nUse \\textbf{nested {braces}} and $\\{a\\}$.\n\\[\n  a=a.\n\\]\n\n",
                "  Suppose $a\\in\\Z$. % unmatched { in a comment\n  Use \\textbf{nested {braces}} and $\\{a\\}$.\n  \\[\n    a=a.\n  \\]\n\n",
            )
            path = root / "theorem.tex"
            path.write_text(source, encoding="utf-8")
            subprocess.run(
                ["git", "add", "theorem.tex"], cwd=root, check=True, timeout=30
            )

            def run(*arguments: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [str(scripts / "format-tex.sh"), *arguments],
                    cwd=root,
                    env={**os.environ, "FORMAT_TEX_CACHE_DIR": str(root / "cache")},
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )

            result = run("--check")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(path.read_text(), source)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(), expected)
            for arguments in [("--check",), ()]:
                shutil.rmtree(root / "cache")
                result = run(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(path.read_text(), expected)
            path.write_text(expected.replace("  \\end{lean}\n", "\\end{lean}\n"))
            result = run("--check")
            self.assertEqual(result.returncode, 1, result.stderr)

    def test_only_tracked_tex_files_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            (root / "config").mkdir()
            shutil.copy2(
                ROOT / "config/latexindent.yaml", root / "config/latexindent.yaml"
            )
            shutil.copy2(ROOT / "scripts/format-tex.sh", scripts / "format-tex.sh")
            shutil.copy2(
                ROOT / "scripts/format-tex-file.sh", scripts / "format-tex-file.sh"
            )
            shutil.copy2(
                ROOT / "scripts/normalize-eof.sh", scripts / "normalize-eof.sh"
            )
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
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
                '#!/usr/bin/env python3\nimport os\nimport pathlib\nimport sys\nif "--version" in sys.argv:\n    print("latexindent fake")\n    raise SystemExit(0)\ncapture = pathlib.Path(os.environ["FORMAT_TEX_CAPTURE"])\nwith capture.open("a", encoding="utf-8") as stream:\n    for argument in sys.argv[1:]:\n        if argument.endswith((".tex", ".sty")):\n            stream.write(argument + "\\n")\n            print(pathlib.Path(argument).read_text(), end="")\n',
            )
            capture = root / "capture.txt"
            result = subprocess.run(
                [str(scripts / "format-tex.sh"), "--check"],
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
            self.assertEqual(result.returncode, 0, result.stderr)
            inputs = capture.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(inputs), 2)
            self.assertEqual(inputs[0], "tracked.tex")
            self.assertEqual(Path(inputs[1]).name, "wrapped.tex")


class FormatShellTests(unittest.TestCase):
    def test_only_repository_shell_scripts_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            (root / "config").mkdir()
            shutil.copy2(ROOT / "config/authoring.json", root / "config/authoring.json")
            shutil.copy2(
                ROOT / "scripts/repository_config.py", scripts / "repository_config.py"
            )
            shutil.copy2(ROOT / "scripts/format-shell.sh", scripts / "format-shell.sh")
            shutil.copy2(ROOT / "scripts/format-code.py", scripts / "format-code.py")
            shutil.copy2(
                ROOT / "scripts/normalize-eof.sh", scripts / "normalize-eof.sh"
            )
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
            (scripts / "tracked.sh").write_text(
                "#!/usr/bin/env bash\n", encoding="utf-8"
            )
            (scripts / "draft.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (root / "outside.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "scripts/tracked.sh"], cwd=root, check=True, timeout=30
            )
            binary = root / "bin"
            binary.mkdir()
            shfmt = binary / "shfmt"
            write_executable(
                shfmt,
                '#!/usr/bin/env python3\nimport os\nimport pathlib\nimport sys\ncapture = pathlib.Path(os.environ["FORMAT_SHELL_CAPTURE"])\nwith capture.open("w", encoding="utf-8") as stream:\n    for argument in sys.argv[1:]:\n        if argument.endswith(".sh"):\n            stream.write(argument + "\\n")\n',
            )
            capture = root / "capture.txt"
            result = subprocess.run(
                [str(scripts / "format-shell.sh"), "--check"],
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
                    "scripts/format-shell.sh",
                    "scripts/normalize-eof.sh",
                    "scripts/tracked.sh",
                },
            )


if __name__ == "__main__":
    unittest.main()
