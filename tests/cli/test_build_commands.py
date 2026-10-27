"""Build orchestration and public CLI commands."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from tests.support.fixtures import (
    copy_file,
    copy_validation_configuration,
    write_executable,
)

ROOT = Path(__file__).resolve().parents[2]


class FullCheckTests(unittest.TestCase):
    def test_ci_source_profile_pairs_proof_modes_and_stops_on_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir(exist_ok=True)
            for name in (
                "cli/repository_cli.py",
                "cli/repository_tasks.py",
                "cli/task_stages.py",
                "repository/source_reads.py",
                "repository/file_updates.py",
            ):
                copy_file(ROOT / "scripts" / name, scripts / name)
            for name in ("lean/check_lean.sh", "repository/checks/check_repository.sh"):
                write_executable(
                    scripts / name,
                    (
                        "#!/usr/bin/env bash\n"
                        'printf "%s %s\\n" "${0##*/}" "$*" >> "$CAPTURE"\n'
                        'if [[ "${0##*/}" == check_lean.sh ]]; then\n'
                        '  exit "$PROOF_STATUS"\n'
                        "fi\n"
                        'exit "$SOURCE_STATUS"\n'
                    ),
                )
            (scripts / "lean/proof_links.py").write_text(
                "import os\n"
                "with open(os.environ['CAPTURE'], 'a') as output:\n"
                "    output.write('proof_links.py \\n')\n"
                "raise SystemExit(int(os.environ['PROOF_STATUS']))\n"
            )
            for mode in ("build", "links"):
                for proof_status, source_status in ((0, 0), (7, 0), (0, 9)):
                    with self.subTest(
                        mode=mode,
                        proof_status=proof_status,
                        source_status=source_status,
                    ):
                        capture = root / "calls"
                        capture.unlink(missing_ok=True)
                        result = subprocess.run(
                            [
                                sys.executable,
                                str(scripts / "cli/repository_cli.py"),
                                "ci-source",
                                "--lean-mode",
                                mode,
                            ],
                            cwd=root,
                            env={
                                **os.environ,
                                "CAPTURE": str(capture),
                                "PROOF_STATUS": str(proof_status),
                                "SOURCE_STATUS": str(source_status),
                            },
                            text=True,
                            capture_output=True,
                            timeout=15,
                        )
                        self.assertEqual(
                            result.returncode,
                            proof_status or source_status,
                            result.stderr,
                        )
                        proof = (
                            "check_lean.sh " if mode == "build" else "proof_links.py "
                        )
                        expected = [proof]
                        if not proof_status:
                            expected.append("check_repository.sh --defer-lean")
                        self.assertEqual(capture.read_text().splitlines(), expected)

    def test_full_check_defers_links_and_stops_on_lean_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir(exist_ok=True)
            copy_file(ROOT / "scripts/ashaiy", scripts / "ashaiy")
            for name in (
                "cli/repository_cli.py",
                "cli/repository_tasks.py",
                "cli/task_stages.py",
                "repository/source_reads.py",
                "repository/file_updates.py",
            ):
                copy_file(ROOT / "scripts" / name, scripts / name)
            names = [
                "repository/checks/check_repository.sh",
                "repository/formatting/format_code.py",
                "latex/format_tex.py",
                "repository/formatting/normalize_eof.py",
                "lean/check_lean.sh",
                "latex/build_all.py",
            ]
            for name in names:
                script = scripts / name
                if script.suffix == ".py":
                    program = textwrap.dedent("""\
                        import os
                        import sys
                        from pathlib import Path

                        name = Path(sys.argv[0]).name
                        capture = Path(os.environ["CAPTURE"])
                        with capture.open("a") as output:
                            output.write(f"{name} {' '.join(sys.argv[1:])}\\n")
                        with Path(f"{capture}.environment").open("a") as output:
                            strict = os.environ.get("CHECK_LOG_STRICT", "0")
                            validated = os.environ.get("BOOKS_MANIFEST_VALIDATED", "0")
                            output.write(f"{name} {strict} {validated}\\n")
                        """)
                else:
                    program = (
                        '#!/bin/sh\nprintf "%s %s\\n" "${0##*/}" "$*" >> "$CAPTURE"\n'
                        'printf "%s %s %s\\n" "${0##*/}" "${CHECK_LOG_STRICT:-0}" '
                        '"${BOOKS_MANIFEST_VALIDATED:-0}" >> "$CAPTURE.environment"\n'
                    )
                    if name == "lean/check_lean.sh":
                        program += 'exit "${LEAN_EXIT_CODE:-0}"\n'
                write_executable(script, program)
            for status, strict in ((0, False), (7, False), (0, True)):
                with self.subTest(status=status, strict=strict):
                    capture = root / f"calls-{status}-{strict}"
                    entry = "cli/repository_cli.py" if strict else "ashaiy"
                    arguments = [sys.executable, str(scripts / entry), "check", "all"]
                    if strict:
                        arguments.append("--strict")
                    result = subprocess.run(
                        arguments,
                        cwd=root,
                        env={
                            **os.environ,
                            "CAPTURE": str(capture),
                            "LEAN_EXIT_CODE": str(status),
                            "CHECK_LOG_STRICT": "0",
                            "BOOKS_MANIFEST_VALIDATED": "0",
                        },
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(result.returncode, status, result.stderr)
                    calls = capture.read_text().splitlines()
                    self.assertEqual(calls[0], "check_repository.sh --defer-lean")
                    self.assertIn("format_code.py py --check", calls)
                    self.assertIn("format_code.py sh --check", calls)
                    self.assertIn("normalize_eof.py --check --exclude-formatted", calls)
                    self.assertEqual(calls.count("check_lean.sh "), 1)
                    self.assertEqual("build_all.py check" in calls, status == 0)
                    environments = (
                        Path(f"{capture}.environment").read_text().splitlines()
                    )
                    for environment in environments:
                        name, strict_flag, manifest_flag = environment.split()
                        self.assertEqual(strict_flag, "1" if strict else "0")
                        self.assertEqual(manifest_flag, "0")


class BuildVSCodeTests(unittest.TestCase):
    def test_prepares_output_tree_before_running_latexmk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir(exist_ok=True)
            copy_file(
                ROOT / "scripts/latex/build_vscode.sh",
                scripts / "latex/build_vscode.sh",
            )
            copy_file(
                ROOT / "scripts/latex/build_support.sh",
                scripts / "latex/build_support.sh",
            )
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config/latexmkrc").write_text("", encoding="utf-8")
            book = root / "books/example"
            (book / "chapters/example").mkdir(parents=True)
            (book / "chapters/space and\nnewline").mkdir()
            document = book / "book.tex"
            document.write_text("", encoding="utf-8")
            output = root / "vscode-build/books/example"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            latexmk = bin_dir / "latexmk"
            write_executable(
                latexmk,
                (
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    'printf "%s\\n" "$PWD" "$@" > "$LATEXMK_CAPTURE"\n'
                ),
            )
            capture = root / "latexmk-arguments"
            environment = os.environ.copy()
            environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
            environment["LATEXMK_CAPTURE"] = str(capture)
            result = subprocess.run(
                [
                    str(scripts / "latex/build_vscode.sh"),
                    str(output),
                    str(document),
                    "-shell-escape",
                ],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output / "chapters/example").is_dir())
            self.assertTrue((output / "chapters/space and\nnewline").is_dir())
            self.assertEqual(
                capture.read_text(encoding="utf-8").splitlines(),
                [
                    str(book),
                    "-r",
                    str(root / "config/latexmkrc"),
                    "-lualatex",
                    f"-outdir={output}",
                    "-shell-escape",
                    "book.tex",
                ],
            )


class BookCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        copy_validation_configuration(self.root)
        from tests.support.fixtures import book_record, manifest_document, write_yaml

        write_yaml(
            self.root / "config/books.yml", manifest_document([book_record("sample")])
        )
        (self.root / "books/sample").mkdir(parents=True)
        (self.root / "books/sample/book.tex").write_text("Fixture.\n")
        shutil.copytree(
            ROOT / "scripts",
            self.root / "scripts",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        scripts = self.root / "scripts"
        scripts.mkdir(exist_ok=True)
        (self.root / "config/generated").mkdir(parents=True, exist_ok=True)
        copy_file(ROOT / "scripts/latex/check_log.py", scripts / "latex/check_log.py")
        for name in (
            "cli/repository_cli.py",
            "cli/repository_tasks.py",
            "cli/task_stages.py",
            "repository/source_reads.py",
        ):
            copy_file(ROOT / "scripts" / name, scripts / name)
        build = scripts / "latex/build_book.sh"
        write_executable(
            build,
            (
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                'mkdir -p "build/$1"\n'
                'printf %b "${BUILD_LOG_TEXT:-}" > "build/$1/book.log"\n'
            ),
        )
        build_all = scripts / "latex/build_all.py"
        write_executable(
            build_all,
            "import os\nimport sys\nfrom pathlib import Path\n"
            'Path("bulk-arguments").write_text(" ".join(sys.argv[1:]))\n'
            'Path("bulk-strict").write_text(os.environ.get("CHECK_LOG_STRICT", "0"))\n',
        )

    def run_cli(
        self, *goals: str, log_text: str = ""
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "scripts/cli/repository_cli.py",
                "book",
                "build",
                "--book",
                "sample",
                *["--" + goal for goal in goals],
            ],
            cwd=self.root,
            env={**os.environ, "PYTHON": sys.executable, "BUILD_LOG_TEXT": log_text},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def test_build_options_reach_the_builder_environment(self) -> None:
        write_executable(
            self.root / "scripts/latex/build_book.sh",
            '#!/bin/sh\nprintf "%s %s" "$BOOK_BUILD_JOBS" "$SHELL_ESCAPE" > build-options\n',
        )
        result = subprocess.run(
            [
                sys.executable,
                "scripts/cli/repository_cli.py",
                "book",
                "build",
                "--book",
                "sample",
                "--jobs",
                "2",
                "--shell-escape",
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "build-options").read_text(), "2 1")

    def test_check_rejects_a_latex_log_error(self) -> None:
        result = self.run_cli(
            "check", log_text="LaTeX Warning: Reference `x` undefined.\n"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("undefined reference", result.stderr)

    def test_bulk_build_selection_and_strict_mode_through_both_entries(self) -> None:
        cases = ((False, False), (True, False), (True, True))
        for entry in ("python",):
            for check, strict in cases:
                with self.subTest(entry=entry, check=check, strict=strict):
                    arguments = [
                        sys.executable,
                        "scripts/cli/repository_cli.py",
                        "book",
                        "build",
                    ]
                    if check:
                        arguments.append("--check")
                    if strict:
                        arguments.append("--strict")
                    result = subprocess.run(
                        arguments,
                        cwd=self.root,
                        env={
                            **os.environ,
                            "PYTHON": sys.executable,
                            "CHECK_LOG_STRICT": "0",
                        },
                        text=True,
                        capture_output=True,
                        timeout=15,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        (self.root / "bulk-arguments").read_text(),
                        "check" if check else "",
                    )
                    self.assertEqual(
                        (self.root / "bulk-strict").read_text(), "1" if strict else "0"
                    )

    def test_direct_book_command_preserves_build_failure_status(self) -> None:
        (self.root / "scripts/latex/build_book.sh").write_text(
            "#!/usr/bin/env bash\nexit 23\n"
        )
        result = subprocess.run(
            [
                sys.executable,
                "scripts/cli/repository_cli.py",
                "book",
                "build",
                "--book",
                "sample",
                "--check",
                "--strict",
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertNotIn("book.log", result.stderr)

    def test_strict_without_check_rejects_before_building(self) -> None:
        arguments = [
            sys.executable,
            "scripts/cli/repository_cli.py",
            "book",
            "build",
            "--book",
            "sample",
            "--strict",
        ]
        for command in (
            [
                sys.executable,
                "scripts/cli/repository_cli.py",
                "book",
                "build",
                "--book",
                "sample",
                "--strict",
            ],
            arguments,
        ):
            with self.subTest(command=command):
                result = subprocess.run(
                    command,
                    cwd=self.root,
                    env={**os.environ, "PYTHON": sys.executable},
                    text=True,
                    capture_output=True,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("strict requires check", result.stderr)
                self.assertFalse((self.root / "build").exists())

    def test_build_failure_is_not_masked_by_a_previous_clean_log(self) -> None:
        output = self.root / "build/sample"
        output.mkdir(parents=True)
        (output / "book.log").write_text("Previous successful build\n")
        (self.root / "scripts/latex/build_book.sh").write_text(
            "#!/usr/bin/env bash\necho build-failed >&2\nexit 23\n"
        )
        for goals in ((), ("check",), ("check", "strict")):
            with self.subTest(goals=goals):
                result = self.run_cli(*goals)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("build-failed", result.stderr)

    def test_strict_controls_overfull_box_failure(self) -> None:
        log = (
            "Overfull \\hbox (1.0pt too wide) detected at line 1\n"
            "Output written on book.pdf (1 page, 123 bytes).\n"
        )
        advisory = self.run_cli("check", log_text=log)
        strict = self.run_cli("check", "strict", log_text=log)
        self.assertEqual(advisory.returncode, 0, advisory.stderr)
        self.assertIn("warning: overfull box", advisory.stderr)
        self.assertEqual(strict.returncode, 1)
        self.assertIn("error: overfull box", strict.stderr)


class BuildBookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        copy_validation_configuration(self.root)
        scripts = self.root / "scripts"
        scripts.mkdir(exist_ok=True)
        copy_file(ROOT / "scripts/latex/build_book.sh", scripts / "latex/build_book.sh")
        copy_file(
            ROOT / "scripts/latex/build_support.sh", scripts / "latex/build_support.sh"
        )
        (scripts / "books/books.py").write_text(
            textwrap.dedent(
                "            import sys\n"
                '            if sys.argv[1:3] != ["require", "sample"]:\n'
                "                raise SystemExit(1)\n"
                "            "
            ),
            encoding="utf-8",
        )
        (self.root / "config").mkdir(parents=True, exist_ok=True)
        (self.root / "config/latexmkrc").write_text("", encoding="utf-8")
        (self.root / "common/styles").mkdir(parents=True)
        (self.root / "common/templates").mkdir(parents=True)
        book = self.root / "books/sample"
        (book / "chapters/start").mkdir(parents=True)
        (book / "book.tex").write_text("book", encoding="utf-8")
        binary = self.root / "bin"
        binary.mkdir()
        write_executable(
            binary / "latexmk",
            textwrap.dedent(
                "            #!/usr/bin/env bash\n"
                "            set -euo pipefail\n"
                "            printf '%s\n"
                '\' "$TEXINPUTS" > "$LATEXMK_CAPTURE/texinputs"\n'
                "            printf '%s\n"
                '\' "$@" > "$LATEXMK_CAPTURE/arguments"\n'
                '            if [[ -e "$LATEXMK_CAPTURE/book.pdf" ]]; then\n'
                '              touch "$LATEXMK_CAPTURE/stale-pdf-observed"\n'
                "            fi\n"
                '            touch "$LATEXMK_CAPTURE/book.pdf"\n'
                '            exit "${LATEXMK_EXIT_CODE:-0}"\n'
                "            "
            ),
        )
        self.path = f"{binary}:{os.environ['PATH']}"

    def test_build_creates_mirrored_output_and_passes_texinputs(self) -> None:
        output = self.root / "build/sample"
        result = subprocess.run(
            [str(self.root / "scripts/latex/build_book.sh"), "sample"],
            cwd=self.root,
            env={
                **os.environ,
                "PATH": self.path,
                "PYTHON": sys.executable,
                "LATEXMK_CAPTURE": str(output),
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "chapters/start").is_dir())
        self.assertIn(
            str(self.root / "common/styles//"), (output / "texinputs").read_text()
        )
        self.assertIn(f"-outdir={output}", (output / "arguments").read_text())

    def test_editor_and_cli_share_environment_and_failure_cleanup(self) -> None:
        copy_file(
            ROOT / "scripts/latex/build_vscode.sh",
            self.root / "scripts/latex/build_vscode.sh",
        )
        for status in (0, 17):
            with self.subTest(status=status):
                output = self.root / "vscode-build/sample"
                output.mkdir(parents=True, exist_ok=True)
                (output / "book.pdf").write_text("previous PDF")
                result = subprocess.run(
                    [
                        str(self.root / "scripts/latex/build_vscode.sh"),
                        str(output),
                        str(self.root / "books/sample/book.tex"),
                    ],
                    cwd=self.root,
                    env={
                        **os.environ,
                        "PATH": self.path,
                        "TEXINPUTS": "external/path:",
                        "SHELL_ESCAPE": "1",
                        "LATEXMK_CAPTURE": str(output),
                        "LATEXMK_EXIT_CODE": str(status),
                    },
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual((output / "book.pdf").exists(), status == 0)
                self.assertEqual(
                    (output / "texinputs").read_text().strip(),
                    f".:{self.root}/common/styles//:{self.root}/common/templates//:external/path:",
                )
                self.assertIn("-shell-escape", (output / "arguments").read_text())

    def test_shell_escape_is_explicit_and_validated(self) -> None:
        for option in ("0", "1", "invalid"):
            with self.subTest(option=option):
                result = subprocess.run(
                    [str(self.root / "scripts/latex/build_book.sh"), "sample"],
                    cwd=self.root,
                    env={
                        **os.environ,
                        "PATH": self.path,
                        "LATEXMK_CAPTURE": str(self.root / "build/sample"),
                        "SHELL_ESCAPE": option,
                    },
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    result.returncode, 2 if option == "invalid" else 0, result.stderr
                )
                if option != "invalid":
                    arguments = (self.root / "build/sample/arguments").read_text()
                    self.assertEqual("-shell-escape" in arguments, option == "1")

    def test_preserves_pdf_for_incremental_latexmk(self) -> None:
        output = self.root / "build/sample"
        output.mkdir(parents=True)
        (output / "book.pdf").write_text("stale", encoding="utf-8")
        result = subprocess.run(
            [str(self.root / "scripts/latex/build_book.sh"), "sample"],
            cwd=self.root,
            env={
                **os.environ,
                "PATH": self.path,
                "PYTHON": sys.executable,
                "LATEXMK_CAPTURE": str(output),
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "stale-pdf-observed").exists())
        self.assertTrue((output / "book.pdf").exists())

    def test_failed_latexmk_removes_pdf_and_preserves_exit_status(self) -> None:
        output = self.root / "build/sample"
        output.mkdir(parents=True)
        (output / "book.pdf").write_text("stale", encoding="utf-8")
        result = subprocess.run(
            [str(self.root / "scripts/latex/build_book.sh"), "sample"],
            cwd=self.root,
            env={
                **os.environ,
                "PATH": self.path,
                "PYTHON": sys.executable,
                "LATEXMK_CAPTURE": str(output),
                "LATEXMK_EXIT_CODE": "17",
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertFalse((output / "book.pdf").exists())
        self.assertNotIn("==> Built", result.stdout)

    def test_same_output_is_serialized_through_failed_pdf_cleanup(self) -> None:
        from tests.support.fixtures import stop_process_group

        write_executable(
            self.root / "bin/latexmk",
            f"#!{sys.executable}\n"
            "import os, time\n"
            "from pathlib import Path\n"
            "root = Path(os.environ['GATE'])\n"
            "name = os.environ['RUN_NAME']\n"
            "(root / (name + '.started')).touch()\n"
            "output = Path(os.environ['LATEXMK_CAPTURE']) / 'book.pdf'\n"
            "output.write_text(name)\n"
            "if name == 'first':\n"
            "    while not (root / 'release').exists():\n"
            "        time.sleep(0.01)\n"
            "    raise SystemExit(17)\n",
        )
        output = self.root / "build/sample"
        commands = [str(self.root / "scripts/latex/build_book.sh"), "sample"]
        processes = []
        for name in ("first", "second"):
            process = subprocess.Popen(
                commands,
                cwd=self.root,
                env={
                    **os.environ,
                    "PATH": self.path,
                    "GATE": str(self.root),
                    "RUN_NAME": name,
                    "LATEXMK_CAPTURE": str(output),
                },
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            self.addCleanup(stop_process_group, process)
            processes.append(process)
            if name == "first":
                deadline = time.monotonic() + 5
                while not (self.root / "first.started").exists():
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.01)
        time.sleep(0.1)
        self.assertFalse((self.root / "second.started").exists())
        (self.root / "release").touch()
        for process, status in zip(processes, (17, 0), strict=True):
            _, errors = process.communicate(timeout=5)
            self.assertEqual(process.returncode, status, errors)
        self.assertEqual((output / "book.pdf").read_text(), "second")


if __name__ == "__main__":
    unittest.main()
