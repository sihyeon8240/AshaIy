"""Exercise public container and book commands without a Docker daemon."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_support import copy_validation_configuration, write_executable

ROOT = Path(__file__).resolve().parent.parent


class ContainerCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="math container ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        copy_validation_configuration(self.root)
        shutil.copytree(
            ROOT / "scripts",
            self.root / "scripts",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        for directory in ("scripts", "config", "bin", ".devcontainer"):
            (self.root / directory).mkdir(exist_ok=True)
        (self.root / "config/generated").mkdir(parents=True, exist_ok=True)
        for name in ("build_image.sh", "run_container.sh"):
            shutil.copy2(ROOT / "scripts" / name, self.root / "scripts" / name)
        self.image = "ghcr.io/example/math@sha256:" + "a" * 64
        (self.root / "config/container-image.txt").write_text(self.image + "\n")
        docker = self.root / "bin/docker"
        write_executable(
            docker,
            f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\nPath(os.environ['DOCKER_ARGUMENTS']).write_text(json.dumps(sys.argv[1:]))\nsys.exit(int(os.environ.get('DOCKER_EXIT', '0')))\n",
        )
        self.arguments_path = self.root / "arguments.json"
        self.environment = {
            **os.environ,
            "PATH": f"{self.root / 'bin'}:{os.environ['PATH']}",
            "DOCKER_ARGUMENTS": str(self.arguments_path),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "IMAGE": "",
            "CMD": "",
            "PYTHON": sys.executable,
        }

    def cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/repository_cli.py", *arguments],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    def arguments(self) -> list[str]:
        return json.loads(self.arguments_path.read_text())

    def test_build_uses_repository_context_and_custom_tag(self) -> None:
        for options, tag in (
            ([], "ashaiy-toolchain:local"),
            (["--image", "custom:dev"], "custom:dev"),
        ):
            with self.subTest(tag=tag):
                result = self.cli("image", "build", *options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    self.arguments(),
                    [
                        "build",
                        "--tag",
                        tag,
                        "--file",
                        str(self.root / ".devcontainer/Dockerfile"),
                        str(self.root),
                    ],
                )

    def test_run_mounts_checkout_and_preserves_user_and_cache(self) -> None:
        result = self.cli("image", "run")
        self.assertEqual(result.returncode, 0, result.stderr)
        arguments = self.arguments()
        self.assertEqual(arguments[-2:], [self.image, "/bin/zsh"])
        self.assertIn(f"{self.root}:/workspace", arguments)
        self.assertEqual(
            arguments[arguments.index("--user") + 1], f"{os.getuid()}:{os.getgid()}"
        )
        self.assertIn("--interactive", arguments)
        self.assertNotIn("--tty", arguments)
        self.assertIn("HOME=/home/developer", arguments)
        self.assertIn("ELAN_HOME=/home/developer/.elan", arguments)
        self.assertIn("PYTHONPYCACHEPREFIX=/workspace/.cache/python", arguments)
        self.assertIn("MATHLIB_CACHE_DIR=/workspace/.cache/mathlib", arguments)
        self.assertEqual(
            arguments[arguments.index("--entrypoint") + 1],
            "/workspace/scripts/container_entrypoint.sh",
        )
        self.assertIn(
            "TEXINPUTS=.:/workspace/common/styles//:/workspace/common/templates//:",
            arguments,
        )
        homes = list((self.root / "cache/ashaiy-container").iterdir())
        self.assertEqual(len(homes), 1)
        marker = homes[0] / "cached"
        marker.write_text("keep")
        self.assertEqual(self.cli("image", "run").returncode, 0)
        self.assertEqual(marker.read_text(), "keep")
        self.assertEqual(self.arguments(), arguments)

    def test_command_is_passed_literally_without_host_execution(self) -> None:
        command = 'printf "%s" "$HOME"; touch "$(pwd)/unexpected"'
        result = self.cli("image", "run", "--image", "custom:dev", "--command", command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.arguments()[-4:], ["custom:dev", "/bin/bash", "-c", command]
        )
        self.assertFalse((self.root / "unexpected").exists())

    def test_direct_script_propagates_exit_status_from_any_directory(self) -> None:
        result = subprocess.run(
            [str(self.root / "scripts/run_container.sh")],
            cwd=self.root / "bin",
            env={**self.environment, "DOCKER_EXIT": "23"},
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 23)
        self.assertIn(f"{self.root}:/workspace", self.arguments())
        self.environment["DOCKER_EXIT"] = "23"
        self.assertNotEqual(self.cli("image", "run").returncode, 0)

    def test_container_entrypoint_sets_a_writable_lean_home(self) -> None:
        shutil.copy2(
            ROOT / "scripts/container_entrypoint.sh",
            self.root / "scripts/container_entrypoint.sh",
        )
        shutil.copy2(self.root / "bin/docker", self.root / "bin/elan")
        (self.root / "config/toolchain.env").write_text(
            "LEAN_TOOLCHAIN=leanprover/lean4:v99.0.0\n"
        )
        elan_home = self.root / "writable-elan"
        for _ in range(2):
            result = subprocess.run(
                [
                    str(self.root / "scripts/container_entrypoint.sh"),
                    "/bin/sh",
                    "-c",
                    'test "${PATH%%:*}" = "$1" || exit 1; exit 37',
                    "sh",
                    str(self.root / ".cache/bin"),
                ],
                env={**self.environment, "ELAN_HOME": str(elan_home)},
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(result.returncode, 37, result.stderr)
            self.assertEqual(self.arguments(), ["default", "leanprover/lean4:v99.0.0"])
            self.assertTrue((elan_home / "toolchains").is_dir())
