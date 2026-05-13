"""Example pypi-profile plugin — proves two plugins can coexist."""

from john_doe.__about__ import __version__

from pypi_profile.plugin_spec import hookimpl

__all__ = ["__version__"]


@hookimpl
def get_profile_data() -> dict:  # type: ignore[type-arg]
    """Return John Doe's profile data."""
    return {
        "author": "John Doe",
        "pypi_username": "john_doe",
        "github": "https://github.com/john_doe",
    }
