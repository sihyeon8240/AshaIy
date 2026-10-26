"""Exercise host container commands without requiring a Docker daemon."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support.fixtures import copy_validation_configuration, write_executable

ROOT = Path(__file__).resolve().parents[2]


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
        for directory in ("config/generated", "bin", ".devcontainer"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        self.image = "ghcr.io/example/math@sha256:" + "a" * 64
        (self.root / "config/container-image.txt").write_text(self.image + "\n")
        self.config = json.loads((ROOT / ".devcontainer/devcontainer.json").read_text())
        self.config["image"] = self.image
        self.config_path = self.root / ".devcontainer/devcontainer.json"
        self.config_path.write_text(json.dumps(self.config))
        self.log = self.root / "calls.jsonl"
        prefix = (
            f"#!{sys.executable}\n"
            "import json, os, signal, sys\n"
            "from pathlib import Path\n"
            "arguments = sys.argv[1:]\n"
            "with Path(os.environ['CALL_LOG']).open('a') as stream:\n"
            "    stream.write(json.dumps([Path(sys.argv[0]).name, *arguments]) + '\\n')\n"
        )
        write_executable(
            self.root / "bin/docker",
            prefix + "if arguments[:2] == ['image', 'inspect']:\n"
            "    print(os.environ.get('IMAGE_ID', 'sha256:' + 'b' * 64))\n"
            "elif arguments[0] == 'ps':\n"
            "    print(os.environ.get('DOCKER_MATCHES', '').replace(',', '\\n'))\n"
            "elif arguments[:2] == ['container', 'inspect']:\n"
            "    print(json.dumps([{'Id': arguments[2],\n"
            "        'Image': os.environ.get('EXISTING_IMAGE_ID', 'sha256:' + 'b' * 64),\n"
            "        'Config': {'Labels': {}},\n"
            "        'NetworkSettings': {'Ports': {'4000/tcp': [\n"
            "            {'HostIp': '127.0.0.1', 'HostPort': '4000'}]}}}]))\n"
            "sys.exit(int(os.environ.get('DOCKER_EXIT', '0')))\n",
        )
        write_executable(
            self.root / "bin/devcontainer",
            prefix + "if arguments[0] == 'up':\n"
            "    print(json.dumps({'outcome': 'success', 'containerId': 'container123'}))\n"
            "    sys.exit(int(os.environ.get('PREPARE_EXIT', '0')))\n"
            "if os.environ.get('EXEC_SIGNAL'):\n"
            "    os.kill(os.getpid(), signal.SIGTERM)\n"
            "print('command output')\n"
            "sys.exit(int(os.environ.get('EXEC_EXIT', '0')))\n",
        )
        self.environment = {
            **os.environ,
            "PATH": f"{self.root / 'bin'}:{os.environ['PATH']}",
            "CALL_LOG": str(self.log),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "IMAGE": "",
            "CMD": "",
            "DEVCONTAINER": str(self.root / "bin/devcontainer"),
            "PYTHON": sys.executable,
        }

    def cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/cli/repository_cli.py", *arguments],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    def calls(self, tool: str) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [
            call[1:]
            for line in self.log.read_text().splitlines()
            if (call := json.loads(line))[0] == tool
        ]

    def test_build_uses_repository_context_and_custom_tag(self) -> None:
        for options, tag in (
            ([], "ashaiy-toolchain:local"),
            (["--image", "custom:dev"], "custom:dev"),
        ):
            with self.subTest(tag=tag):
                result = self.cli("image", "build", *options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    self.calls("docker")[-1],
                    [
                        "build",
                        "--tag",
                        tag,
                        "--file",
                        str(self.root / ".devcontainer/Dockerfile"),
                        str(self.root),
                    ],
                )

    def test_default_run_uses_shared_configuration_and_exact_prepared_container(
        self,
    ) -> None:
        result = self.cli("image", "run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "command output\n")
        prepare, execute = self.calls("devcontainer")
        self.assertEqual(prepare[0], "up")
        self.assertEqual(execute[0], "exec")
        for arguments in (prepare, execute):
            self.assertEqual(
                arguments[arguments.index("--config") + 1], str(self.config_path)
            )
            self.assertIn(str(self.root), arguments)
            self.assertNotIn("--override-config", arguments)
            self.assertNotIn("--remove-existing-container", arguments)
        self.assertEqual(execute[execute.index("--container-id") + 1], "container123")
        self.assertEqual(execute[-1], "/bin/zsh")
        self.assertIn(
            f"label=devcontainer.config_file={self.config_path}",
            self.calls("docker")[1],
        )
        self.assertFalse((self.root / "cache/ashaiy-container").exists())

    def test_image_override_preserves_settings_and_isolates_rebuilt_tags(self) -> None:
        original = self.config_path.read_bytes()
        result = self.cli("image", "run", "--image", "custom:dev")
        self.assertEqual(result.returncode, 0, result.stderr)
        prepare = self.calls("devcontainer")[0]
        override = Path(prepare[prepare.index("--override-config") + 1])
        effective = json.loads(override.read_text())
        self.assertEqual(effective["image"], "custom:dev")
        for key in self.config.keys() - {"image", "runArgs"}:
            self.assertEqual(effective[key], self.config[key])
        self.assertNotIn("devcontainer.local_folder=", " ".join(prepare))
        self.assertIn("ashaiy.workspace=", " ".join(prepare))
        self.assertEqual(self.config_path.read_bytes(), original)
        self.environment["IMAGE_ID"] = "sha256:" + "c" * 64
        self.assertEqual(
            self.cli("image", "run", "--image", "custom:dev").returncode, 0
        )
        second = self.calls("devcontainer")[2]
        self.assertNotEqual(
            second[second.index("--override-config") + 1], str(override)
        )

    def test_command_is_passed_literally_without_host_execution(self) -> None:
        command = 'printf "%s" "$HOME"; touch "$(pwd)/unexpected"'
        result = self.cli("image", "run", "--command", command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.calls("devcontainer")[-1][-3:], ["/bin/bash", "-c", command]
        )
        self.assertFalse((self.root / "unexpected").exists())

    def test_direct_script_propagates_exit_status_from_any_directory(self) -> None:
        result = subprocess.run(
            [str(self.root / "scripts/toolchain/run_container.sh")],
            cwd=self.root / "bin",
            env={**self.environment, "EXEC_EXIT": "37"},
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 37, result.stderr)
        self.environment["EXEC_SIGNAL"] = "1"
        self.assertEqual(self.cli("image", "run").returncode, 143)

    def test_failed_preparation_never_executes_a_command(self) -> None:
        self.environment["PREPARE_EXIT"] = "23"
        result = self.cli("image", "run", "--command", "touch unexpected")
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(len(self.calls("devcontainer")), 1)
        self.assertEqual(result.stdout, "")

    def test_ambiguous_or_stale_containers_are_preserved(self) -> None:
        for matches in ("one,two", "old-container"):
            with self.subTest(matches=matches):
                self.environment["DOCKER_MATCHES"] = matches
                self.environment["EXISTING_IMAGE_ID"] = "sha256:" + "d" * 64
                result = self.cli("image", "run")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.calls("devcontainer"), [])
                self.assertFalse(
                    any(call[0] in {"rm", "stop"} for call in self.calls("docker"))
                )

    def test_missing_cli_and_invalid_images_fail_before_docker_changes(self) -> None:
        for image in ("--privileged", "bad image", "bad\nimage"):
            with self.subTest(image=image):
                result = self.cli("image", "run", "--image=" + image)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.calls("docker"), [])
        self.environment["DEVCONTAINER"] = str(self.root / "missing-devcontainer")
        result = self.cli("image", "run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required host tool not found", result.stderr)
        self.assertEqual(self.calls("docker"), [])
