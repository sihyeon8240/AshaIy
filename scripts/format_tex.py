"""Run latexindent with source-preserving normalization and content-addressed checks."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.latex_scan import source_spans, without_comments_and_literals
from scripts.lean_source import ignored_spans
from scripts.normalize_eof import normalized_bytes
from scripts.validation_patterns import validation_pattern

ROOT = Path(__file__).resolve().parent.parent
LEAN_BLOCK = re.compile(
    rb"^([\t ]*)(\\begin\{lean\}[\t ]*(?:%[^\n]*)?\n)(.*?)"
    rb"^[\t ]*(\\end\{lean\}[\t ]*(?:%[^\n]*)?$)",
    re.MULTILINE | re.DOTALL,
)


def normalize_lean_indentation(source: bytes) -> bytes:
    def replace(match: re.Match[bytes]) -> bytes:
        indent, opening, body, closing = match.groups()
        prefixes = re.findall(rb"^([\t ]*)\S", body, re.MULTILINE)
        if prefixes:
            common = cast(bytes, os.path.commonprefix(prefixes))
            body = re.sub(
                rb"^" + re.escape(common) + rb"(?=[^\n]*\S)",
                lambda _: indent + b"  ",
                body,
                flags=re.MULTILINE,
            )
        return indent + opening + body + indent + closing

    return LEAN_BLOCK.sub(replace, source)


def format_file(file: Path) -> bytes:
    if not file.is_file():
        raise ValueError(f"FILE does not exist: {file}")
    settings = ROOT / "config/latexindent.yaml"
    source = file.read_text(encoding="utf-8")
    protected: dict[str, str] = {}
    for span in reversed(source_spans(source)):
        if span.kind == "comment":
            continue
        literal = source[span.start : span.end]
        if span.kind == "lean" and not any(
            kind == "literal" and "\n" in literal[start:end]
            for start, end, kind in ignored_spans(literal)
        ):
            continue
        marker = (
            f"ASHAIYLITERAL{span.start}X"
            + hashlib.sha256(literal.encode()).hexdigest().upper()
        )
        if marker in source:
            raise ValueError("literal protection marker already occurs in source")
        protected[marker] = literal
        source = source[: span.start] + marker + source[span.end :]
    with tempfile.TemporaryDirectory() as temporary:
        cruft = Path(temporary)
        wrapped = cruft / f"wrapped{file.suffix}"
        original = cruft / file.name
        original.write_text(source, encoding="utf-8")
        options = ["latexindent", f"--local={settings}", f"--cruft={cruft}"]
        result = subprocess.check_output(
            [*options, "--modifylinebreaks", str(original)]
        )
        wrapped.write_bytes(result)
        # The second pass corrects indentation added to short wrapped sentences.
        result = subprocess.check_output([*options, str(wrapped)])
    result = normalized_bytes(normalize_lean_indentation(result), collapse=True)
    text = result.decode()
    clean = without_comments_and_literals(text)
    labels = re.compile(
        r"(\\begin\{(?:theorem|lemma|proposition|corollary|definition|axiom|example|exercise|problem)\})[ \t]*\n[ \t]*(\\label\{[^}\n]+\})"
    )
    for match in reversed(list(labels.finditer(clean))):
        if text[match.end(1) : match.start(2)].isspace():
            text = text[: match.end(1)] + " " + text[match.start(2) :]
    result = text.encode()
    for marker, literal in protected.items():
        if result.count(marker.encode()) != 1:
            raise ValueError("latexindent changed a protected literal marker")
        result = result.replace(marker.encode(), literal.encode())
    return result


def selected_files(root: Path, file: Path | None) -> list[Path]:
    if file is None:
        output = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--", "*.tex", "*.sty"], cwd=root
        )
        return [
            Path(os.fsdecode(name))
            for name in output.split(b"\0")
            if name and (root / os.fsdecode(name)).is_file()
        ]
    path = file.resolve()
    if not path.is_relative_to(root) or path.suffix not in {".tex", ".sty"}:
        raise ValueError(
            "FILE must be an existing .tex or .sty file inside the repository"
        )
    if not path.is_file():
        raise ValueError(f"FILE does not exist: {path}")
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", str(path)], cwd=root, check=False
    )
    if result.returncode == 0:
        raise ValueError("FILE must not be ignored by Git")
    if result.returncode != 1:
        raise subprocess.CalledProcessError(result.returncode, result.args)
    return [path.relative_to(root)]


def cache_directory(root: Path) -> Path:
    digest = hashlib.sha256()
    # Include implementations and wrappers so any formatting change invalidates checks.
    for name in (
        "format_tex.py",
        "normalize_eof.py",
        "latex_scan.py",
        "lean_source.py",
        "format_tex.sh",
        "format_tex_file.sh",
        "normalize_eof.sh",
    ):
        digest.update((ROOT / "scripts" / name).read_bytes())
    digest.update((ROOT / "config/latexindent.yaml").read_bytes())
    version = subprocess.check_output(["latexindent", "--version"]).splitlines()[0]
    digest.update(version)
    cache = (
        Path(os.environ.get("FORMAT_TEX_CACHE_DIR", root / ".cache/latexindent"))
        / digest.hexdigest()
    )
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def prune_cache(cache: Path) -> None:
    """Remove obsolete generations only when no other formatter is using them."""
    for entry in cache.parent.iterdir():
        if (
            entry != cache
            and re.fullmatch(validation_pattern("sha256"), entry.name)
            and not entry.is_symlink()
            and entry.is_dir()
        ):
            shutil.rmtree(entry)


def format_sources(
    root: Path, *, check: bool, file: Path | None, prune: bool = False
) -> int:
    files = selected_files(root, file)
    if shutil.which("latexindent") is None:
        print("error: latexindent is required", file=sys.stderr)
        return 127
    cache = cache_directory(root)
    if prune:
        prune_cache(cache)
    print(
        f"[tex] {'checking' if check else 'formatting'} LaTeX source files", flush=True
    )
    cached = changed = status = 0
    for path in files:
        source = root / path
        original = source.read_bytes()
        content_hash = hashlib.sha256(original).hexdigest()
        entry = cache / hashlib.sha256(os.fsencode(path)).hexdigest()
        if entry.is_file() and entry.read_text().strip() == content_hash:
            cached += 1
            continue
        # Use repository-relative names for bulk formatting, as the existing CLI does.
        formatted = format_file(path)
        if formatted != original:
            if check:
                print(f"[tex] needs formatting: {path}", file=sys.stderr)
                status = 1
                continue
            source.write_bytes(formatted)
            changed += 1
            print(f"[tex] reformatted: {path}")
        entry.write_text(hashlib.sha256(formatted).hexdigest() + "\n")
    if status:
        return status
    if check:
        print(
            f"[tex] {len(files)} files checked, all correctly formatted ({cached} cached)"
        )
    else:
        print(
            f"[tex] {len(files)} files total: {cached} cached, "
            f"{changed} reformatted, {len(files) - cached - changed} unchanged"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--file", type=Path)
    parser.add_argument(
        "--prune-cache",
        action="store_true",
        help="remove obsolete cache generations; avoid concurrent formatter runs",
    )
    parser.add_argument(
        "--stdout", type=Path, help="format one file to stdout for the editor"
    )
    args = parser.parse_args()
    if args.stdout is not None and (
        args.check or args.file is not None or args.prune_cache
    ):
        parser.error(
            "--stdout cannot be combined with --check, --file, or --prune-cache"
        )
    try:
        if args.stdout is not None:
            sys.stdout.buffer.write(format_file(args.stdout))
            return 0
        # Resolve caller-relative paths before changing to the repository root.
        file = args.file.resolve() if args.file is not None else None
        root = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], text=True
            ).strip()
        )
        os.chdir(root)
        return format_sources(root, check=args.check, file=file, prune=args.prune_cache)
    except subprocess.CalledProcessError as error:
        return error.returncode
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2 if isinstance(error, ValueError) else 1


if __name__ == "__main__":
    raise SystemExit(main())
