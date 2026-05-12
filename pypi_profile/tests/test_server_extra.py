"""Extra tests for server.py to fill coverage gaps."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from pypi_profile.models import IdentitySection, ProfileData, ProfileLink, ProfileSection, VerificationSection
from pypi_profile.server import build_app, generate_proofs


@pytest.fixture
def minimal_profile() -> ProfileData:
    return ProfileData(
        profile=ProfileSection(display_name="Alice"),
        identity=IdentitySection(pypi_username="alice"),
        profiles=[ProfileLink(kind="github", label="GH", url="https://github.com/alice")],
        verification=VerificationSection(public_key="pubkey"),
    )


def test_generate_proofs_empty_needing_proof(minimal_profile: ProfileData) -> None:
    # All verified -> needing_proof is empty
    claim_results = [{"url": "https://github.com/alice", "status": "verified"}]
    res = generate_proofs(minimal_profile, "pkg", claim_results)
    assert res == []


def test_generate_proofs_no_key(minimal_profile: ProfileData, mocker: Any) -> None:
    # Simulate no key available: load_secret_key raises FileNotFoundError
    mocker.patch(
        "pypi_profile.signing.load_secret_key",
        side_effect=FileNotFoundError("no key"),
    )

    res = generate_proofs(minimal_profile, "pkg", [])
    assert len(res) == 1
    assert res[0]["error"] == "no-key"


def test_generate_proofs_sign_error(minimal_profile: ProfileData, mocker: Any) -> None:
    mocker.patch("pathlib.Path.exists", return_value=True)
    # The import is inside the function: from pypi_profile.signing import sign_controls_url
    mock_sign = mocker.patch("pypi_profile.signing.sign_controls_url")
    mock_sign.side_effect = ValueError("invalid key")

    res = generate_proofs(minimal_profile, "pkg", [])
    assert res[0]["error"] == "invalid key"


def test_build_app_pubkey_load_fail(minimal_profile: ProfileData, mocker: Any) -> None:
    minimal_profile.verification.public_key = ""
    mocker.patch("pathlib.Path.exists", return_value=True)
    # Need to patch minisign.PublicKey.from_file which is called inside build_app
    mock_ms = mocker.patch("minisign.PublicKey.from_file")
    mock_ms.side_effect = OSError("read fail")

    build_app(minimal_profile)
    assert minimal_profile.verification.public_key == ""


def test_verification_route_error(minimal_profile: ProfileData, mocker: Any) -> None:
    mock_verify = mocker.patch("pypi_profile.verifier.verify_all_profiles")
    mock_verify.side_effect = OSError("verify boom")

    app = build_app(minimal_profile)
    client = TestClient(app)

    response = client.get("/verification")
    assert response.status_code == 200
    assert "PyPI-published" in response.text


def test_api_verification_route_error(minimal_profile: ProfileData, mocker: Any) -> None:
    mock_verify = mocker.patch("pypi_profile.verifier.verify_all_profiles")
    mock_verify.side_effect = ValueError("verify boom")

    app = build_app(minimal_profile)
    client = TestClient(app)

    response = client.get("/api/verification.json")
    assert response.status_code == 200
    data = response.json()
    assert data["claim_results"] == []


def test_resume_page_renders(minimal_profile: ProfileData) -> None:
    app = build_app(minimal_profile)
    client = TestClient(app)
    response = client.get("/resume")
    assert response.status_code == 200
    assert "Alice" in response.text


def test_api_projects_json(minimal_profile: ProfileData) -> None:
    from pypi_profile.models import ProjectEntry

    minimal_profile.projects = [ProjectEntry(name="my-proj", url="https://x.com")]
    app = build_app(minimal_profile)
    client = TestClient(app)
    response = client.get("/api/projects.json")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["name"] == "my-proj"


def test_generate_proofs_sign_raises_os_error(minimal_profile: ProfileData, mocker: Any) -> None:
    # sign_controls_url raises OSError (e.g. key file unreadable)
    mocker.patch(
        "pypi_profile.signing.sign_controls_url",
        side_effect=OSError("disk error"),
    )

    res = generate_proofs(minimal_profile, "pkg", [])
    assert res[0]["error"] == "disk error"
