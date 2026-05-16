"""Tests for JSON/TOML serialization helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypi_profile.serialization import json_dumps, json_dumps_bytes, json_loads, toml_load, toml_load_path


def test_json_helpers_round_trip() -> None:
    payload: dict[str, Any] = {"name": "Alice", "items": [1, 2, 3]}

    encoded = json_dumps(payload, sort_keys=True)

    assert json_loads(encoded) == payload


def test_json_dumps_bytes_uses_utf8() -> None:
    encoded = json_dumps_bytes({"message": "hello"}, separators=(",", ":"))

    assert encoded == b'{"message":"hello"}'


def test_json_dumps_supports_default_callback() -> None:
    payload = {"path": Path("demo.txt")}

    encoded = json_dumps(payload, default=str)

    assert json_loads(encoded) == {"path": "demo.txt"}


def test_toml_helpers_load_from_path_and_file(tmp_path: Path) -> None:
    toml_path = tmp_path / "profile.toml"
    toml_path.write_text('[profile]\ndisplay_name = "Alice"\n', encoding="utf-8")

    assert toml_load_path(toml_path)["profile"]["display_name"] == "Alice"

    with open(toml_path, "rb") as fh:
        assert toml_load(fh)["profile"]["display_name"] == "Alice"
