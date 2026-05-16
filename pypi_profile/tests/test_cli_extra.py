"""Extra tests for cli.py to fill coverage gaps."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from pypi_profile.cli import main


def test_cli_help(capsys):
    with patch.object(sys, "argv", ["pypi-profile", "--help"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
    out, _ = capsys.readouterr()
    assert "usage: pypi-profile" in out


def test_cli_key_info(capsys, mocker):
    mocker.patch(
        "pypi_profile.key_management.key_info",
        return_value={
            "not_found": False,
            "source": "mock-source",
            "key_id": "MOCK-KID",
            "generated": "2023-01-01",
            "public_key": "MOCK-PK",
            "profile_binding": "matches",
        },
    )

    with patch.object(sys, "argv", ["pypi-profile", "key-info"]):
        main()

    out, _ = capsys.readouterr()
    assert "MOCK-KID" in out
    assert "mock-source" in out


def test_cli_key_list(capsys, mocker):
    mocker.patch(
        "pypi_profile.key_management.key_list",
        return_value=[
            {"identity_or_path": "label", "key_id": "KID", "source": "src", "public_key": "pub", "binding": "bind"}
        ],
    )

    with patch.object(sys, "argv", ["pypi-profile", "key-list"]):
        main()

    out, _ = capsys.readouterr()
    assert "KID" in out
    assert "src" in out


def test_cli_key_export(capsys, mocker, tmp_path):
    out_path = tmp_path / "export.key"
    mocker.patch(
        "pypi_profile.key_management.key_export",
        return_value={
            "dry_run": False,
            "written_to": str(out_path),
            "source": "src",
            "key_id": "KID",
            "warning": "warn",
        },
    )

    with patch.object(sys, "argv", ["pypi-profile", "key-export", "--output", str(out_path)]):
        main()

    out, _ = capsys.readouterr()
    assert "KID" in out
    assert str(out_path) in out
