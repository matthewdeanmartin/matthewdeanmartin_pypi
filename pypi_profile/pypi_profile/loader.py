"""Load and parse pypi_profile.toml files."""

from __future__ import annotations

import importlib.metadata as meta
import sys
from pathlib import Path

from pypi_profile.models import ProfileData

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib


def load_profile(path: Path) -> ProfileData:
    """Read a pypi_profile.toml (or pyproject.toml [tool.pypi-profile]) and return a validated ProfileData."""
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    if path.name == "pyproject.toml":
        raw = raw.get("tool", {}).get("pypi-profile", {})
    return ProfileData.model_validate(raw)


def find_resume(toml_path: Path) -> Path | None:
    """Look for resume.json adjacent to the given TOML or one directory up."""
    candidates = [
        toml_path.parent / "resume.json",
        toml_path.parent.parent / "resume.json",
        toml_path.parent / "resources" / "resume.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def find_profile(source: str) -> Path:
    """Resolve a profile TOML path from a file path or package name.

    Accepts:
    - A direct .toml file path (pypi_profile.toml or pyproject.toml)
    - A directory containing pypi_profile.toml or pyproject.toml with [tool.pypi-profile]
    - An installed package name (looks in dist-info)
    """
    candidate = Path(source)
    if candidate.suffix == ".toml" and candidate.exists():
        return candidate
    if candidate.is_dir():
        toml_in_dir = candidate / "pypi_profile.toml"
        if toml_in_dir.exists():
            return toml_in_dir
        pyproject = candidate / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as fh:
                data = tomllib.load(fh)
            if "pypi-profile" in data.get("tool", {}):
                return pyproject
    # Try installed package dist-info
    try:
        dist = meta.distribution(source)
        data_path = dist.locate_file("pypi_profile.toml")
        if Path(str(data_path)).exists():
            return Path(str(data_path))
    except meta.PackageNotFoundError:
        pass
    raise FileNotFoundError(f"Cannot find pypi_profile.toml for: {source!r}")
