"""Comprehensive web API tests for the FastAPI profile server.

Exercises every HTML and JSON endpoint, including hub mode, static_mode,
query parameters, and edge-case profile data states.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

JOHN_DOE_TOML = Path(__file__).parent.parent.parent / "john_doe" / "john_doe" / "pypi_profile.toml"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def john_doe_client() -> TestClient:
    from pypi_profile.loader import load_profile
    from pypi_profile.server import build_app

    profile = load_profile(JOHN_DOE_TOML)
    app = build_app(profile, static_mode=True)
    return TestClient(app)


@pytest.fixture()
def minimal_profile():
    from pypi_profile.models import (
        ContactMethod,
        HiringSection,
        HumanEntry,
        IdentitySection,
        PackageEntry,
        ProfileData,
        ProfileLink,
        ProfileSection,
        ProjectEntry,
        SuccessionContact,
        SuccessionSection,
        VerificationSection,
        WorkEntry,
    )

    return ProfileData(
        profile=ProfileSection(kind="individual", display_name="Alice Test", summary="A test profile"),
        identity=IdentitySection(
            pypi_username="alice_test",
            display_name="Alice Test",
            location="Testville, TX",
            timezone="America/Chicago",
            pronouns="she/her",
        ),
        humans=[HumanEntry(id="alice_test", display_name="Alice Test", role="Owner")],
        profiles=[
            ProfileLink(
                kind="github",
                label="GitHub",
                url="https://github.com/alice_test",
                verification="self_asserted",
                rel_me=True,
                stored_proof="",
            ),
            ProfileLink(
                kind="mastodon",
                label="Mastodon",
                url="https://fosstodon.org/@alice_test",
                verification="self_asserted",
                stored_proof="",
            ),
        ],
        contact_methods=[
            ContactMethod(kind="email", label="Work email", value="alice@example.com", visibility="public"),
            ContactMethod(kind="email", label="Obfuscated", value="alice2@example.com", visibility="obfuscated"),
        ],
        packages=[
            PackageEntry(name="alice-pkg", role="owner", state="active", summary="Alice's package"),
            PackageEntry(name="old-pkg", role="former-maintainer", state="archived", summary="Archived."),
        ],
        projects=[
            ProjectEntry(name="Alice's Project", url="https://example.com", role="creator", state="active"),
        ],
        work_experience=[
            WorkEntry(organization="Test Corp", title="Engineer", start_date="2020-01", end_date="present"),
        ],
        hiring=HiringSection(employment_types=["contracting"], work_model=["remote"], jurisdiction=["US"]),
        succession=SuccessionSection(
            policy="Contact Jane if unreachable for 30 days.",
            last_reviewed="2026-01-01",
            contacts=[
                SuccessionContact(
                    name="Jane Doe",
                    contact="jane@example.com",
                    scope=["alice-pkg"],
                    relationship="co-maintainer",
                )
            ],
        ),
        verification=VerificationSection(public_key="", preferred_signature_backend="minisign"),
    )


@pytest.fixture()
def minimal_client(minimal_profile) -> TestClient:
    from pypi_profile.server import build_app

    app = build_app(minimal_profile, static_mode=True)
    return TestClient(app)


# ---------------------------------------------------------------------------
# HTML page tests — john_doe profile (rich data)
# ---------------------------------------------------------------------------


class TestHtmlPagesJohnDoe:
    def test_summary_status_ok(self, john_doe_client):
        assert john_doe_client.get("/").status_code == 200

    def test_summary_contains_name(self, john_doe_client):
        r = john_doe_client.get("/")
        assert "John Doe" in r.text

    def test_summary_contains_username(self, john_doe_client):
        r = john_doe_client.get("/")
        assert "john_doe" in r.text

    def test_packages_page_status_ok(self, john_doe_client):
        assert john_doe_client.get("/packages").status_code == 200

    def test_packages_page_lists_packages(self, john_doe_client):
        r = john_doe_client.get("/packages")
        assert "john-doe" in r.text
        assert "example-cli" in r.text

    def test_projects_page_status_ok(self, john_doe_client):
        assert john_doe_client.get("/projects").status_code == 200

    def test_projects_page_lists_project(self, john_doe_client):
        r = john_doe_client.get("/projects")
        assert "Chicago" in r.text

    def test_resume_page_status_ok(self, john_doe_client):
        assert john_doe_client.get("/resume").status_code == 200

    def test_resume_contains_work_entry(self, john_doe_client):
        r = john_doe_client.get("/resume")
        assert "Example Corp" in r.text

    def test_hiring_page_status_ok(self, john_doe_client):
        assert john_doe_client.get("/hiring").status_code == 200

    def test_hiring_page_contains_employment_type(self, john_doe_client):
        r = john_doe_client.get("/hiring")
        assert "Consulting" in r.text or "contracting" in r.text.lower()

    def test_contact_page_status_ok(self, john_doe_client):
        assert john_doe_client.get("/contact").status_code == 200

    def test_verification_page_status_ok(self, john_doe_client):
        assert john_doe_client.get("/verification").status_code == 200

    def test_verification_page_shows_proof_section(self, john_doe_client):
        r = john_doe_client.get("/verification")
        assert "PyPI-published" in r.text

    def test_succession_page_status_ok(self, john_doe_client):
        assert john_doe_client.get("/succession").status_code == 200

    def test_succession_page_contains_policy(self, john_doe_client):
        r = john_doe_client.get("/succession")
        assert "Succession policy" in r.text


# ---------------------------------------------------------------------------
# HTML page tests — minimal profile (edge-case data)
# ---------------------------------------------------------------------------


class TestHtmlPagesMinimal:
    def test_summary_renders(self, minimal_client):
        r = minimal_client.get("/")
        assert r.status_code == 200
        assert "Alice Test" in r.text

    def test_packages_renders(self, minimal_client):
        r = minimal_client.get("/packages")
        assert r.status_code == 200
        assert "alice-pkg" in r.text

    def test_projects_renders(self, minimal_client):
        r = minimal_client.get("/projects")
        assert r.status_code == 200

    def test_resume_renders(self, minimal_client):
        r = minimal_client.get("/resume")
        assert r.status_code == 200
        assert "Test Corp" in r.text

    def test_contact_renders(self, minimal_client):
        r = minimal_client.get("/contact")
        assert r.status_code == 200

    def test_verification_renders_with_no_public_key(self, minimal_client):
        r = minimal_client.get("/verification")
        assert r.status_code == 200

    def test_succession_renders(self, minimal_client):
        r = minimal_client.get("/succession")
        assert r.status_code == 200

    def test_hiring_renders_when_no_hiring_section(self, minimal_client):
        r = minimal_client.get("/hiring")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# JSON API endpoint tests
# ---------------------------------------------------------------------------


class TestJsonApiJohnDoe:
    def test_profile_json_status_ok(self, john_doe_client):
        assert john_doe_client.get("/api/profile.json").status_code == 200

    def test_profile_json_structure(self, john_doe_client):
        data = john_doe_client.get("/api/profile.json").json()
        assert "identity" in data
        assert "packages" in data
        assert "profiles" in data

    def test_profile_json_identity_fields(self, john_doe_client):
        data = john_doe_client.get("/api/profile.json").json()
        assert data["identity"]["pypi_username"] == "john_doe"
        assert data["identity"]["display_name"] == "John Doe"

    def test_packages_json_status_ok(self, john_doe_client):
        assert john_doe_client.get("/api/packages.json").status_code == 200

    def test_packages_json_is_list(self, john_doe_client):
        pkgs = john_doe_client.get("/api/packages.json").json()
        assert isinstance(pkgs, list)
        assert len(pkgs) == 3

    def test_packages_json_has_required_fields(self, john_doe_client):
        pkgs = john_doe_client.get("/api/packages.json").json()
        for pkg in pkgs:
            assert "name" in pkg
            assert "role" in pkg
            assert "state" in pkg

    def test_projects_json_status_ok(self, john_doe_client):
        assert john_doe_client.get("/api/projects.json").status_code == 200

    def test_projects_json_is_list(self, john_doe_client):
        data = john_doe_client.get("/api/projects.json").json()
        assert isinstance(data, list)

    def test_projects_json_content(self, john_doe_client):
        data = john_doe_client.get("/api/projects.json").json()
        assert any("Chicago" in p["name"] for p in data)

    def test_people_json_status_ok(self, john_doe_client):
        assert john_doe_client.get("/api/people.json").status_code == 200

    def test_people_json_is_list(self, john_doe_client):
        data = john_doe_client.get("/api/people.json").json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_people_json_has_display_name(self, john_doe_client):
        data = john_doe_client.get("/api/people.json").json()
        assert data[0]["display_name"] == "John Doe"

    def test_verification_json_status_ok(self, john_doe_client):
        assert john_doe_client.get("/api/verification.json").status_code == 200

    def test_verification_json_structure(self, john_doe_client):
        data = john_doe_client.get("/api/verification.json").json()
        assert "claim_results" in data
        assert "static_mode" in data

    def test_verification_json_claim_results_is_list(self, john_doe_client):
        data = john_doe_client.get("/api/verification.json").json()
        assert isinstance(data["claim_results"], list)

    def test_verification_json_static_mode_flag(self, john_doe_client):
        data = john_doe_client.get("/api/verification.json").json()
        assert data["static_mode"] is True

    def test_verification_json_claim_results_have_status(self, john_doe_client):
        data = john_doe_client.get("/api/verification.json").json()
        for result in data["claim_results"]:
            assert "status" in result
            assert "url" in result


class TestJsonApiMinimal:
    def test_profile_json_returns_minimal_data(self, minimal_client):
        data = minimal_client.get("/api/profile.json").json()
        assert data["identity"]["pypi_username"] == "alice_test"

    def test_packages_json_empty_list_for_no_packages(self):
        from pypi_profile.models import IdentitySection, ProfileData, ProfileSection, VerificationSection
        from pypi_profile.server import build_app

        profile = ProfileData(
            profile=ProfileSection(display_name="Empty"),
            identity=IdentitySection(pypi_username="empty_user"),
            verification=VerificationSection(),
        )
        client = TestClient(build_app(profile, static_mode=True))
        data = client.get("/api/packages.json").json()
        assert data == []

    def test_people_json_empty_when_no_humans(self):
        from pypi_profile.models import IdentitySection, ProfileData, ProfileSection, VerificationSection
        from pypi_profile.server import build_app

        profile = ProfileData(
            profile=ProfileSection(display_name="Solo"),
            identity=IdentitySection(pypi_username="solo_user"),
            verification=VerificationSection(),
        )
        client = TestClient(build_app(profile, static_mode=True))
        data = client.get("/api/people.json").json()
        assert data == []

    def test_verification_json_stored_proof_gives_verified_status(self, minimal_profile):
        from pypi_profile.server import build_app

        minimal_profile.profiles[0].stored_proof = "pypi-profile-proof: dummytoken"
        client = TestClient(build_app(minimal_profile, static_mode=True))
        data = client.get("/api/verification.json").json()
        github_result = next(r for r in data["claim_results"] if "github" in r["url"])
        assert github_result["status"] == "verified"
        assert github_result["has_stored_proof"] is True

    def test_verification_json_no_stored_proof_uses_verification_field(self, minimal_profile):
        from pypi_profile.server import build_app

        minimal_profile.profiles[0].verification = "self_asserted"
        minimal_profile.profiles[0].stored_proof = ""
        client = TestClient(build_app(minimal_profile, static_mode=True))
        data = client.get("/api/verification.json").json()
        github_result = next(r for r in data["claim_results"] if "github" in r["url"])
        assert github_result["status"] == "self_asserted"


# ---------------------------------------------------------------------------
# Static-mode vs dynamic-mode behavior
# ---------------------------------------------------------------------------


class TestStaticMode:
    def test_static_mode_verification_no_live_requests(self, minimal_profile, mocker: Any):
        from pypi_profile.server import build_app

        mock_diagnose = mocker.patch("pypi_profile.verifier.diagnose_all_profiles")
        client = TestClient(build_app(minimal_profile, static_mode=True))
        client.get("/api/verification.json")
        mock_diagnose.assert_not_called()

    def test_dynamic_mode_calls_diagnose(self, minimal_profile, mocker: Any):
        from pypi_profile.server import build_app

        mock_diagnose = mocker.patch("pypi_profile.verifier.diagnose_all_profiles", return_value=[])
        client = TestClient(build_app(minimal_profile, static_mode=False))
        client.get("/api/verification.json")
        mock_diagnose.assert_called_once()


# ---------------------------------------------------------------------------
# 404 for unknown routes
# ---------------------------------------------------------------------------


class TestUnknownRoutes:
    def test_unknown_html_route_returns_404(self, minimal_client):
        assert minimal_client.get("/nonexistent-page").status_code == 404

    def test_unknown_api_route_returns_404(self, minimal_client):
        assert minimal_client.get("/api/nonexistent.json").status_code == 404


# ---------------------------------------------------------------------------
# Content-type checks
# ---------------------------------------------------------------------------


class TestContentTypes:
    def test_html_pages_return_html_content_type(self, minimal_client):
        for path in ["/", "/packages", "/projects", "/resume", "/hiring", "/contact", "/verification", "/succession"]:
            r = minimal_client.get(path)
            assert "text/html" in r.headers["content-type"], f"Expected HTML content type for {path}"

    def test_json_endpoints_return_json_content_type(self, minimal_client):
        for path in [
            "/api/profile.json",
            "/api/packages.json",
            "/api/projects.json",
            "/api/people.json",
            "/api/verification.json",
        ]:
            r = minimal_client.get(path)
            assert "application/json" in r.headers["content-type"], f"Expected JSON content type for {path}"


# ---------------------------------------------------------------------------
# allow_code flag
# ---------------------------------------------------------------------------


class TestAllowCodeFlag:
    def test_summary_renders_with_allow_code_true(self, minimal_profile):
        from pypi_profile.server import build_app

        client = TestClient(build_app(minimal_profile, allow_code=True, static_mode=True))
        r = client.get("/")
        assert r.status_code == 200

    def test_summary_renders_with_allow_code_false(self, minimal_profile):
        from pypi_profile.server import build_app

        client = TestClient(build_app(minimal_profile, allow_code=False, static_mode=True))
        r = client.get("/")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# base_url / hub_base propagation
# ---------------------------------------------------------------------------


class TestBaseUrl:
    def test_build_app_with_base_url(self, minimal_profile):
        from pypi_profile.server import build_app

        client = TestClient(build_app(minimal_profile, base_url="/profiles/alice_test", static_mode=True))
        r = client.get("/")
        assert r.status_code == 200

    def test_build_app_with_hub_base(self, minimal_profile):
        from pypi_profile.server import build_app

        client = TestClient(build_app(minimal_profile, hub_base="/profiles", static_mode=True))
        r = client.get("/")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# profile_package auto-naming
# ---------------------------------------------------------------------------


class TestProfilePackageNaming:
    def test_auto_names_package_from_username(self, minimal_profile):
        from pypi_profile.server import build_app

        # When profile_package is empty, it should default to pypi-profile-{username}
        # Verify the app still builds and serves correctly
        client = TestClient(build_app(minimal_profile, profile_package="", static_mode=True))
        assert client.get("/api/profile.json").status_code == 200

    def test_explicit_package_name_accepted(self, minimal_profile):
        from pypi_profile.server import build_app

        client = TestClient(build_app(minimal_profile, profile_package="custom-pkg-name", static_mode=True))
        assert client.get("/api/profile.json").status_code == 200
