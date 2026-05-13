"""PyPI profile data and plugin for pypi-profile — Matthew Martin's packages."""

from matthewdeanmartin.__about__ import __version__

from pypi_profile.plugin_spec import hookimpl

__all__ = ["__version__"]


@hookimpl
def get_profile_data() -> dict:  # type: ignore[type-arg]
    """Return Matthew Martin's profile data."""
    return {
        "author": "Matthew Martin",
        "pypi_username": "matthewdeanmartin",
        "github": "https://github.com/matthewdeanmartin",
    }
