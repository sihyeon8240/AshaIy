"""Load and validate repository-wide toolchain configuration."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from scripts.validation_patterns import validation_pattern
except ModuleNotFoundError:
    from validation_patterns import validation_pattern

ROOT = Path(__file__).resolve().parent.parent
TOOLCHAIN_PATH = ROOT / "config/toolchain.env"
IMAGE_PATH = ROOT / "config/container-image.txt"

ASSIGNMENT = re.compile(r"([A-Z][A-Z0-9_]*)=([A-Za-z0-9._:/+-]+)")
IMAGE = re.compile(validation_pattern("pinned_image"))
SHA256 = re.compile(validation_pattern("sha256"))
REQUIRED_TOOLCHAIN_KEYS = {
    "TEXLIVE_YEAR",
    "TEXLIVE_ARCHIVE_DATE",
    "TEXLIVE_INSTALLER_SHA256",
    "PYTHON_VERSION",
    "PYTHON_SERIES",
    "ELAN_VERSION",
    "ELAN_SHA256_AMD64",
    "ELAN_SHA256_ARM64",
    "RUFF_VERSION",
    "RUFF_SHA256_AMD64",
    "RUFF_SHA256_ARM64",
    "SHELLCHECK_VERSION",
    "SHELLCHECK_SHA256_AMD64",
    "SHELLCHECK_SHA256_ARM64",
    "SHFMT_VERSION",
    "SHFMT_SHA256_AMD64",
    "SHFMT_SHA256_ARM64",
    "LATEXINDENT_VERSION",
    "LATEXINDENT_RELEASE_DATE",
    "LATEXINDENT_SHA256_AMD64",
    "LATEXINDENT_SHA256_ARM64",
    "PYYAML_VERSION",
    "PLAYWRIGHT_VERSION",
    "HYPOTHESIS_VERSION",
    "COVERAGE_VERSION",
    "BASEDPYRIGHT_VERSION",
    "YAMLLINT_VERSION",
    "DJLINT_VERSION",
    "CHECK_JSONSCHEMA_VERSION",
    "JEKYLL_VERSION",
    "BUNDLER_VERSION",
    "ACTIONLINT_VERSION",
    "ACTIONLINT_SHA256_AMD64",
    "LEAN_VERSION",
    "LEAN_TOOLCHAIN",
    "GH_VERSION",
    "GH_SHA256_AMD64",
    "GH_SHA256_ARM64",
}


def load_toolchain(path: Path = TOOLCHAIN_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = ASSIGNMENT.fullmatch(line)
        if not match:
            raise ValueError(f"{path}:{number}: invalid configuration assignment")
        key, value = match.groups()
        if key in values:
            raise ValueError(f"{path}:{number}: duplicate key {key}")
        values[key] = value
    missing = sorted(REQUIRED_TOOLCHAIN_KEYS - values.keys())
    extra = sorted(values.keys() - REQUIRED_TOOLCHAIN_KEYS)
    if missing:
        raise ValueError(f"{path}: missing keys: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{path}: unknown keys: {', '.join(extra)}")
    for key in (key for key in values if "SHA256" in key):
        if not SHA256.fullmatch(values[key]):
            raise ValueError(f"{path}: {key} must be a lowercase SHA-256 digest")
    if not values["PYTHON_VERSION"].startswith(values["PYTHON_SERIES"] + "."):
        raise ValueError(f"{path}: PYTHON_VERSION must match PYTHON_SERIES")
    expected_lean = f"leanprover/lean4:v{values['LEAN_VERSION']}"
    if values["LEAN_TOOLCHAIN"] != expected_lean:
        raise ValueError(f"{path}: LEAN_TOOLCHAIN must be {expected_lean}")
    return values


def load_image(path: Path = IMAGE_PATH) -> str:
    image = path.read_text(encoding="utf-8").strip()
    if not IMAGE.fullmatch(image):
        raise ValueError(f"{path}: expected an immutable GHCR image reference")
    return image


def image_name(image: str) -> str:
    return image.split("@", 1)[0]


def load_image_build(root: Path = ROOT) -> dict:
    path = root / "config/image-build.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "policy_version", "inputs", "platforms"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
    ):
        raise ValueError(f"{path}: unsupported image build configuration")
    if not isinstance(data["policy_version"], str) or not re.fullmatch(
        r"[A-Za-z0-9-]+", data["policy_version"]
    ):
        raise ValueError(f"{path}: invalid policy version")
    inputs = data["inputs"]
    if (
        not isinstance(inputs, list)
        or not inputs
        or not all(
            isinstance(item, str)
            and re.fullmatch(validation_pattern("relative_path"), item)
            and not any(part in {".", ".."} for part in item.split("/"))
            for item in inputs
        )
    ):
        raise ValueError(f"{path}: inputs must be repository-relative file paths")
    if len(inputs) != len(set(inputs)) or "config/image-build.json" not in inputs:
        raise ValueError(f"{path}: inputs must be unique and include the configuration")
    platforms = data["platforms"]
    if not isinstance(platforms, list) or not platforms:
        raise ValueError(f"{path}: platforms must be a nonempty list")
    for platform in platforms:
        if (
            not isinstance(platform, dict)
            or set(platform) != {"arch", "runner"}
            or not all(
                isinstance(value, str) and re.fullmatch(r"[a-z0-9.-]+", value)
                for value in platform.values()
            )
        ):
            raise ValueError(f"{path}: invalid platform or runner")
    architectures = [platform["arch"] for platform in platforms]
    if len(architectures) != len(set(architectures)) or "amd64" not in architectures:
        raise ValueError(
            f"{path}: architectures must be unique and include the PR consumer's amd64 platform"
        )
    return data


def load_authoring(root: Path = ROOT) -> dict:
    path = root / "config/authoring.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or set(data)
        != {"schema_version", "shell_args", "test_directory", "test_pattern"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
    ):
        raise ValueError(f"{path}: unsupported authoring configuration")
    args = data["shell_args"]
    if (
        not isinstance(args, list)
        or len(args) != 4
        or args[:3] != ["-ln", "bash", "-i"]
        or not isinstance(args[3], str)
        or not re.fullmatch(validation_pattern("positive_integer"), args[3])
    ):
        raise ValueError(
            f"{path}: expected bash shell arguments with positive indentation"
        )
    for key in ("test_directory", "test_pattern"):
        if (
            not isinstance(data[key], str)
            or not re.fullmatch(r"[A-Za-z0-9_.*-]+", data[key])
            or data[key] in {".", ".."}
        ):
            raise ValueError(f"{path}: invalid {key}")
    return data
