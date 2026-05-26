"""Scan the filesystem for pypi_profile.toml files and pyproject.toml with [tool.pypi-profile]."""

from __future__ import annotations

import os
import time
from pathlib import Path

from pypi_profile.serialization import TOMLDecodeError, toml_load

# Directories that are always skipped during the walk (case-insensitive exact name match).
SKIP_DIRS = {
    ".venv",
    "venv",
    ".env",
    "env",
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "temp",
    "site-packages",
    ".eggs",
}
PYPROJECT_SCAN_BYTES = 8192


def should_skip_dir(name: str) -> bool:
    """Return True when a directory should be skipped during scanning."""
    lowered = name.lower()
    return lowered in SKIP_DIRS or lowered.endswith(".egg-info")


def record_profile_match(
    entry: Path, direct: list[Path], via_pyproject: list[Path]
) -> None:
    """Append matching profile files to the appropriate result list."""
    if entry.name == "pypi_profile.toml":
        direct.append(entry)
        return
    if entry.name != "pyproject.toml":
        return
    try:
        if b"pypi-profile" not in entry.read_bytes()[:PYPROJECT_SCAN_BYTES]:
            return
    except OSError:
        return
    try:
        data = toml_load(entry)
        if "pypi-profile" in data.get("tool", {}):
            via_pyproject.append(entry)
    except (OSError, TOMLDecodeError):
        pass


def find_profile_files(
    root: Path | None = None,
    max_depth: int = 6,
    max_files: int | None = None,
    max_duration_ms: int | None = None,
) -> list[Path]:
    """Return all profile TOML paths under *root* (default: cwd), skipping heavy dirs.

    Finds:
    - Any file named ``pypi_profile.toml``
    - Any ``pyproject.toml`` that contains a ``[tool.pypi-profile]`` section

    The scan can be bounded by directory depth, file count, and elapsed time.

    Results are sorted: ``pypi_profile.toml`` files first, then ``pyproject.toml``,
    both groups in alphabetical order.
    """
    root = (root or Path.cwd()).resolve()
    direct: list[Path] = []
    via_pyproject: list[Path] = []
    scanned_files = 0
    stop_scan = False
    deadline = (
        None
        if max_duration_ms is None
        else time.perf_counter() + (max_duration_ms / 1000)
    )

    def should_stop() -> bool:
        if max_files is not None and scanned_files >= max_files:
            return True
        return deadline is not None and time.perf_counter() >= deadline

    def walk(directory: Path, depth: int) -> None:
        nonlocal scanned_files, stop_scan
        if stop_scan or should_stop():
            stop_scan = True
            return
        if depth > max_depth:
            return
        try:
            with os.scandir(directory) as entries:
                for raw_entry in entries:
                    if stop_scan or should_stop():
                        stop_scan = True
                        break
                    try:
                        if raw_entry.is_dir(follow_symlinks=False):
                            if should_skip_dir(raw_entry.name):
                                continue
                            walk(Path(raw_entry.path), depth + 1)
                        elif raw_entry.is_file(follow_symlinks=False):
                            scanned_files += 1
                            record_profile_match(
                                Path(raw_entry.path), direct, via_pyproject
                            )
                    except OSError:
                        continue
        except OSError:
            return

    walk(root, 0)
    return sorted(direct) + sorted(via_pyproject)
