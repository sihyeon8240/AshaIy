"""Publish verified PR images and append pins without executing PR source."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

import github_artifacts
from ci_changes import IMAGE_PIPELINE, changed_paths
from config_sync import replace_once
from image_policy import input_hash
from repository_config import ROOT, image_name, load_image, load_image_build

try:
    from scripts.validation_patterns import validation_pattern
except ModuleNotFoundError:
    from validation_patterns import validation_pattern


def command(
    *args: str, data: str | None = None, env: dict | None = None, stream: bool = False
) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        input=data,
        env=env,
        text=True,
        capture_output=not stream,
        check=True,
        timeout=600 if stream else 1800,
    )
    return (result.stdout or "").strip()


def source_text(revision: str, path: str) -> str:
    # Preserve source newlines when preparing a two-file commit.
    return subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        timeout=60,
    ).stdout.decode("utf-8")


def source_policy(revision: str) -> tuple[dict, str]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        config = root / "config/image-build.json"
        config.parent.mkdir()
        config.write_text(source_text(revision, "config/image-build.json"))
        policy = load_image_build(root)
        for name in policy["inputs"]:
            entry = command("git", "ls-tree", revision, "--", name)
            mode = entry.split(" ", 1)[0]
            if mode not in {"100644", "100755"}:
                raise ValueError(f"image input must be a regular Git blob: {name}")
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source_text(revision, name))
            target.chmod(0o755 if mode == "100755" else 0o644)
        return policy, f"texlive-{input_hash(root)}"


def select_pull(repository: str, run: dict) -> dict | None:
    head = run["head_sha"]
    if not github_artifacts.eligible_run(run, repository, head):
        return None
    pulls = github_artifacts.api(
        f"repos/{repository}/commits/{head}/pulls?per_page=100"
    )
    for candidate in pulls:
        pull = github_artifacts.api(f"repos/{repository}/pulls/{candidate['number']}")
        if (
            pull["state"] == "open"
            and pull["base"]["ref"] == "main"
            and pull["base"]["repo"]["full_name"] == repository
            and (pull["head"]["repo"] or {}).get("full_name") == repository
            and pull["head"]["sha"] == head
            and pull["head"]["ref"] != "main"
        ):
            return pull
    return None


def summary(message: str) -> None:
    print(message, flush=True)
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if destination:
        with Path(destination).open("a") as stream:
            stream.write(message + "\n\n")


def dispatch_validation(repository: str, branch: str, commit: str) -> None:
    command(
        "gh",
        "api",
        "--method",
        "POST",
        f"repos/{repository}/actions/workflows/build.yml/dispatches",
        "--input",
        "-",
        data=json.dumps({"ref": branch, "inputs": {"expected_sha": commit}}),
    )
    summary(f"Started final consumer CI for `{commit}` on `{branch}` automatically.")


def append_pin(repository: str, pull: dict, image: str) -> bool:
    current = github_artifacts.api(f"repos/{repository}/pulls/{pull['number']}")
    head = pull["head"]["sha"]
    if (
        current["state"] != "open"
        or current["head"]["sha"] != head
        or current["head"]["ref"] != pull["head"]["ref"]
        or (current["head"]["repo"] or {}).get("full_name") != repository
    ):
        summary(
            "PR changed or closed during publication; leaving its branch untouched."
        )
        return False

    pin_path = "config/container-image.txt"
    dev_path = ".devcontainer/devcontainer.json"
    pin = source_text(head, pin_path)
    dev = source_text(head, dev_path)
    json.loads(dev)
    updated_dev = replace_once(
        dev,
        r'("image"\s*:\s*)"[^"]+"',
        rf'\g<1>"{image}"',
        Path(dev_path),
    )
    if pin == image + "\n" and dev == updated_dev:
        summary("PR already pins the tested image; no additional commit is needed.")
        return False

    # An isolated index avoids checking out PR hooks, configuration, or scripts.
    with tempfile.TemporaryDirectory() as temporary:
        env = {
            **os.environ,
            "GIT_INDEX_FILE": str(Path(temporary) / "index"),
            "GIT_AUTHOR_NAME": "github-actions[bot]",
            "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
            "GIT_COMMITTER_NAME": "github-actions[bot]",
            "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
        }
        command("git", "read-tree", head, env=env)
        for path, content in ((pin_path, image + "\n"), (dev_path, updated_dev)):
            entry = command("git", "ls-tree", head, "--", path)
            if not entry.startswith("100644 blob "):
                raise ValueError(f"expected a regular file: {path}")
            blob = command("git", "hash-object", "-w", "--stdin", data=content)
            command(
                "git", "update-index", "--cacheinfo", f"100644,{blob},{path}", env=env
            )
        tree = command("git", "write-tree", env=env)
        commit = command(
            "git",
            "commit-tree",
            tree,
            "-p",
            head,
            data="build(toolchain): pin tested development image\n",
            env=env,
        )

    # The commit extends the inspected head; the lease rejects any concurrent
    # author update, branch deletion, or rewind without overwriting their work.
    ref = f"refs/heads/{pull['head']['ref']}"
    command(
        "git", "push", f"--force-with-lease={ref}:{head}", "origin", f"{commit}:{ref}"
    )
    summary(f"Appended image pin to PR #{pull['number']}: `{commit}`.")
    dispatch_validation(repository, pull["head"]["ref"], commit)
    return True


def publish(load_candidate: Callable, *, policy: str, max_bytes: int) -> None:
    repository = os.environ["GITHUB_REPOSITORY"]
    run_id = int(os.environ["SOURCE_RUN_ID"])
    run = github_artifacts.api(f"repos/{repository}/actions/runs/{run_id}")
    print(f"Checking publication eligibility for run {run_id}", flush=True)
    pull = select_pull(repository, run)
    if pull is None:
        print("No current, successful same-repository PR candidate; skipping.")
        return

    command("git", "fetch", "--no-tags", "origin", f"refs/pull/{pull['number']}/merge")
    revision = command("git", "rev-parse", "FETCH_HEAD")
    parents = command("git", "show", "-s", "--format=%P", revision).split()
    if parents != [pull["base"]["sha"], pull["head"]["sha"]]:
        summary(
            "PR merge changed; rerun PR CI to validate the current revision before publication."
        )
        return
    config, tag = source_policy(revision)
    paths = changed_paths(pull["base"]["sha"], pull["head"]["sha"])
    if paths is None:
        raise ValueError("PR comparison unavailable")
    if not set(paths) & (set(config["inputs"]) | IMAGE_PIPELINE):
        print("PR does not change the image pipeline; skipping.")
        return

    # The registry destination comes from trusted main, never from PR artifacts.
    name = image_name(load_image())
    source_pin = source_text(revision, "config/container-image.txt").strip()
    if image_name(source_pin) != name:
        raise ValueError("image registry migration requires manual publication")
    release = f"{name}:{tag}"
    env = {**os.environ, "IMAGE_NAME": name, "RELEASE_TAG": tag}
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "output"
        command(
            "bash",
            "scripts/check_image_tag.sh",
            env={**env, "GITHUB_OUTPUT": str(output)},
        )
        exists = output.read_text().strip() == "exists=true"
    if not exists:
        artifacts = github_artifacts.api(
            f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100"
        )["artifacts"]
        candidates = {
            artifact["name"]: artifact
            for artifact in artifacts
            if not artifact.get("expired", True)
            and artifact.get("size_in_bytes", max_bytes + 1) <= max_bytes
        }
        architectures = [item["arch"] for item in config["platforms"]]
        if not all(f"toolchain-image-{arch}" in candidates for arch in architectures):
            raise ValueError("missing verified architecture artifacts; rerun PR CI")
        tree = command("git", "rev-parse", f"{revision}^{{tree}}")
        sources = []
        for arch in architectures:
            image = f"{name}:pr-{pull['number']}-{run_id}-{run['run_attempt']}-{arch}"
            expected = {"policy": policy, "tree": tree, "arch": arch}
            load_candidate(
                repository, candidates[f"toolchain-image-{arch}"], expected, run, image
            )
            # Loading and inspecting an image never executes its contents.
            print(f"Publishing {arch} image to GHCR: {image}", flush=True)
            command("docker", "push", image, stream=True)
            print(f"Published {arch} image; checking registry digest", flush=True)
            digest = command(
                "docker",
                "buildx",
                "imagetools",
                "inspect",
                image,
                "--format",
                "{{.Manifest.Digest}}",
            )
            if not re.fullmatch(validation_pattern("image_digest"), digest):
                raise ValueError("invalid published image digest")
            sources.append(f"{name}@{digest}")
            command("docker", "image", "rm", image)
        print(f"Publishing multi-platform index: {release}", flush=True)
        command("docker", "buildx", "imagetools", "create", "--tag", release, *sources)

    digest = command(
        "docker",
        "buildx",
        "imagetools",
        "inspect",
        release,
        "--format",
        "{{.Manifest.Digest}}",
    )
    if not re.fullmatch(validation_pattern("image_digest"), digest):
        raise ValueError("invalid published index digest")
    image = f"{name}@{digest}"
    command(
        "bash",
        "scripts/check_image_tag.sh",
        env={**env, "IMAGE_REF": image, "REQUIRE_IMAGE": "true"},
    )
    print(f"Updating PR #{pull['number']} with verified image pin", flush=True)
    append_pin(repository, pull, image)
