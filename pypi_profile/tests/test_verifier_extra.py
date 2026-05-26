"""Extra tests for verifier.py to fill coverage gaps."""

from __future__ import annotations

import base64
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from pypi_profile.models import ProfileLink
from pypi_profile.verifier import (
    diagnose_mastodon_link,
    diagnose_profile_link,
    diagnose_tokens,
    extract_urls_from_field,
    fetch_page,
    verify_claim_signature,
)


def test_fetch_page_success():
    with patch("urllib.request.build_opener") as mock_opener:
        mock_r = MagicMock()
        mock_r.read.return_value = b"content"
        mock_r.__enter__.return_value = mock_r
        mock_opener.return_value.open.return_value = mock_r

        assert fetch_page("https://example.com") == "content"


def test_fetch_page_error():
    with patch("urllib.request.build_opener") as mock_opener:
        mock_opener.return_value.open.side_effect = urllib.error.URLError("reason")
        with pytest.raises(OSError, match="reason"):
            fetch_page("https://example.com")


def test_verify_claim_signature_invalid_pk():
    # Public key must be 42 bytes standard b64
    assert not verify_claim_signature({}, "too-short")
    assert not verify_claim_signature({}, "invalid-b64-!!!")


def test_verify_claim_signature_missing_fields():
    # Need 42 bytes b64 for PK
    pk = base64.b64encode(b"A" * 42).decode()
    assert not verify_claim_signature({}, pk)


def test_verify_claim_signature_invalid_compact_sig():
    pk = base64.b64encode(b"A" * 42).decode()
    claim = {"g": "too-short"}  # Compact claim uses 'g'
    assert not verify_claim_signature(claim, pk)


def test_verify_claim_signature_invalid_full_sig():
    pk = base64.b64encode(b"A" * 42).decode()
    claim = {"signature": "too-short"}  # Full claim uses 'signature'
    assert not verify_claim_signature(claim, pk)


def test_diagnose_tokens_no_tokens():
    status, steps = diagnose_tokens(
        [], subject_url="url", pypi_username="u", profile_package="p", public_key_b64=""
    )
    assert status == "unverified"
    assert "No pypi-profile-proof tokens found" in steps[0]


def test_diagnose_tokens_mismatch(mocker):
    # Mock decode_claim to return a claim that doesn't match
    mocker.patch(
        "pypi_profile.verifier.decode_claim", return_value={"subject": "other"}
    )
    status, steps = diagnose_tokens(
        ["token"],
        subject_url="url",
        pypi_username="u",
        profile_package="p",
        public_key_b64="",
    )
    assert status == "unverified"
    assert any("Subject mismatch" in s for s in steps)


def test_extract_urls_from_field():
    assert extract_urls_from_field("http://example.com") == ["http://example.com"]
    assert extract_urls_from_field('<a href="http://example.com">link</a>') == [
        "http://example.com"
    ]


def test_diagnose_profile_link_scraper_hostile():
    link = ProfileLink(
        kind="github", label="GitHub", url="https://linkedin.com/in/user"
    )
    status, steps = diagnose_profile_link(link, "", "p", "u")
    assert status == "unverified"
    assert "actively blocks automated requests" in steps[0]


def test_diagnose_mastodon_link_invalid_url():
    link = ProfileLink(
        kind="mastodon", label="M", url="https://example.com/not-mastodon"
    )
    status, steps = diagnose_mastodon_link(link, "p")
    assert status == "unverified"
    assert "does not look like a Mastodon profile URL" in steps[0]


def test_diagnose_mastodon_link_success(mocker):
    link = ProfileLink(kind="mastodon", label="M", url="https://mastodon.social/@user")

    # Mock API call
    mock_r = MagicMock()
    mock_r.read.return_value = b'{"fields": [{"name": "PyPI", "value": "https://pypi.org/project/p", "verified_at": "2023-01-01"}]}'
    mock_r.__enter__.return_value = mock_r
    mocker.patch("urllib.request.urlopen", return_value=mock_r)

    status, steps = diagnose_mastodon_link(link, profile_package="p")
    assert status == "verified"
    assert any(
        "Contains 'pypi.org/project/p' and is Mastodon-verified" in s for s in steps
    )


def test_diagnose_mastodon_link_api_fail(mocker):
    link = ProfileLink(kind="mastodon", label="M", url="https://mastodon.social/@user")
    mocker.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("fail"))

    status, steps = diagnose_mastodon_link(link, profile_package="p")
    assert status == "unverified"
    assert any("Could not reach Mastodon API" in s for s in steps)


def test_diagnose_mastodon_link_fallback_verified(mocker):
    link = ProfileLink(kind="mastodon", label="M", url="https://mastodon.social/@user")

    # Mock API call - no verified fields
    mock_api_r = MagicMock()
    mock_api_r.read.return_value = b'{"fields": []}'
    mock_api_r.__enter__.return_value = mock_api_r

    mocker.patch("urllib.request.urlopen", return_value=mock_api_r)
    mocker.patch(
        "pypi_profile.verifier.fetch_page", return_value="pypi-profile-proof: token"
    )
    mocker.patch("pypi_profile.verifier.find_proof_tokens", return_value=["token"])
    mocker.patch(
        "pypi_profile.verifier.diagnose_tokens", return_value=("verified", ["step"])
    )

    status, steps = diagnose_mastodon_link(
        link, profile_package="p", public_key_b64="pk"
    )
    assert status == "verified"
    assert "step" in steps


def test_diagnose_tokens_expired(mocker):
    mocker.patch(
        "pypi_profile.verifier.decode_claim",
        return_value={
            "subject": "url",
            "pypi_username": "u",
            "profile_package": "p",
            "expires_at": "2000-01-01T00:00:00Z",
        },
    )
    mocker.patch("pypi_profile.verifier.is_expired", return_value=True)
    status, steps = diagnose_tokens(
        ["token"],
        subject_url="url",
        pypi_username="u",
        profile_package="p",
        public_key_b64="pk",
    )
    assert status == "expired"
    assert any("Claim expired" in s for s in steps)


def test_diagnose_tokens_no_pk(mocker):
    mocker.patch(
        "pypi_profile.verifier.decode_claim",
        return_value={"subject": "url", "pypi_username": "u", "profile_package": "p"},
    )
    mocker.patch("pypi_profile.verifier.is_expired", return_value=False)
    status, steps = diagnose_tokens(
        ["token"],
        subject_url="url",
        pypi_username="u",
        profile_package="p",
        public_key_b64="",
    )
    assert status == "unverified"
    assert any("No public_key in [verification]" in s for s in steps)


def test_diagnose_tokens_invalid_sig(mocker):
    mocker.patch(
        "pypi_profile.verifier.decode_claim",
        return_value={
            "subject": "url",
            "pypi_username": "u",
            "profile_package": "p",
            "signature": base64.b64encode(b"A" * 74).decode(),
        },
    )
    mocker.patch("pypi_profile.verifier.is_expired", return_value=False)
    mocker.patch("pypi_profile.verifier.verify_claim_signature", return_value=False)
    status, steps = diagnose_tokens(
        ["token"],
        subject_url="url",
        pypi_username="u",
        profile_package="p",
        public_key_b64=base64.b64encode(b"A" * 42).decode(),
    )
    assert status == "invalid"
    assert any("Signature INVALID" in s for s in steps)
