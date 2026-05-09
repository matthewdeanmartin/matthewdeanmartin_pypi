"""Smoke tests for the matthewdeanmartin plugin."""


def test_import() -> None:
    """Package can be imported."""
    import matthewdeanmartin

    assert matthewdeanmartin.__name__ == "matthewdeanmartin"


def test_version() -> None:
    """Package exposes a version string."""
    from matthewdeanmartin.__about__ import __version__

    assert isinstance(__version__, str)
    assert __version__


def test_get_profile_data() -> None:
    """Hook implementation returns expected data."""
    from matthewdeanmartin import get_profile_data

    data = get_profile_data()
    assert data["pypi_username"] == "matthewdeanmartin"
