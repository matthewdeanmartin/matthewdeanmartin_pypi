"""Sphinx configuration for matthewdeanmartin docs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

project = "matthewdeanmartin"
copyright = "2024, Matthew Dean Martin"
author = "Matthew Dean Martin"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]
html_title = "matthewdeanmartin"

# MyST settings
myst_enable_extensions = ["colon_fence"]

autodoc_member_order = "bysource"
