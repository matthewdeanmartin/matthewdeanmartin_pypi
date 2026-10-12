"""Tests for bounded profile discovery."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from pytest import MonkeyPatch

from pypi_profile.finder import find_profile_files


class ScandirWrapper:
    """Provide a context manager around a deterministic scandir iterator."""

    def __init__(self, entries: list[os.DirEntry[str]]) -> None:
        self.entries = entries

    def __enter__(self) -> Iterator[os.DirEntry[str]]:
        return iter(self.entries)

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> Literal[False]:
        return False


def test_find_profile_files_skips_temp_and_venv(tmp_path: Path) -> None:
    (tmp_path / "keep").mkdir()
    (tmp_path / "keep" / "pypi_profile.toml").write_text("", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pypi_profile.toml").write_text("", encoding="utf-8")
    (tmp_path / "Temp").mkdir()
    (tmp_path / "Temp" / "pypi_profile.toml").write_text("", encoding="utf-8")

    found = find_profile_files(root=tmp_path)

    assert found == [tmp_path / "keep" / "pypi_profile.toml"]


def test_find_profile_files_respects_max_depth(tmp_path: Path) -> None:
    shallow = tmp_path / "a" / "b" / "c"
    shallow.mkdir(parents=True)
    (shallow / "pypi_profile.toml").write_text("", encoding="utf-8")

    too_deep = tmp_path / "a" / "b" / "c" / "d"
    too_deep.mkdir(parents=True)
    (too_deep / "pypi_profile.toml").write_text("", encoding="utf-8")

    found = find_profile_files(root=tmp_path, max_depth=3)

    assert found == [shallow / "pypi_profile.toml"]


def test_find_profile_files_respects_max_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    real_scandir = os.scandir

    for index in range(500):
        (tmp_path / f"{index:03}.txt").write_text("", encoding="utf-8")
    (tmp_path / "zzz").mkdir()
    profile = tmp_path / "zzz" / "pypi_profile.toml"
    profile.write_text("", encoding="utf-8")

    def sorted_scandir(path: str | os.PathLike[str]) -> ScandirWrapper:
        entries = list(real_scandir(path))
        entries.sort(key=lambda entry: entry.name)
        return ScandirWrapper(entries)

    monkeypatch.setattr(os, "scandir", sorted_scandir)

    found = find_profile_files(root=tmp_path, max_files=500)

    assert found == []
    assert find_profile_files(root=tmp_path) == [profile]


def test_find_profile_files_respects_time_budget(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    real_scandir = os.scandir

    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    (tmp_path / "profiles").mkdir()
    profile = tmp_path / "profiles" / "pypi_profile.toml"
    profile.write_text("", encoding="utf-8")

    def sorted_scandir(path: str | os.PathLike[str]) -> ScandirWrapper:
        entries = list(real_scandir(path))
        entries.sort(key=lambda entry: entry.name)
        return ScandirWrapper(entries)

    perf_counter_values = iter([0.0, 0.0, 0.0, 1.1])

    def fake_perf_counter() -> float:
        return next(perf_counter_values, 1.1)

    monkeypatch.setattr(os, "scandir", sorted_scandir)
    monkeypatch.setattr("pypi_profile.finder.time.perf_counter", fake_perf_counter)

    found = find_profile_files(root=tmp_path, max_duration_ms=1000)

    assert found == []
    assert find_profile_files(root=tmp_path) == [profile]


def test_find_profile_files_skips_pyproject_parse_without_marker(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.black]\nline-length = 120\n", encoding="utf-8")

    def fail_if_called(_path: Path) -> dict[str, object]:
        raise AssertionError("pyproject without pypi-profile marker should not be parsed")

    monkeypatch.setattr("pypi_profile.finder.toml_load", fail_if_called)

    assert find_profile_files(root=tmp_path) == []
