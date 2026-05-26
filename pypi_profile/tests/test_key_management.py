"""Tests for key_management.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pypi_profile.key_management import (
    derive_key_id,
    derive_public_key_b64,
    key_export,
    key_import,
    key_info,
    key_list,
    key_match_status,
    key_recover,
    key_rotate,
    load_all_toml_public_keys,
)


@pytest.fixture
def mock_minisign(mocker):
    pytest.importorskip("minisign")
    return mocker.patch("minisign.SecretKey.from_bytes")


def test_derive_key_id(mock_minisign):
    mock_sk = MagicMock()
    mock_sk._keynum_sk.key_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    mock_minisign.return_value = mock_sk

    kid = derive_key_id(b"some bytes")
    assert kid == "0102030405060708"


def test_derive_public_key_b64(mock_minisign):
    mock_sk = MagicMock()
    mock_pk = MagicMock()
    mock_pk.to_base64.return_value = b"pubkeybase64"
    mock_sk.get_public_key.return_value = mock_pk
    mock_minisign.return_value = mock_sk

    pub = derive_public_key_b64(b"some bytes")
    assert pub == "pubkeybase64"


def test_load_all_toml_public_keys(tmp_path, mocker):
    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text(' [verification]\npublic_key = "mypubkey"', encoding="utf-8")

    mocker.patch("pypi_profile.finder.find_profile_files", return_value=[toml_path])

    keys = load_all_toml_public_keys(start_dir=tmp_path)
    assert len(keys) == 1
    assert keys[0] == (toml_path, "mypubkey")


def test_key_match_status():
    toml_entries = [(Path("p1.toml"), "pk1"), (Path("p2.toml"), "pk2")]

    assert key_match_status("pk1", toml_entries) == "matches (p1.toml)"
    assert key_match_status("pk3", toml_entries) == "mismatch (p1.toml)"
    assert key_match_status("pk1", []) == "no profile TOML found"

    toml_no_pk = [(Path("p3.toml"), "")]
    assert key_match_status("pk1", toml_no_pk) == "absent (no public_key in TOML)"


def test_key_info_not_found(mocker):
    mocker.patch("pypi_profile.key_management.keyring_is_usable", return_value=False)
    mocker.patch("pathlib.Path.exists", return_value=False)

    info = key_info()
    assert info["not_found"] is True


def test_key_info_disk(tmp_path, mocker, mock_minisign):
    sk_path = tmp_path / "minisign.key"
    sk_path.write_bytes(b"keybytes")

    mock_sk = MagicMock()
    mock_sk._keynum_sk.key_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    mock_pk = MagicMock()
    mock_pk.to_base64.return_value = b"pubkey"
    mock_sk.get_public_key.return_value = mock_pk
    mock_minisign.return_value = mock_sk

    mocker.patch(
        "pypi_profile.key_management.load_all_toml_public_keys", return_value=[]
    )

    info = key_info(sk_path=sk_path)
    assert info["not_found"] is False
    assert info["key_id"] == "0102030405060708"
    assert info["public_key"] == "pubkey"
    assert "disk" in info["source"]


def test_key_list(mocker, mock_minisign):
    mocker.patch("pypi_profile.key_management.keyring_is_usable", return_value=False)
    mocker.patch(
        "pypi_profile.key_management.load_all_toml_public_keys", return_value=[]
    )

    # Mocking Path.glob and exists is tricky, let's just mock the whole search part or use tmp_path
    mocker.patch("pathlib.Path.is_dir", return_value=False)

    results = key_list()
    assert len(results) == 1
    assert results[0]["source"] == "keyring unavailable"


def test_key_export_stdout_error(tmp_path, mocker):
    sk_path = tmp_path / "minisign.key"
    sk_path.touch()
    mocker.patch("pypi_profile.key_management.derive_key_id", return_value="KID")
    with pytest.raises(ValueError, match="output_path is required"):
        key_export(output_path=None, sk_path=sk_path)


def test_key_export_disk(tmp_path, mock_minisign):
    sk_path = tmp_path / "minisign.key"
    sk_path.write_bytes(b"keybytes")

    mock_sk = MagicMock()
    mock_sk._keynum_sk.key_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    mock_minisign.return_value = mock_sk

    out_path = tmp_path / "export.key"
    res = key_export(output_path=out_path, sk_path=sk_path)

    assert res["key_id"] == "0102030405060708"
    assert out_path.read_bytes() == b"keybytes"


def test_key_rotate_dry_run(tmp_path, mocker):
    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text('public_key = "old"', encoding="utf-8")

    res = key_rotate(
        toml_path=toml_path,
        profile_package="pkg",
        pypi_username="user",
        dry_run=True,
        key_dir=tmp_path / "keys",
    )
    assert res["dry_run"] is True
    assert res["new_key_id"] == "(would generate)"


def test_key_recover_dry_run(tmp_path, mocker):
    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text('public_key = "old"', encoding="utf-8")

    mocker.patch("pypi_profile.key_management.keyring_is_usable", return_value=False)

    res = key_recover(
        toml_path=toml_path,
        profile_package="pkg",
        pypi_username="user",
        dry_run=True,
        key_dir=tmp_path / "keys",
    )
    assert res["dry_run"] is True
    assert "DRY RUN" in res["message"]


def test_key_import_dry_run(tmp_path):
    import_path = tmp_path / "import.key"
    import_path.touch()

    res = key_import(import_path=import_path, dry_run=True)
    assert res["dry_run"] is True
    assert res["key_id"] == "(not read in dry-run)"


def test_key_import_exists_error(tmp_path, mock_minisign):
    import_path = tmp_path / "import.key"
    import_path.write_bytes(b"keybytes")

    # Mocking DEFAULT_KEY_DIR is better than relying on it
    mocker_dir = tmp_path / "keys"
    mocker_dir.mkdir()
    (mocker_dir / "minisign.key").touch()

    mock_sk = MagicMock()
    mock_sk._keynum_sk.key_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    mock_minisign.return_value = mock_sk

    with pytest.raises(FileExistsError):
        key_import(import_path=import_path, key_dir=mocker_dir)


def test_key_rotate_success(tmp_path, mocker):
    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text('public_key = "old"', encoding="utf-8")

    mocker.patch("pypi_profile.key_management.keyring_is_usable", return_value=False)
    mocker.patch(
        "pypi_profile.key_management.generate_keypair",
        return_value=(tmp_path / "new.key", tmp_path / "new.pub", "newpubb64"),
    )
    mocker.patch(
        "pypi_profile.key_management.patch_proofs_in_toml", return_value=["url1"]
    )

    mock_sk = MagicMock()
    mock_sk._keynum_sk.key_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    mocker.patch("minisign.SecretKey.from_file", return_value=mock_sk)

    res = key_rotate(
        toml_path=toml_path,
        profile_package="pkg",
        pypi_username="user",
        key_dir=tmp_path,
    )

    assert res["new_key_id"] == "0102030405060708"
    assert res["updated_urls"] == ["url1"]
    assert 'public_key = "newpubb64"' in toml_path.read_text()


def test_key_recover_success(tmp_path, mocker):
    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text('public_key = "old"', encoding="utf-8")

    mocker.patch("pypi_profile.key_management.keyring_is_usable", return_value=False)
    mocker.patch(
        "pypi_profile.key_management.generate_keypair",
        return_value=(tmp_path / "new.key", tmp_path / "new.pub", "newpubb64"),
    )
    mocker.patch(
        "pypi_profile.key_management.patch_proofs_in_toml", return_value=["url1"]
    )
    mocker.patch("pypi_profile.key_management.patch_public_key_in_toml")

    mock_sk = MagicMock()
    mock_sk._keynum_sk.key_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    mocker.patch("minisign.SecretKey.from_file", return_value=mock_sk)

    res = key_recover(
        toml_path=toml_path,
        profile_package="pkg",
        pypi_username="user",
        key_dir=tmp_path,
    )

    assert res["new_key_id"] == "0102030405060708"
    assert res["updated_urls"] == ["url1"]


def test_key_import_success(tmp_path, mocker, mock_minisign):
    import_path = tmp_path / "import.key"
    import_path.write_bytes(b"keybytes")

    mock_sk = MagicMock()
    mock_sk._keynum_sk.key_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    mock_minisign.return_value = mock_sk

    mocker.patch("pypi_profile.key_management.keyring_is_usable", return_value=False)

    mocker_dir = tmp_path / "keys"
    res = key_import(import_path=import_path, key_dir=mocker_dir)

    assert res["key_id"] == "0102030405060708"
    assert res["stored_on_disk"] is True
    assert (mocker_dir / "minisign.key").read_bytes() == b"keybytes"
