"""CLI rubric tests covering help, version, exit codes, interactivity, and JSON output."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from pypi_profile.cli import build_parser, cmd_fetch, cmd_inspect, cmd_key_list, main

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "delete_failed_github_actions.py"


def _load_delete_failed_script() -> Any:
    spec = importlib.util.spec_from_file_location(
        "delete_failed_github_actions", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _subcommands() -> list[str]:
    parser = build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict):
            return sorted(choices)
    raise AssertionError("Could not find CLI subcommands.")


def test_console_entry_point_help_and_version_render() -> None:
    help_result = subprocess.run(
        ["uv", "run", "pypi-profile", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    version_result = subprocess.run(
        ["uv", "run", "pypi-profile", "--version"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert help_result.returncode == 0
    assert "usage: pypi-profile" in help_result.stdout
    assert version_result.returncode == 0
    assert "pypi-profile " in version_result.stdout


def test_all_subcommand_help_renders(capsys: pytest.CaptureFixture[str]) -> None:
    for command in _subcommands():
        with pytest.raises(SystemExit) as exc:
            main([command, "--help"])
        assert exc.value.code == 0
        out, err = capsys.readouterr()
        assert err == ""
        assert f"usage: pypi-profile {command}" in out


def test_missing_required_value_returns_usage_code_and_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["inspect", "--no-interactive"])
    out, err = capsys.readouterr()

    assert exit_code == 2
    assert out == ""
    assert "Profile source is required" in err


def test_fetch_json_output_is_machine_readable(
    capsys: pytest.CaptureFixture[str], mocker: Any, tmp_path: Path
) -> None:
    mocker.patch(
        "pypi_profile.loader.find_profile", return_value=tmp_path / "pypi_profile.toml"
    )
    mock_profile = mocker.patch("pypi_profile.loader.load_profile").return_value
    mock_profile.profile.display_name = "Alice"
    mock_profile.profiles = []
    mocker.patch(
        "pypi_profile.fetcher.fetch_all",
        return_value={"pypi_packages": [{"name": "demo"}], "github": {"name": "Alice"}},
    )
    mocker.patch(
        "pypi_profile.fetcher.compare_packages",
        return_value=[{"name": "demo", "status": "confirmed"}],
    )

    args = argparse.Namespace(
        source=str(tmp_path / "pypi_profile.toml"), json=True, dry_run=False
    )
    cmd_fetch(args)

    out, err = capsys.readouterr()
    payload = json.loads(out)
    assert err == ""
    assert payload["profile_name"] == "Alice"
    assert payload["package_comparison"][0]["status"] == "confirmed"


def test_key_list_json_output_is_machine_readable(
    capsys: pytest.CaptureFixture[str], mocker: Any
) -> None:
    mocker.patch(
        "pypi_profile.key_management.key_list",
        return_value=[
            {"identity_or_path": "alice", "key_id": "kid-1", "source": "keyring"}
        ],
    )

    args = argparse.Namespace(json=True, dry_run=False)
    cmd_key_list(args)

    out, err = capsys.readouterr()
    payload = json.loads(out)
    assert err == ""
    assert payload[0]["key_id"] == "kid-1"


def test_interactive_prompt_supplies_missing_source(
    capsys: pytest.CaptureFixture[str], mocker: Any, tmp_path: Path
) -> None:
    profile_path = tmp_path / "pypi_profile.toml"
    mocker.patch("sys.stdin.isatty", return_value=True)
    mocker.patch("sys.stdout.isatty", return_value=True)
    mocker.patch("builtins.input", return_value=str(profile_path))
    mocker.patch("pypi_profile.loader.find_profile", return_value=profile_path)

    args = argparse.Namespace(
        source="",
        no_validate=False,
        json=False,
        interactive=True,
        no_interactive=False,
        dry_run=True,
    )
    cmd_inspect(args)

    out, err = capsys.readouterr()
    assert err == ""
    assert "DRY RUN:" in out
    assert str(profile_path) in out


def test_standalone_script_help_version_and_json_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_delete_failed_script()

    with pytest.raises(SystemExit) as help_exit:
        module.parse_args(["--help"])
    with pytest.raises(SystemExit) as version_exit:
        module.parse_args(["--version"])

    help_out, help_err = capsys.readouterr()
    assert help_exit.value.code == 0
    assert version_exit.value.code == 0
    assert "usage: delete_failed_github_actions.py" in help_out
    assert help_err == ""

    module.build_gh_env = lambda _env_file: {}
    module.resolve_repo = lambda _repo: "owner/repo"
    module.iter_workflow_runs = lambda **_kwargs: []

    exit_code = module.main(["--repo", "owner/repo", "--json"])
    out, err = capsys.readouterr()
    payload = json.loads(out)

    assert exit_code == 0
    assert err == ""
    assert payload["repo"] == "owner/repo"
    assert payload["matched_runs"] == []
