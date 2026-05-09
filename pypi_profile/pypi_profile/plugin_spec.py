"""Pluggy hook specifications for pypi-profile plugins."""

from __future__ import annotations

from typing import Any

import pluggy

hookspec = pluggy.HookspecMarker("pypi_profile")
hookimpl = pluggy.HookimplMarker("pypi_profile")


class PypiProfileSpec:
    """Hook specifications that plugins may implement."""

    @hookspec
    def get_profile_data(self) -> dict[str, Any]:  # type: ignore[empty-body]
        """Return a dict of profile data contributed by this plugin."""
