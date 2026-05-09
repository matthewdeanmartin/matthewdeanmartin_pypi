"""Tests for the ProfileData model and loader."""

import sys
from pathlib import Path

import pytest

JOHN_DOE_TOML = Path(__file__).parent.parent.parent / "john_doe" / "john_doe" / "pypi_profile.toml"
MATT_TOML = Path(__file__).parent.parent.parent / "matthewdeanmartin" / "matthewdeanmartin" / "pypi_profile.toml"


def test_empty_profile_has_defaults() -> None:
    from pypi_profile.models import ProfileData

    p = ProfileData()
    assert p.profile.kind == "individual"
    assert p.packages == []
    assert p.hiring.open_to_work is False


def test_load_john_doe_profile() -> None:
    from pypi_profile.loader import load_profile

    profile = load_profile(JOHN_DOE_TOML)
    assert profile.identity.pypi_username == "john_doe"
    assert profile.profile.kind == "individual"
    assert len(profile.packages) == 3
    assert len(profile.work_experience) == 2
    assert profile.hiring.consulting is True


def test_load_matthewdeanmartin_profile() -> None:
    from pypi_profile.loader import load_profile

    profile = load_profile(MATT_TOML)
    assert profile.identity.pypi_username == "matthewdeanmartin"
    assert len(profile.packages) >= 1


def test_find_profile_by_path() -> None:
    from pypi_profile.loader import find_profile

    found = find_profile(str(JOHN_DOE_TOML))
    assert found == JOHN_DOE_TOML


def test_find_profile_by_directory() -> None:
    from pypi_profile.loader import find_profile

    toml_dir = JOHN_DOE_TOML.parent
    found = find_profile(str(toml_dir))
    assert found == JOHN_DOE_TOML


def test_find_profile_missing_raises() -> None:
    from pypi_profile.loader import find_profile

    with pytest.raises(FileNotFoundError):
        find_profile("no-such-package-name-xyz")


def test_package_state_badge_values() -> None:
    from pypi_profile.models import PackageEntry

    pkg = PackageEntry(name="test", state="deprecated", role="maintainer")
    assert pkg.state == "deprecated"


def test_profile_link_defaults_to_self_asserted() -> None:
    from pypi_profile.models import ProfileLink

    link = ProfileLink(kind="github", label="GitHub", url="https://github.com/x")
    assert link.verification == "self_asserted"
