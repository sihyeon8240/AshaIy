"""Generate macro packages and select synchronized declarations by source owner."""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.books.book_manifest import load_manifest
from scripts.latex.command_specs import BUILTIN_COMMANDS, CommandSpec
from scripts.latex.macro_manifest import load_macros, render_macros
from scripts.repository.file_updates import changed_files, write_updates
from scripts.repository.source_reads import read_text

ROOT = Path(__file__).resolve().parents[2]
GENERATED_NAME = "generated-macros.sty"


@dataclass(frozen=True)
class MacroRegistry:
    commands: dict[str, CommandSpec]
    updates: dict[Path, str]
    fingerprint: bytes

    def check(self) -> None:
        stale = changed_files(self.updates)
        if stale:
            raise ValueError(
                f"{stale[0]}: generated macros are stale; run ashaiy macros generate"
            )


class MacroRepository:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root.resolve()
        self.registries: dict[str | None, MacroRegistry] = {}

    def books(self) -> list[str]:
        manifest = load_manifest(
            self.root / "config/books.yml", repository_root=self.root
        )
        return [book["slug"] for book in manifest["books"]]

    def registry(self, book: str | None = None, *, check: bool = True) -> MacroRegistry:
        if book not in self.registries:
            if book is not None and book not in self.books():
                raise ValueError(f"unknown macro book: {book}")
            manifests = [
                (
                    self.root / "common/styles/macros.yml",
                    self.root / "common/styles" / GENERATED_NAME,
                    "generated-macros",
                )
            ]
            if book is not None:
                book_root = self.root / "books" / book
                path = book_root / "styles/macros.yml"
                generated = book_root / "styles" / GENERATED_NAME
                if path.is_file():
                    manifests.append((path, generated, "styles/generated-macros"))
                elif generated.exists():
                    raise ValueError(
                        f"{generated}: generated macros have no macros.yml owner"
                    )
            commands = dict(BUILTIN_COMMANDS)
            updates = {}
            digest = hashlib.sha256()
            for path, output, package in manifests:
                declarations = load_macros(path)
                duplicate = commands.keys() & declarations.keys()
                if duplicate:
                    raise ValueError(
                        f"{path}: duplicate macro names: {', '.join(sorted(duplicate))}"
                    )
                commands.update(
                    {name: macro.spec for name, macro in declarations.items()}
                )
                updates[output] = render_macros(
                    declarations, path.relative_to(self.root).as_posix(), package
                )
                digest.update(path.relative_to(self.root).as_posix().encode())
                digest.update(read_text(path).encode())
            self.registries[book] = MacroRegistry(commands, updates, digest.digest())
        registry = self.registries[book]
        if check:
            registry.check()
        return registry

    def for_source(self, source: Path) -> MacroRegistry:
        try:
            relative = source.resolve().relative_to(self.root / "books")
        except ValueError:
            return self.registry()
        if len(relative.parts) < 2:
            return self.registry()
        return self.registry(relative.parts[0])


def generate(*, book: str | None = None, check: bool = False, root: Path = ROOT) -> int:
    repository = MacroRepository(root)
    books = repository.books()
    if book is not None and book not in books:
        raise ValueError(f"unknown macro book: {book}")
    registered = set(books)
    for path in (root / "books").glob("*/styles/macros.yml"):
        if path.parents[1].name not in registered:
            raise ValueError(f"{path}: macro manifest belongs to an unregistered book")
    updates = dict(repository.registry(check=False).updates)
    for slug in [book] if book is not None else books:
        updates.update(repository.registry(slug, check=False).updates)
    stale = changed_files(updates) if check else write_updates(updates)
    if check and stale:
        for path in stale:
            print(
                f"{path}: error: generated macros are stale; run ashaiy macros generate",
                file=sys.stderr,
            )
        return 1
    print(f"{'Validated' if check else 'Generated'} {len(updates)} macro package(s).")
    return 0


if __name__ == "__main__":
    from scripts.cli.repository_cli import main

    raise SystemExit(main(["macros", *sys.argv[1:]]))
