"""Scan the filesystem for pypi_profile.toml files and pyproject.toml with [tool.pypi-profile]."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

# Directories that are always skipped during the walk (exact name match).
_SKIP_DIRS = {
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
    "site-packages",
    ".eggs",
    "*.egg-info",
}


def find_profile_files(root: Path | None = None, max_depth: int = 6) -> list[Path]:
    """Return all profile TOML paths under *root* (default: cwd), skipping heavy dirs.

    Finds:
    - Any file named ``pypi_profile.toml``
    - Any ``pyproject.toml`` that contains a ``[tool.pypi-profile]`` section

    Results are sorted: ``pypi_profile.toml`` files first, then ``pyproject.toml``,
    both groups in alphabetical order.
    """
    root = (root or Path.cwd()).resolve()
    direct: list[Path] = []
    via_pyproject: list[Path] = []

    def _walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(directory.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in _SKIP_DIRS or entry.name.endswith(".egg-info"):
                    continue
                _walk(entry, depth + 1)
            elif entry.is_file():
                if entry.name == "pypi_profile.toml":
                    direct.append(entry)
                elif entry.name == "pyproject.toml":
                    try:
                        with open(entry, "rb") as fh:
                            data = tomllib.load(fh)
                        if "pypi-profile" in data.get("tool", {}):
                            via_pyproject.append(entry)
                    except (OSError, tomllib.TOMLDecodeError):
                        pass

    _walk(root, 0)
    return sorted(direct) + sorted(via_pyproject)
