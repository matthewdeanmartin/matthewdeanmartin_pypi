"""Smoke tests for the john-doe profile plugin."""

from pathlib import Path

TOML = Path(__file__).parent.parent / "john_doe" / "pypi_profile.toml"


def test_import() -> None:
    import john_doe

    assert john_doe.__name__ == "john_doe"


def test_version() -> None:
    from john_doe.__about__ import __version__

    assert isinstance(__version__, str)
    assert __version__


def test_get_profile_data() -> None:
    from john_doe import get_profile_data

    data = get_profile_data()
    assert data["pypi_username"] == "john_doe"


def test_toml_exists() -> None:
    assert TOML.exists(), f"pypi_profile.toml not found at {TOML}"


def test_toml_loads() -> None:
    from pypi_profile.loader import load_profile

    profile = load_profile(TOML)
    assert profile.identity.pypi_username == "john_doe"
    assert len(profile.packages) >= 1
    assert profile.hiring.open_to_work_since != "" or profile.hiring.employment_types == []
