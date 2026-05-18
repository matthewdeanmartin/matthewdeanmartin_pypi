from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pypi_profile.loader import load_profile


def _sample_skip_trace_export() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "generator": {"name": "skip-trace", "version": "0.1.1"},
        "source_package": {
            "name": "demo-package",
            "version": "1.2.3",
            "summary": "",
            "url": "https://pypi.org/project/demo-package/",
            "role": "maintainer",
            "pypi_usernames": ["alice"],
            "owner_candidates": ["Alice Example"],
        },
        "subject": {
            "kind": "individual",
            "display_name": "Alice Example",
            "legal_name": "Alice Example",
            "pypi_usernames": ["alice"],
            "summary": "Maintains Python packages including demo-package.",
            "contacts": [
                {
                    "kind": "email",
                    "label": "PyPI maintainer email",
                    "value": "alice@example.com",
                    "source": "pypi",
                    "confidence": 0.8,
                }
            ],
            "profiles": [
                {
                    "kind": "github",
                    "label": "GitHub",
                    "url": "https://github.com/alice",
                    "source": "repo",
                    "confidence": 0.7,
                }
            ],
            "organizations": [],
            "owner_candidates": ["Alice Example"],
            "packages": [
                {
                    "name": "demo-package",
                    "version": "1.2.3",
                    "summary": "",
                    "url": "https://pypi.org/project/demo-package/",
                    "role": "maintainer",
                    "pypi_usernames": ["alice"],
                    "owner_candidates": ["Alice Example"],
                }
            ],
        },
    }


def test_from_skip_trace_export_dict_maps_to_profile_data() -> None:
    from pypi_profile.importers import from_skip_trace_export_dict

    data = from_skip_trace_export_dict(_sample_skip_trace_export())

    assert data["identity"]["pypi_username"] == "alice"
    assert data["profile"]["display_name"] == "Alice Example"
    assert data["packages"][0]["name"] == "demo-package"
    assert data["profiles"][0]["kind"] == "github"


def test_init_from_skip_trace_produces_valid_toml(tmp_path: Path) -> None:
    from pypi_profile.cli import cmd_init
    from pypi_profile.serialization import json_dumps

    export_path = tmp_path / "skip-trace.json"
    export_path.write_text(json_dumps(_sample_skip_trace_export(), indent=2), encoding="utf-8")
    dest = tmp_path / "pypi_profile.toml"
    args = argparse.Namespace(
        kind="individual",
        username="",
        output=str(dest),
        force=False,
        from_json_resume="",
        from_skip_trace=str(export_path),
        fetch=False,
        no_interactive=True,
    )

    cmd_init(args)
    profile = load_profile(dest)

    assert profile.identity.pypi_username == "alice"
    assert profile.profile.display_name == "Alice Example"
    assert profile.packages[0].name == "demo-package"


def test_cmd_generate_missing_writes_grouped_profiles(tmp_path: Path, mocker: Any) -> None:
    from pypi_profile.cli import cmd_generate_missing

    mocker.patch(
        "pypi_profile.skip_trace_bridge.list_installed_package_names",
        return_value=["demo-package", "other-package"],
    )
    mocker.patch(
        "pypi_profile.skip_trace_bridge.collect_skip_trace_exports",
        return_value=(
            [
                _sample_skip_trace_export(),
                {
                    **_sample_skip_trace_export(),
                    "source_package": {
                        **_sample_skip_trace_export()["source_package"],
                        "name": "other-package",
                        "url": "https://pypi.org/project/other-package/",
                    },
                    "subject": {
                        **_sample_skip_trace_export()["subject"],
                        "packages": [
                            {
                                **_sample_skip_trace_export()["subject"]["packages"][0],
                                "name": "other-package",
                                "url": "https://pypi.org/project/other-package/",
                            }
                        ],
                    },
                },
            ],
            [],
        ),
    )

    args = argparse.Namespace(
        venv="",
        output_dir=str(tmp_path / "profiles"),
        limit=0,
        force=False,
        json=False,
        dry_run=False,
    )
    cmd_generate_missing(args)

    generated = load_profile(tmp_path / "profiles" / "alice" / "pypi_profile.toml")
    package_names = {pkg.name for pkg in generated.packages}
    assert package_names == {"demo-package", "other-package"}
