"""Pluggy hook specifications for pypi-profile plugins."""

from __future__ import annotations

import pluggy

hookspec = pluggy.HookspecMarker("pypi_profile")
hookimpl = pluggy.HookimplMarker("pypi_profile")


class PypiProfileSpec:
    """Hook specifications that plugins may implement."""

    @hookspec
    def get_profile_data(self) -> dict:  # type: ignore[empty-body]
        """Return a dict of profile data contributed by this plugin."""
