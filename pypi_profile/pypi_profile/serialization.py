"""Shared JSON and TOML helpers with optional fast backends."""

from __future__ import annotations

import json as stdlib_json
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, cast

orjson: Optional[types.ModuleType]
try:
    import orjson  # type: ignore[import-not-found]
except ImportError:
    orjson = None

rtoml: Optional[types.ModuleType]
try:
    import rtoml  # type: ignore[import-not-found]
except ImportError:
    rtoml = None

if sys.version_info >= (3, 11):
    import tomllib as stdlib_toml
else:
    try:
        import tomllib as stdlib_toml
    except ImportError:
        import tomli as stdlib_toml

JSON_BACKEND = "orjson" if orjson is not None else "json"
TOML_BACKEND = "rtoml" if rtoml is not None else stdlib_toml.__name__

JSONDecodeError = (
    orjson.JSONDecodeError if orjson is not None else stdlib_json.JSONDecodeError
)


class TOMLDecodeError(ValueError):
    """Raised when TOML parsing fails across supported backends."""


def _normalize_text(data: str | bytes | bytearray | memoryview) -> str:
    if isinstance(data, str):
        return data
    return bytes(data).decode("utf-8")


def json_loads(data: str | bytes | bytearray | memoryview) -> Any:
    """Load JSON from text or bytes, preferring orjson when available."""
    if orjson is not None:
        return orjson.loads(data)
    return stdlib_json.loads(_normalize_text(data))


def json_dumps(
    value: Any,
    *,
    indent: int | None = None,
    sort_keys: bool = False,
    separators: tuple[str, str] | None = None,
    default: Callable[[Any], Any] | None = None,
) -> str:
    """Dump JSON to text, using orjson when the requested options fit."""
    if orjson is not None and separators in (None, (",", ":")) and indent in (None, 2):
        option = 0
        if sort_keys:
            option |= orjson.OPT_SORT_KEYS
        if indent == 2:
            option |= orjson.OPT_INDENT_2
        return cast(bytes, orjson.dumps(value, default=default, option=option)).decode(
            "utf-8"
        )
    return stdlib_json.dumps(
        value,
        indent=indent,
        sort_keys=sort_keys,
        separators=separators,
        default=default,
    )


def json_dumps_bytes(
    value: Any,
    *,
    indent: int | None = None,
    sort_keys: bool = False,
    separators: tuple[str, str] | None = None,
    default: Callable[[Any], Any] | None = None,
) -> bytes:
    """Dump JSON to UTF-8 bytes."""
    if orjson is not None and separators in (None, (",", ":")) and indent in (None, 2):
        option = 0
        if sort_keys:
            option |= orjson.OPT_SORT_KEYS
        if indent == 2:
            option |= orjson.OPT_INDENT_2
        return cast(bytes, orjson.dumps(value, default=default, option=option))
    return json_dumps(
        value,
        indent=indent,
        sort_keys=sort_keys,
        separators=separators,
        default=default,
    ).encode("utf-8")


def toml_load(source: str | Path | Any) -> dict[str, Any]:
    """Load TOML from a path, file handle, or string."""
    if rtoml is not None:
        try:
            return cast(dict[str, Any], rtoml.load(source))
        except rtoml.TomlParsingError as exc:
            raise TOMLDecodeError(str(exc)) from exc

    try:
        if isinstance(source, Path):
            with open(source, "rb") as fh:
                return cast(dict[str, Any], stdlib_toml.load(fh))
        if hasattr(source, "read"):
            return cast(dict[str, Any], stdlib_toml.load(source))
        return cast(dict[str, Any], stdlib_toml.loads(_normalize_text(source)))
    except stdlib_toml.TOMLDecodeError as exc:
        raise TOMLDecodeError(str(exc)) from exc


def toml_load_path(path: Path) -> dict[str, Any]:
    """Load TOML from *path*."""
    return toml_load(path)
