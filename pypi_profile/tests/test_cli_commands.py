"""Tests for CLI commands in cli.py."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pytest


def test_cmd_validate_success(capsys: Any, tmp_path: Path) -> None:
    from pypi_profile.cli import cmd_validate

    toml = tmp_path / "pypi_profile.toml"
    toml.write_text('[profile]\ndisplay_name = "Alice"', encoding="utf-8")

    args = argparse.Namespace(path=str(toml))
    cmd_validate(args)

    captured = capsys.readouterr()
    assert "OK:" in captured.out
    assert "Alice" in captured.out


def test_cmd_validate_invalid(capsys: Any, tmp_path: Path) -> None:
    from pypi_profile.cli import cmd_validate

    toml = tmp_path / "pypi_profile.toml"
    # Invalid: 'kind' must be one of the literals
    toml.write_text('[profile]\nkind = "not-a-kind"', encoding="utf-8")

    args = argparse.Namespace(path=str(toml))
    with pytest.raises(SystemExit) as exc:
        cmd_validate(args)
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "INVALID:" in captured.err


def test_cmd_validate_dry_run_skips_public_key_autopatch(capsys: Any, tmp_path: Path, mocker: Any) -> None:
    from pypi_profile.cli import cmd_validate

    autopatch = mocker.patch("pypi_profile.signing.patch_public_key_in_toml")
    toml = tmp_path / "pypi_profile.toml"
    toml.write_text(
        (
            "[profile]\n"
            'display_name = "Alice"\n'
            "[verification]\n"
            'public_key = ""\n'
            'preferred_signature_backend = "minisign"\n'
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(path=str(toml), dry_run=True)
    cmd_validate(args)

    autopatch.assert_not_called()
    captured = capsys.readouterr()
    assert "DRY RUN:" in captured.out


def test_cmd_init_basic(capsys: Any, tmp_path: Path, mocker: Any) -> None:
    from pypi_profile.cli import cmd_init

    # Mock stdin.isatty to False to avoid wizard
    mocker.patch("sys.stdin.isatty", return_value=False)

    dest = tmp_path / "pypi_profile.toml"
    args = argparse.Namespace(
        output=str(dest),
        username="alice",
        kind="individual",
        force=False,
        from_json_resume=None,
        fetch=False,
    )

    cmd_init(args)

    assert dest.exists()
    assert 'pypi_username = "alice"' in dest.read_text()

    captured = capsys.readouterr()
    assert "Created" in captured.out


def test_cmd_init_dry_run_does_not_write(capsys: Any, tmp_path: Path, mocker: Any) -> None:
    from pypi_profile.cli import cmd_init

    mocker.patch("sys.stdin.isatty", return_value=False)

    dest = tmp_path / "pypi_profile.toml"
    args = argparse.Namespace(
        output=str(dest),
        username="alice",
        kind="individual",
        force=False,
        from_json_resume="",
        fetch=True,
        no_interactive=True,
        dry_run=True,
    )

    cmd_init(args)

    assert not dest.exists()
    captured = capsys.readouterr()
    assert "DRY RUN:" in captured.out


def test_cmd_serve_mock(mocker: Any, tmp_path: Path) -> None:
    from pypi_profile.cli import cmd_serve

    mock_uvicorn = mocker.patch("uvicorn.run")
    mocker.patch("pypi_profile.loader.load_profile")
    mocker.patch("pypi_profile.server.build_app")

    toml = tmp_path / "pypi_profile.toml"
    toml.touch()

    args = argparse.Namespace(source=str(toml), host="127.0.0.1", port=8000, allow_code=False)

    cmd_serve(args)

    mock_uvicorn.assert_called_once()
    assert mock_uvicorn.call_args[1]["host"] == "127.0.0.1"


def test_cmd_serve_dry_run_skips_uvicorn(mocker: Any, tmp_path: Path, capsys: Any) -> None:
    from pypi_profile.cli import cmd_serve

    mock_uvicorn = mocker.patch("uvicorn.run")
    mocker.patch("pypi_profile.loader.load_profile")
    mocker.patch("pypi_profile.loader.find_profile", return_value=tmp_path / "pypi_profile.toml")

    args = argparse.Namespace(
        source=str(tmp_path / "pypi_profile.toml"), host="127.0.0.1", port=8000, allow_code=False, dry_run=True
    )

    cmd_serve(args)

    mock_uvicorn.assert_not_called()
    captured = capsys.readouterr()
    assert "DRY RUN:" in captured.out


def test_cmd_fetch_mock(mocker: Any, tmp_path: Path, capsys: Any) -> None:
    from pypi_profile.cli import cmd_fetch

    mock_fetch_all = mocker.patch("pypi_profile.fetcher.fetch_all", return_value={"pypi_packages": []})
    mocker.patch("pypi_profile.fetcher.compare_packages", return_value=[])
    mocker.patch("pypi_profile.loader.load_profile")
    mocker.patch("pypi_profile.loader.find_profile", return_value=tmp_path / "pypi_profile.toml")

    toml = tmp_path / "pypi_profile.toml"
    toml.touch()

    args = argparse.Namespace(source=str(toml), verbose=True, update=False, json=False)

    cmd_fetch(args)

    mock_fetch_all.assert_called_once()
    captured = capsys.readouterr()
    assert "Fetching live data" in captured.out


def test_cmd_doctor(capsys: Any, tmp_path: Path, mocker: Any) -> None:
    from pypi_profile.cli import cmd_doctor

    mocker.patch("importlib.import_module")
    mocker.patch("pypi_profile.loader.find_profile", return_value=tmp_path / "pypi_profile.toml")
    mocker.patch("pypi_profile.loader.load_profile")

    toml = tmp_path / "pypi_profile.toml"
    toml.write_text('[profile]\ndisplay_name = "Alice"', encoding="utf-8")

    args = argparse.Namespace(source=str(toml))
    cmd_doctor(args)

    captured = capsys.readouterr()
    assert "pypi-profile doctor" in captured.out
    assert "All required checks passed" in captured.out


def test_cmd_keygen_mock(mocker: Any, tmp_path: Path, capsys: Any) -> None:
    from pypi_profile.cli import cmd_keygen

    mock_gen = mocker.patch(
        "pypi_profile.signing.generate_keypair",
        return_value=(Path("sk"), Path("pk"), "pubkey"),
    )

    args = argparse.Namespace(key_dir=str(tmp_path), password="", force=False)

    cmd_keygen(args)

    mock_gen.assert_called_once()
    captured = capsys.readouterr()
    assert "Secret key" in captured.out


def test_cmd_keygen_dry_run_skips_generation(mocker: Any, tmp_path: Path, capsys: Any) -> None:
    from pypi_profile.cli import cmd_keygen

    mock_gen = mocker.patch("pypi_profile.signing.generate_keypair")
    args = argparse.Namespace(
        key_dir=str(tmp_path),
        password="",
        force=True,
        keyring_identity="work",
        no_keyring=True,
        dry_run=True,
    )

    cmd_keygen(args)

    mock_gen.assert_not_called()
    captured = capsys.readouterr()
    assert "DRY RUN:" in captured.out


def test_cmd_sign_mock(mocker: Any, tmp_path: Path, capsys: Any) -> None:
    from pypi_profile.cli import cmd_sign

    mocker.patch("pypi_profile.loader.find_profile", return_value=tmp_path / "pypi_profile.toml")
    mocker.patch("pypi_profile.loader.load_profile")
    mock_sign = mocker.patch(
        "pypi_profile.signing.sign_controls_url",
        return_value="pypi-profile-proof: token",
    )

    args = argparse.Namespace(
        source=str(tmp_path / "pypi_profile.toml"),
        url="https://example.com",
        key="sk",
        password="",
        profile_package=None,
        compact=False,
    )

    cmd_sign(args)

    mock_sign.assert_called_once()
    captured = capsys.readouterr()
    assert "pypi-profile-proof" in captured.out


def test_cmd_update_proofs_dry_run_skips_patch(mocker: Any, tmp_path: Path, capsys: Any) -> None:
    from pypi_profile.cli import cmd_update_proofs

    mock_patch = mocker.patch("pypi_profile.signing.patch_proofs_in_toml")
    mocker.patch("pypi_profile.loader.find_profile", return_value=tmp_path / "pypi_profile.toml")
    mock_profile = mocker.patch("pypi_profile.loader.load_profile").return_value
    mock_profile.identity.pypi_username = "alice"
    mock_profile.profiles = []

    args = argparse.Namespace(
        source=str(tmp_path / "pypi_profile.toml"),
        key="",
        password="",
        profile_package="",
        force=False,
        dry_run=True,
    )

    cmd_update_proofs(args)

    mock_patch.assert_not_called()
    captured = capsys.readouterr()
    assert "DRY RUN:" in captured.out


def test_cmd_verify_mock(mocker: Any, tmp_path: Path, capsys: Any) -> None:
    from pypi_profile.cli import cmd_verify

    mocker.patch("pypi_profile.loader.find_profile", return_value=tmp_path / "pypi_profile.toml")
    mocker.patch("pypi_profile.loader.load_profile")
    mock_verify = mocker.patch(
        "pypi_profile.verifier.verify_all_profiles",
        return_value=[{"label": "GH", "url": "url", "status": "verified"}],
    )

    args = argparse.Namespace(source=str(tmp_path / "pypi_profile.toml"), verbose=False, profile_package=None)

    cmd_verify(args)

    mock_verify.assert_called_once()
    captured = capsys.readouterr()
    assert "verified" in captured.out


def test_main_help(mocker: Any, capsys: Any) -> None:
    from pypi_profile.cli import main

    mocker.patch("sys.argv", ["pypi-profile", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "usage: pypi-profile" in captured.out


def test_main_gui_dry_run(mocker: Any, capsys: Any) -> None:
    from pypi_profile.cli import main

    launch = mocker.patch("pypi_profile.cli.launch_gui")
    mocker.patch("sys.argv", ["pypi-profile", "gui", "--dry-run"])

    main()

    launch.assert_not_called()
    captured = capsys.readouterr()
    assert "DRY RUN:" in captured.out
