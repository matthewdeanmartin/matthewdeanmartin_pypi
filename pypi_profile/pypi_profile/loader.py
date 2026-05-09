"""Load and parse pypi_profile.toml files."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

from pypi_profile.models import ProfileData


def load_profile(path: Path) -> ProfileData:
    """Read a pypi_profile.toml and return a validated ProfileData."""
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    return ProfileData.model_validate(raw)


def find_profile(source: str) -> Path:
    """Resolve a profile TOML path from a file path or package name.

    Accepts:
    - A direct .toml file path
    - A directory containing pypi_profile.toml
    - An installed package name (looks in dist-info)
    """
    candidate = Path(source)
    if candidate.suffix == ".toml" and candidate.exists():
        return candidate
    if candidate.is_dir():
        toml_in_dir = candidate / "pypi_profile.toml"
        if toml_in_dir.exists():
            return toml_in_dir
    # Try installed package dist-info
    try:
        import importlib.metadata as meta
        dist = meta.distribution(source)
        data_path = dist.locate_file("pypi_profile.toml")
        if Path(str(data_path)).exists():
            return Path(str(data_path))
    except meta.PackageNotFoundError:
        pass
    raise FileNotFoundError(f"Cannot find pypi_profile.toml for: {source!r}")
