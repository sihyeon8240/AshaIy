#!/usr/bin/env python3
"""Open the checkout's Dev Container from a host terminal using only the stdlib."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.repository.config.json_config import parse_json, read_json

ROOT = Path(__file__).resolve().parents[2]


def captured(*arguments: str) -> str:
    return subprocess.check_output(arguments, text=True).strip()


def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise ValueError(
            f"required host tool not found: {name}; install the Dev Container CLI "
            "with 'Dev Containers: Install devcontainer CLI' in VS Code, or "
            "'npm install -g @devcontainers/cli'; see docs/developer-workflow.md"
        )
    return executable


def image_identity(image: str) -> str:
    result = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        if "No such image" not in result.stderr:
            raise ValueError(result.stderr.strip() or "could not inspect image")
        subprocess.run(["docker", "pull", image], stdout=sys.stderr, check=True)
        return captured("docker", "image", "inspect", "--format", "{{.Id}}", image)
    return result.stdout.strip()


def cache_directory(root: Path) -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    repository = hashlib.sha256(os.fsencode(root)).hexdigest()[:16]
    directory = cache / "ashaiy-devcontainers" / repository
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_override(path: Path, config: dict) -> None:
    text = json.dumps(config, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def matching_container(labels: list[str]) -> dict | None:
    filters = [value for label in labels for value in ("--filter", f"label={label}")]
    identifiers = captured(
        "docker", "ps", "--all", *filters, "--format", "{{.ID}}"
    ).splitlines()
    if len(identifiers) > 1:
        raise ValueError(
            "multiple development containers match this checkout: "
            + ", ".join(identifiers)
            + "; inspect them with 'docker ps -a' before choosing a container"
        )
    if not identifiers:
        return None
    return parse_json(captured("docker", "container", "inspect", identifiers[0]))[0]


def check_existing_image(container: dict | None, image: str, identity: str) -> None:
    if container is None or container["Image"] == identity:
        return
    # Image profiles record their base even if Dev Container features derive an image.
    labels = container["Config"].get("Labels") or {}
    if labels.get("ashaiy.image-id") == identity:
        return
    raise ValueError(
        f"container {container['Id'][:12]} does not use the requested image {image}; "
        "preserve any changes in its home, then use 'Dev Containers: Rebuild "
        "Container' in VS Code, or run with --image to create an isolated profile"
    )


def preparation_result(output: str) -> dict:
    for line in reversed(output.splitlines()):
        try:
            result = parse_json(line)
        except ValueError:
            continue
        if isinstance(result, dict) and result.get("outcome") == "success":
            identifier = result.get("containerId")
            if isinstance(identifier, str) and identifier:
                return result
    raise ValueError("Dev Container CLI did not return a successful container ID")


def report_container(identifier: str, image: str) -> None:
    print(f"[Container] {identifier[:12]} using {image}", file=sys.stderr)
    container = parse_json(captured("docker", "container", "inspect", identifier))[0]
    bindings = container.get("NetworkSettings", {}).get("Ports", {}) or {}
    for binding in bindings.get("4000/tcp") or []:
        print(
            f"[Preview] http://{binding['HostIp']}:{binding['HostPort']}",
            file=sys.stderr,
        )
    if not bindings.get("4000/tcp"):
        print(
            "[Preview] No published port 4000; preserve home changes and rebuild "
            "the container to apply new port settings, or use VS Code forwarding.",
            file=sys.stderr,
        )
    print(
        f"[Container] Stop when unused: docker stop {identifier[:12]}", file=sys.stderr
    )


def main(root: Path = ROOT) -> int:
    require_tool("docker")
    devcontainer = require_tool(os.environ.get("DEVCONTAINER", "devcontainer"))
    config_path = root / ".devcontainer/devcontainer.json"
    config = read_json(config_path)
    pin = (root / "config/container-image.txt").read_text(encoding="utf-8").strip()
    if config.get("image") != pin:
        raise ValueError(
            "development image settings have drifted; run ashaiy config generate"
        )
    override_image = os.environ.get("IMAGE", "")
    image = override_image or pin
    if (
        not image
        or image.startswith("-")
        or any(character.isspace() for character in image)
    ):
        raise ValueError(f"invalid container image reference: {image!r}")
    identity = image_identity(image)
    directory = cache_directory(root)
    common = ["--workspace-folder", str(root), "--config", str(config_path)]
    labels = [
        f"devcontainer.local_folder={root}",
        f"devcontainer.config_file={config_path}",
    ]
    if override_image:
        config["image"] = image
        config.setdefault("runArgs", []).extend(
            ["--label", f"ashaiy.image-id={identity}"]
        )
        # Include host substitutions and image identity when isolating mutable local tags.
        profile_input = json.dumps(
            [config, identity, os.environ.get("ASHAIY_PREVIEW_PORT", "4000")],
            sort_keys=True,
        )
        profile = hashlib.sha256(profile_input.encode()).hexdigest()[:16]
        override = directory / f"{profile}.json"
        write_override(override, config)
        common.extend(["--override-config", str(override)])
        labels = [f"ashaiy.workspace={root}", f"ashaiy.profile={profile}"]
        for label in labels:
            common.extend(["--id-label", label])

    with (directory / "prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = matching_container(labels)
        check_existing_image(existing, image, identity)
        command = [devcontainer, "up", *common]
        result = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=False)
        if result.returncode:
            if result.stdout:
                print(result.stdout, file=sys.stderr, end="")
            print(
                "error: container preparation failed; if the preview port is occupied, "
                "choose ASHAIY_PREVIEW_PORT before creating a new container",
                file=sys.stderr,
            )
            return result.returncode
        identifier = preparation_result(result.stdout)["containerId"]

    report_container(identifier, image)
    arguments = [devcontainer, "exec", *common, "--container-id", identifier]
    for name in ("TERM", "COLORTERM"):
        value = os.environ.get(name)
        if value:
            arguments.extend(["--remote-env", f"{name}={value}"])
    command_text = os.environ.get("CMD", "")
    if command_text:
        arguments.extend(["/bin/bash", "-c", command_text])
    else:
        arguments.append("/bin/zsh")
    os.execvpe(devcontainer, arguments, os.environ)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode) from error
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
