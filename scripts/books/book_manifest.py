#!/usr/bin/env python3

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

import yaml

from scripts.repository.config.validation_patterns import validation_pattern
from scripts.repository.file_updates import source_updates, write_updates
from scripts.repository.source_reads import field_mapping, read_yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "config/books.yml"
SLUG_PATTERN = re.compile("^" + validation_pattern("book_slug") + "$")
LABEL_PREFIX_PATTERN = re.compile(validation_pattern("label_prefix"))
LEAN_MODULE_PATTERN = re.compile(validation_pattern("lean_name"))
STATUS_LABELS = {
    "draft": "Draft",
    "review": "In Review",
    "published": "Published",
    "archived": "Archived",
}
ALLOWED_STATUSES = frozenset(STATUS_LABELS)
ROOT_FIELDS = {"schema_version", "defaults", "books"}
DEFAULT_FIELDS = {"author", "version", "status", "build", "check", "release", "site"}
BOOK_FIELDS = {
    "slug",
    "title",
    "author",
    "version",
    "status",
    "order",
    "label_prefix",
    "lean_module",
    "build",
    "check",
    "release",
    "site",
}


class BookMetadata(TypedDict):
    slug: str
    title: str
    author: str
    version: str
    status: str
    order: int
    label_prefix: str
    lean_module: NotRequired[str]
    build: bool
    check: bool
    release: bool
    site: bool


