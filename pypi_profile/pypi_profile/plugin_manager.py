"""Loads pypi_profile.plugins entry-point plugins via pluggy."""

from __future__ import annotations

import importlib.metadata

import pluggy

from pypi_profile.plugin_spec import PypiProfileSpec

PROJECT_NAME = "pypi_profile"


def build_plugin_manager() -> pluggy.PluginManager:
    """Discover and register all installed plugins."""
    pm = pluggy.PluginManager(PROJECT_NAME)
    pm.add_hookspecs(PypiProfileSpec)
    for ep in importlib.metadata.entry_points(group=f"{PROJECT_NAME}.plugins"):
        plugin_module = ep.load()
        pm.register(plugin_module)
    return pm
