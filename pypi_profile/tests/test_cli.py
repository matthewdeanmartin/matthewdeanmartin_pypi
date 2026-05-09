"""Smoke tests for the pypi_profile package."""


def test_import() -> None:
    """Package can be imported."""
    import pypi_profile  # noqa: F401


def test_version() -> None:
    """Package exposes a version string."""
    from pypi_profile.__about__ import __version__

    assert isinstance(__version__, str)
    assert __version__


def test_plugin_manager_builds() -> None:
    """Plugin manager initialises without error."""
    from pypi_profile.plugin_manager import build_plugin_manager

    pm = build_plugin_manager()
    assert pm is not None
