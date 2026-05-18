"""Helpers for integrating with skip_trace without creating a reverse dependency."""

from __future__ import annotations

import importlib.metadata as meta
import subprocess
from pathlib import Path
from typing import Any

from pypi_profile.serialization import json_loads


def _site_packages_from_python(python_executable: Path) -> list[Path]:
    command = [
        str(python_executable),
        "-c",
        "import json, site; print(json.dumps(site.getsitepackages()))",
    ]
    output = subprocess.check_output(command, text=True)
    raw_paths = json_loads(output)
    return [Path(str(path)).resolve() for path in raw_paths]


def resolve_site_packages(target: Path | None = None) -> list[Path]:
    """Resolve one or more site-packages directories from a venv root, python executable, or direct path."""
    if target is None:
        return []

    resolved = target.expanduser().resolve()
    if resolved.is_file():
        return _site_packages_from_python(resolved)
    if resolved.name == "site-packages":
        return [resolved]

    candidates = [
        resolved / "Lib" / "site-packages",
        *resolved.glob("lib/python*/site-packages"),
    ]
    return [candidate.resolve() for candidate in candidates if candidate.exists()]


def list_installed_package_names(target: Path | None = None) -> list[str]:
    """Return distribution names for the current environment or a target venv/site-packages path."""
    search_paths = resolve_site_packages(target)
    distributions = (
        meta.distributions(path=[str(path) for path in search_paths]) if search_paths else meta.distributions()
    )
    names = {dist.metadata["Name"] for dist in distributions if dist.metadata.get("Name")}
    return sorted(names)


def collect_skip_trace_exports(
    package_names: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Analyze packages with skip_trace and return exchange payloads plus per-package failures."""
    try:
        from skip_trace.exceptions import CollectorError, NetworkError, NoEvidenceError
        from skip_trace.main import analyze_package
        from skip_trace.pypi_profile_export import build_exchange
    except ImportError as exc:
        raise RuntimeError(
            "skip_trace is required for this command. Install pypi-profile with skip-trace available."
        ) from exc

    exports: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for package_name in package_names:
        try:
            result = analyze_package(package_name)
            exports.append(build_exchange(result).model_dump(mode="json"))
        except (CollectorError, NetworkError, NoEvidenceError, OSError, ValueError) as exc:
            failures.append({"package": package_name, "error": str(exc)})
    return exports, failures


def group_exports_by_username(
    exports: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group skip_trace export payloads by discovered PyPI username."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for export in exports:
        subject = export.get("subject", {})
        for username in subject.get("pypi_usernames", []):
            if username:
                grouped.setdefault(str(username), []).append(export)
    return grouped
