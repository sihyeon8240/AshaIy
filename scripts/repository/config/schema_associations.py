"""Share schema targets between repository checks and editor projections."""

from __future__ import annotations

from pathlib import Path

from scripts.repository.config.json_config import read_json


def load_associations(root: Path) -> dict:
    path = root / "config/schema-associations.json"
    data = read_json(path)
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "yaml", "json"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
    ):
        raise ValueError(f"{path}: expected schema association version 1")
    for language in ("yaml", "json"):
        associations = data[language]
        if not isinstance(associations, dict):
            raise ValueError(f"{path}: {language} must map schemas to file patterns")
        for schema, patterns in associations.items():
            if (
                not isinstance(schema, str)
                or not schema.startswith("config/schemas/")
                or not schema.endswith(".json")
                or ".." in Path(schema).parts
                or not isinstance(patterns, list)
                or not patterns
                or any(
                    not isinstance(pattern, str) or not pattern.startswith("/") or ".." in Path(pattern).parts
                    for pattern in patterns
                )
                or len(patterns) != len(set(patterns))
            ):
                raise ValueError(f"{path}: invalid schema association: {schema}")
    return data


def editor_associations(root: Path) -> dict:
    data = load_associations(root)
    return {
        "yaml.schemas": {f"./{schema}": patterns for schema, patterns in data["yaml"].items()},
        "json.schemas": [{"fileMatch": patterns, "url": f"./{schema}"} for schema, patterns in data["json"].items()],
    }
