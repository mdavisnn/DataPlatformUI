from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MetadataReadError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    """Read one metadata object without ever opening it for writing."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise MetadataReadError(f"Metadata file is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise MetadataReadError(f"Metadata file could not be read: {path} ({exc})") from exc
    if not isinstance(value, dict):
        raise MetadataReadError(f"Expected a JSON object in: {path}")
    return value


def optional_json(path: Path) -> dict[str, Any] | None:
    return read_json(path) if path.is_file() else None

