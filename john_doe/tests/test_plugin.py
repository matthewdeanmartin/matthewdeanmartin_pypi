"""Smoke tests for the john_doe plugin."""


def test_import() -> None:
    """Package can be imported."""
    import john_doe  # noqa: F401


def test_version() -> None:
    """Package exposes a version string."""
    from john_doe.__about__ import __version__

    assert isinstance(__version__, str)
    assert __version__


def test_get_profile_data() -> None:
    """Hook implementation returns expected data."""
    from john_doe import get_profile_data

    data = get_profile_data()
    assert data["pypi_username"] == "john_doe"
