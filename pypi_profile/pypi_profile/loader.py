"""Load and parse pypi_profile.toml files."""

from __future__ import annotations

import importlib.metadata as meta
import logging
from importlib import resources
from pathlib import Path

from pypi_profile.models import ProfileData
from pypi_profile.serialization import toml_load, toml_load_path

logger = logging.getLogger(__name__)


def load_profile(path: Path, *, autopatch_public_key: bool = True) -> ProfileData:
    """Read a profile TOML and return validated data.

    Args:
        path: Path to ``pypi_profile.toml`` or ``pyproject.toml``.
        autopatch_public_key: When True, opportunistically fill an empty
            ``[verification].public_key`` from the local key on disk.
    """
    logger.debug("Loading profile from %s", path)
    raw = toml_load_path(path)
    if path.name == "pyproject.toml":
        raw = raw.get("tool", {}).get("pypi-profile", {})
    profile = ProfileData.model_validate(raw)
    if (
        autopatch_public_key
        and not profile.verification.public_key
        and path.name == "pypi_profile.toml"
    ):
        try:
            from pypi_profile.signing import patch_public_key_in_toml

            pub_b64 = patch_public_key_in_toml(path)
            if pub_b64:
                profile.verification.public_key = pub_b64
        except (ImportError, OSError, ValueError):
            logger.warning(
                "Could not auto-patch public key into %s", path, exc_info=True
            )
    logger.debug("Loaded profile for %r", profile.profile.display_name)
    return profile


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


def find_installed_profile_files() -> list[Path]:
    """Return installed package resources named ``pypi_profile.toml`` in the current environment."""
    found: set[Path] = set()

    for dist in meta.distributions():
        for package_file in dist.files or []:
            if package_file.name != "pypi_profile.toml":
                continue
            candidate = Path(str(dist.locate_file(package_file)))
            if candidate.exists():
                found.add(candidate.resolve())

    for entry_point in meta.entry_points(group="pypi_profile.plugins"):
        module_name = entry_point.value.partition(":")[0]
        try:
            candidate = Path(
                str(resources.files(module_name).joinpath("pypi_profile.toml"))
            )
        except (ModuleNotFoundError, TypeError):
            continue
        if candidate.exists():
            found.add(candidate.resolve())

    return sorted(found)


def discover_installed_profiles() -> list[tuple[str, Path, ProfileData]]:
    """Return (package_name, toml_path, profile) for every installed profile in the current environment.

    Discovers profiles via:
    - ``pypi_profile.plugins`` entry points (preferred — explicit registration)
    - Any installed distribution that ships a ``pypi_profile.toml`` resource
    """
    seen_paths: dict[Path, str] = {}

    # Entry-point-registered plugins get a clean package name from the dist metadata.
    for entry_point in meta.entry_points(group="pypi_profile.plugins"):
        module_name = entry_point.value.partition(":")[0]
        try:
            candidate = Path(
                str(resources.files(module_name).joinpath("pypi_profile.toml"))
            )
        except (ModuleNotFoundError, TypeError):
            continue
        if candidate.exists():
            resolved = candidate.resolve()
            pkg_name = entry_point.dist.name if entry_point.dist else entry_point.name
            seen_paths.setdefault(resolved, pkg_name)

    # Fall back to scanning all distributions for a shipped pypi_profile.toml.
    for dist in meta.distributions():
        for package_file in dist.files or []:
            if package_file.name != "pypi_profile.toml":
                continue
            candidate = Path(str(dist.locate_file(package_file)))
            if candidate.exists():
                resolved = candidate.resolve()
                name = dist.metadata["Name"] or str(resolved)
                seen_paths.setdefault(resolved, name)

    results: list[tuple[str, Path, ProfileData]] = []
    for path in sorted(seen_paths):
        pkg_name = seen_paths[path]
        try:
            profile = load_profile(path, autopatch_public_key=False)
        except (ImportError, OSError, ValueError):
            logger.warning("Could not load profile from %s", path, exc_info=True)
            continue
        results.append((pkg_name, path, profile))

    return results


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
            data = toml_load(pyproject)
            if "pypi-profile" in data.get("tool", {}):
                return pyproject
    # Try installed package dist-info
    try:
        dist = meta.distribution(source)
        data_path = dist.locate_file("pypi_profile.toml")
        if Path(str(data_path)).exists():
            logger.debug("Found profile via dist-info for package %r", source)
            return Path(str(data_path))
    except meta.PackageNotFoundError:
        logger.debug("No installed package named %r", source)
    raise FileNotFoundError(f"Cannot find pypi_profile.toml for: {source!r}")
