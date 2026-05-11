"""Tests to fill miscellaneous coverage gaps."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from pypi_profile.claims import is_expired, decode_claim
from pypi_profile.ds.paths import package_root_path, template_root_path, static_root_path
from pypi_profile.loader import find_profile
from pypi_profile.signing import generate_keypair, load_secret_key


def test_claims_is_expired_invalid():
    assert not is_expired({"expires_at": "invalid-date"})


def test_claims_decode_padding_error():
    # Trigger possible issues in decode_claim if any
    with pytest.raises(Exception):
        decode_claim("!!!")


def test_ds_paths():
    assert package_root_path().exists()
    assert template_root_path().exists()
    assert static_root_path().exists()


def test_loader_find_profile_package(mocker: Any):
    mock_dist = MagicMock()
    mock_dist.locate_file.return_value = "pypi_profile.toml"
    mocker.patch("importlib.metadata.distribution", return_value=mock_dist)
    mocker.patch("pathlib.Path.exists", return_value=True)
    
    path = find_profile("some-package")
    assert str(path) == "pypi_profile.toml"


def test_loader_find_profile_not_found():
    with pytest.raises(FileNotFoundError):
        find_profile("non-existent-thing-12345")


def test_signing_generate_keypair_exists(tmp_path: Path):
    sk = tmp_path / "minisign.key"
    sk.touch()
    with pytest.raises(FileExistsError):
        generate_keypair(key_dir=tmp_path, force=False)


def test_signing_generate_keypair_with_password(tmp_path: Path):
    # This requires minisign
    pytest.importorskip("minisign")
    sk, pk, pub = generate_keypair(key_dir=tmp_path, password="secret")
    assert sk.exists()


def test_signing_load_secret_key_env(tmp_path: Path, mocker: Any):
    pytest.importorskip("minisign")
    sk = tmp_path / "my.key"
    sk.touch()
    # Mock SecretKey.from_file to avoid actual loading of empty file
    mocker.patch("minisign.SecretKey.from_file")
    
    mocker.patch.dict(os.environ, {"PYPI_PROFILE_KEY_PATH": str(sk)})
    key = load_secret_key()
    assert key is not None


def test_signing_load_secret_key_not_found():
    with pytest.raises(FileNotFoundError):
        load_secret_key(Path("/non/existent/key"))
