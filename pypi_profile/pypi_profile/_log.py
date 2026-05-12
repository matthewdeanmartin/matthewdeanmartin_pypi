"""Central logging configuration for pypi-profile."""

from __future__ import annotations

import logging


def configure_logging(level: str | int = logging.WARNING) -> None:
    """Set up a stderr handler on the root pypi_profile logger.

    Called once from cli.main() based on --log-level / --verbose.
    Library users who import pypi_profile without the CLI get the
    standard "no handler" behaviour (NullHandler) unless they configure
    logging themselves.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.WARNING)

    root = logging.getLogger("pypi_profile")
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        fmt = logging.Formatter("%(levelname)s %(name)s: %(message)s")
        handler.setFormatter(fmt)
        root.addHandler(handler)
    else:
        for h in root.handlers:
            h.setLevel(level)
