"""Tests for the verifier module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pypi_profile.models import (
    IdentitySection,
    ProfileData,
    ProfileLink,
    VerificationSection,
)
from pypi_profile.verifier import fetch_page, verify_all_profiles, verify_profile_link


def test_fetch_page_success(mocker: Any) -> None:
    mock_opener = MagicMock()
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"page content"
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    mock_opener.open.return_value = mock_resp
    mocker.patch("urllib.request.build_opener", return_value=mock_opener)

    content = fetch_page("https://example.com")
    assert content == "page content"


def test_fetch_page_url_error(mocker: Any) -> None:
    import urllib.error

    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.URLError("connection refused")
    mocker.patch("urllib.request.build_opener", return_value=mock_opener)

    with pytest.raises(OSError, match="connection refused"):
        fetch_page("https://example.com")


def test_fetch_page_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        fetch_page("ftp://example.com/file")


def test_verify_claim_signature_no_sig() -> None:
    from pypi_profile.verifier import verify_claim_signature

    assert not verify_claim_signature({}, "pubkey")


def test_verify_claim_signature_invalid_pubkey(mocker: Any) -> None:
    from pypi_profile.verifier import verify_claim_signature

    mocker.patch("pypi_profile.verifier.import_minisign")
    assert not verify_claim_signature({"signature": "sig"}, "invalid-pubkey")


def test_verify_profile_link_invalid_signature(mocker: Any) -> None:
    mocker.patch(
        "pypi_profile.verifier.fetch_page",
        return_value="pypi-profile-proof: valid_token",
    )
    mocker.patch(
        "pypi_profile.verifier.decode_claim",
        return_value={
            "subject": "https://example.com",
            "pypi_username": "alice",
            "profile_package": "pkg",
            "signature": "sig",
        },
    )
    mocker.patch("pypi_profile.verifier.verify_claim_signature", return_value=False)
    mocker.patch("pypi_profile.verifier.is_expired", return_value=False)

    link = ProfileLink(kind="github", label="GitHub", url="https://example.com")
    status = verify_profile_link(link, "pubkey", "pkg", "alice")
    assert status == "invalid"


def test_verify_profile_link_success(mocker: Any) -> None:
    import base64

    # 74-byte fake sig and 42-byte fake pk so format pre-checks pass
    fake_sig = base64.standard_b64encode(b"ED" + b"\x00" * 72).decode()
    fake_pk = base64.standard_b64encode(b"RW" + b"\x00" * 40).decode()

    mocker.patch(
        "pypi_profile.verifier.fetch_page",
        return_value="pypi-profile-proof: valid_token",
    )
    mocker.patch(
        "pypi_profile.verifier.decode_claim",
        return_value={
            "subject": "https://example.com",
            "pypi_username": "alice",
            "profile_package": "pkg",
            "signature": fake_sig,
        },
    )
    mocker.patch("pypi_profile.verifier.verify_claim_signature", return_value=True)
    mocker.patch("pypi_profile.verifier.is_expired", return_value=False)

    link = ProfileLink(kind="github", label="GitHub", url="https://example.com")
    status = verify_profile_link(link, fake_pk, "pkg", "alice")
    assert status == "verified"


def test_verify_profile_link_no_tokens(mocker: Any) -> None:
    mocker.patch("pypi_profile.verifier.fetch_page", return_value="no tokens here")
    link = ProfileLink(kind="github", label="GitHub", url="https://example.com")
    status = verify_profile_link(link, "pubkey", "pkg", "alice")
    assert status == "unverified"


def test_verify_profile_link_expired(mocker: Any) -> None:
    mocker.patch("pypi_profile.verifier.fetch_page", return_value="pypi-profile-proof: token")
    mocker.patch(
        "pypi_profile.verifier.decode_claim",
        return_value={
            "subject": "https://example.com",
            "pypi_username": "alice",
            "profile_package": "pkg",
        },
    )
    mocker.patch("pypi_profile.verifier.is_expired", return_value=True)

    link = ProfileLink(kind="github", label="GitHub", url="https://example.com")
    status = verify_profile_link(link, "pubkey", "pkg", "alice")
    assert status == "expired"


def test_verify_all_profiles(mocker: Any) -> None:
    profile = ProfileData(
        identity=IdentitySection(pypi_username="alice"),
        verification=VerificationSection(public_key="pubkey"),
        profiles=[
            ProfileLink(kind="github", label="GH", url="https://gh.com"),
            ProfileLink(kind="gitlab", label="GL", url="https://gl.com"),
        ],
    )

    def mock_verify(link, **kwargs):
        if "gh.com" in link.url:
            return "verified"
        return "unverified"

    mocker.patch("pypi_profile.verifier.verify_profile_link", side_effect=mock_verify)

    results = verify_all_profiles(profile, "pkg")
    assert len(results) == 2
    assert results[0]["status"] == "verified"
    assert results[1]["status"] == "unverified"
