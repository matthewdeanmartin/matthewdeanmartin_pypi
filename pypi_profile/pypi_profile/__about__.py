"""Metadata for pypi-profile."""

__all__ = [
    "__credits__",
    "__dependencies__",
    "__description__",
    "__keywords__",
    "__license__",
    "__readme__",
    "__requires_python__",
    "__status__",
    "__title__",
    "__version__",
]

__title__ = "pypi-profile"
__version__ = "0.1.0"
__description__ = "The missing PyPI(tm) profile page — pipx-installable, plugin-extensible. Not associated with PSF."
__readme__ = "README.md"
__credits__ = [{"name": "Matthew Martin", "email": "matthewdeanmartin@gmail.com"}]
__keywords__ = ["pypi", "profile", "cli"]
__license__ = "Apache-2.0"
__requires_python__ = ">=3.10"
__status__ = "3 - Alpha"
__dependencies__ = [
    "pluggy>=1.5.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "jinja2>=3.1.0",
    "pydantic>=2.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
    "prompt-toolkit>=3.0.0",
    "keyring>=25.7.0",
    "py-minisign>=0.13.2",
    "schema-resume-validator>=1.1.0",
]
