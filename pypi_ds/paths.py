from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent


def package_root_path() -> Path:
    return PACKAGE_ROOT


def template_root_path() -> Path:
    return PACKAGE_ROOT / "templates"


def static_root_path() -> Path:
    return PACKAGE_ROOT / "static"