def version_key(value: str) -> tuple:
    """SemVer precedence, excluding build metadata (unsupported by config/books.yml)."""
    match = re.fullmatch(
        validation_pattern("book_version"),
        value,
    )
    if not match:
        raise ValueError(f"invalid semantic version: {value}")
    major, minor, patch, suffix = match.groups()
    identifiers = []
    for part in suffix.split(".") if suffix else []:
        if part.isdigit():
            if len(part) > 1 and part.startswith("0"):
                raise ValueError(f"invalid numeric prerelease identifier: {value}")
            identifiers.append((0, int(part)))
        else:
            identifiers.append((1, part))
    return (int(major), int(minor), int(patch), suffix is None, tuple(identifiers))


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = read_yaml(path)
    except FileNotFoundError as error:
        raise ValueError(f"manifest not found: {path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"invalid YAML in {path}: {error}") from error

    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")
    return data


def read_raw_manifest() -> dict[str, Any]:
    data = _read_yaml(MANIFEST_PATH)
    if not isinstance(data.get("books"), list):
        raise ValueError("'books' must be a list")
    return data


def save_manifest(manifest: dict[str, Any]) -> None:
    with source_updates(REPO_ROOT):
        normalized = normalize_manifest(manifest)
        _validate_book_files(normalized, REPO_ROOT)
        text = yaml.safe_dump(
            manifest,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
        write_updates({MANIFEST_PATH: text}, durable=True)


def validate_new_book_input(slug: str, title: str) -> None:
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError(
            "slug must contain lowercase letters/numbers separated by single hyphens"
        )

    if not title.strip() or "\n" in title or "\r" in title:
        raise ValueError("title must be a non-empty single line")


def suggested_label_prefix(slug: str) -> str:
    """Return the stable default prefix used when scaffolding a new book."""
    return "".join(part[0] for part in slug.split("-"))


def add_book(
    slug: str, title: str, *, release: bool | None = None, site: bool | None = None
) -> None:
    with source_updates(REPO_ROOT):
        _add_book(slug, title, release=release, site=site)


def _add_book(
    slug: str, title: str, *, release: bool | None, site: bool | None
) -> None:
    validate_new_book_input(slug, title)
    title = title.strip()

    load_manifest()
    manifest = read_raw_manifest()
    books = manifest["books"]

    if any(book.get("slug") == slug for book in books):
        raise ValueError(f"book is already registered: {slug}")

    orders = [book["order"] for book in books if isinstance(book.get("order"), int)]
    next_order = max(orders, default=0) + 10

    record = {
        "slug": slug,
        "title": title,
        "version": "0.1.0",
        "label_prefix": suggested_label_prefix(slug),
        "status": "draft",
        "order": next_order,
    }
    for name, value in (("release", release), ("site", site)):
        if value is not None:
            record[name] = value
    books.append(record)

    books.sort(
        key=lambda book: (
            book.get("order", 0),
            book.get("slug", ""),
        )
    )

    save_manifest(manifest)


def load_manifest(
    path: Path = MANIFEST_PATH,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    if repository_root is None:
        repository_root = REPO_ROOT

    data = normalize_manifest(_read_yaml(path))
    _validate_book_files(data, repository_root)
    return data


def _validate_book_files(data: dict[str, Any], repository_root: Path) -> None:
    for book in data["books"]:
        slug = book["slug"]
        book_dir = repository_root / "books" / slug
        if not (book_dir / "book.tex").is_file():
            raise ValueError(f"book '{slug}' is missing books/{slug}/book.tex")


def _validate_defaults(defaults: object) -> dict[str, Any]:
    defaults = field_mapping(defaults, "'defaults'")

    unknown_default_fields = set(defaults) - DEFAULT_FIELDS
    if unknown_default_fields:
        raise ValueError(
            "defaults has unknown field(s): "
            + ", ".join(sorted(unknown_default_fields))
        )

    for flag, value in defaults.items():
        if flag == "version":
            if not isinstance(value, str):
                raise ValueError("defaults field 'version' must be a semantic version")
            version_key(value)
            continue
        if flag == "status":
            if not isinstance(value, str) or value not in ALLOWED_STATUSES:
                raise ValueError(f"defaults field 'status' is invalid: {value!r}")
            continue
        if flag == "author":
            if (
                not isinstance(value, str)
                or not value.strip()
                or "\n" in value
                or "\r" in value
            ):
                raise ValueError("defaults field 'author' must be a non-empty line")
            continue
        if not isinstance(value, bool):
            raise ValueError(f"defaults field '{flag}' must be boolean")

    return defaults


def _validate_book_description(book: dict[str, Any]) -> None:
    slug = book.get("slug")
    title = book.get("title")
    author = book.get("author")
    version = book.get("version")

    if (
        not isinstance(title, str)
        or not title.strip()
        or "\n" in title
        or "\r" in title
    ):
        raise ValueError(f"book '{slug}' must have a non-empty single-line title")

    if (
        not isinstance(author, str)
        or not author.strip()
        or "\n" in author
        or "\r" in author
    ):
        raise ValueError(f"book '{slug}' must have a non-empty single-line author")

    if not isinstance(version, str):
        raise ValueError(f"book '{slug}' has an invalid version")
    try:
        version_key(version)
    except ValueError as error:
        raise ValueError(f"book '{slug}' has an invalid version: {error}") from error


def _validate_book_automation(book: dict[str, Any]) -> None:
    slug = book.get("slug")
    status = book.get("status")
    order = book.get("order")

    if not isinstance(status, str) or status not in ALLOWED_STATUSES:
        raise ValueError(f"book '{slug}' has invalid status: {status!r}")

    if not isinstance(order, int) or isinstance(order, bool):
        raise ValueError(f"book '{slug}' must have an integer order")

    for flag in ("build", "check", "release", "site"):
        if not isinstance(book.get(flag), bool):
            raise ValueError(f"book '{slug}' field '{flag}' must be boolean")

    if book["site"] and not book["build"]:
        raise ValueError(f"book '{slug}' cannot have site=true when build=false")


def _normalize_books(books: list, defaults: dict[str, Any]) -> list[BookMetadata]:
    normalized_books: list[BookMetadata] = []
    seen_slugs: set[str] = set()
    seen_label_prefixes: set[str] = set()
    seen_lean_modules: set[str] = set()

    for index, raw_book in enumerate(books, start=1):
        raw_book = field_mapping(raw_book, f"books[{index}]")

        unknown_book_fields = set(raw_book) - BOOK_FIELDS
        if unknown_book_fields:
            raise ValueError(
                f"books[{index}] has unknown field(s): "
                + ", ".join(sorted(unknown_book_fields))
            )

        book = {**defaults, **raw_book}

        slug = book.get("slug")

        if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug):
            raise ValueError(f"books[{index}] has an invalid slug")

        if slug in seen_slugs:
            raise ValueError(f"duplicate book slug: {slug}")
        seen_slugs.add(slug)

        _validate_book_description(book)

        label_prefix = book.get("label_prefix", suggested_label_prefix(slug))
        if not isinstance(label_prefix, str) or not LABEL_PREFIX_PATTERN.fullmatch(
            label_prefix
        ):
            raise ValueError(
                f"book '{slug}' must have a lowercase alphanumeric label_prefix"
            )
        if label_prefix in seen_label_prefixes:
            raise ValueError(f"duplicate label_prefix: {label_prefix}")
        seen_label_prefixes.add(label_prefix)
        book["label_prefix"] = label_prefix

        lean_module = book.get("lean_module")
        if lean_module is not None:
            if not isinstance(lean_module, str) or not LEAN_MODULE_PATTERN.fullmatch(
                lean_module
            ):
                raise ValueError(f"book '{slug}' has an invalid lean_module")
            if lean_module in seen_lean_modules:
                raise ValueError(f"duplicate lean_module: {lean_module}")
            seen_lean_modules.add(lean_module)

        _validate_book_automation(book)

        normalized_books.append(cast(BookMetadata, book))

    return sorted(
        normalized_books,
        key=lambda book: (book["order"], book["slug"]),
    )


def normalize_manifest(data: object) -> dict[str, Any]:
    """Validate metadata independently of checkout files, including old revisions."""
    data = dict(field_mapping(data, "manifest root"))

    unknown_root_fields = set(data) - ROOT_FIELDS
    if unknown_root_fields:
        raise ValueError(
            "manifest has unknown field(s): " + ", ".join(sorted(unknown_root_fields))
        )

    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported or missing schema_version")

    defaults = _validate_defaults(data.get("defaults", {}))
    books = data.get("books")
    if not isinstance(books, list):
        raise ValueError("'books' must be a list")

    data["books"] = _normalize_books(books, defaults)
    return data


def manifest_warnings(manifest: dict[str, Any]) -> list[str]:
    """Return suspicious, non-fatal manifest configurations."""
    warnings: list[str] = []
    orders: dict[int, list[str]] = {}
    for book in manifest["books"]:
        orders.setdefault(book["order"], []).append(book["slug"])
        if book["status"] == "archived" and book["release"]:
            warnings.append(
                f"book '{book['slug']}' is archived but release=true; "
                "archived books are normally excluded from new releases"
            )
        if book["status"] == "archived" and book["site"]:
            warnings.append(
                f"book '{book['slug']}' is archived but site=true; "
                "confirm that it should remain published on the site"
            )
        if book["status"] == "draft" and book["release"]:
            warnings.append(
                f"book '{book['slug']}' is draft but release=true; "
                "draft books are normally excluded from official releases"
            )
    for order, slugs in sorted(orders.items()):
        if len(slugs) > 1:
            warnings.append(
                f"duplicate order {order} is used by {', '.join(slugs)}; "
                "display order will fall back to slug ordering"
            )
    return warnings


def require_book(slug: str) -> BookMetadata:
    manifest = load_manifest()
    for book in manifest["books"]:
        if book["slug"] == slug:
            return cast(BookMetadata, book)
    raise ValueError(f"book is not registered in config/books.yml: {slug}")
