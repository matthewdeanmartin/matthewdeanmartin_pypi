"""Tests for profile importers: JSON Resume, funding.yml, and live data helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

JOHN_DOE_RESUME = Path(__file__).parent.parent.parent / "john_doe" / "resume.json"


def test_json_resume_import_basics() -> None:
    from pypi_profile.importers import from_json_resume

    data = from_json_resume(JOHN_DOE_RESUME)

    assert data["profile"]["display_name"] == "John Doe"
    assert data["profile"]["kind"] == "individual"
    assert "python developer" in data["profile"]["summary"].lower()


def test_json_resume_import_location() -> None:
    from pypi_profile.importers import from_json_resume

    data = from_json_resume(JOHN_DOE_RESUME)
    location = data["identity"]["location"]
    assert "Chicago" in location


def test_json_resume_import_profiles() -> None:
    from pypi_profile.importers import from_json_resume

    data = from_json_resume(JOHN_DOE_RESUME)
    kinds = [p["kind"] for p in data["profiles"]]
    assert "github" in kinds
    assert "mastodon" in kinds
    assert "linkedin" in kinds


def test_json_resume_import_github_url() -> None:
    from pypi_profile.importers import from_json_resume

    data = from_json_resume(JOHN_DOE_RESUME)
    github = next(p for p in data["profiles"] if p["kind"] == "github")
    assert "john_doe" in github["url"]


def test_json_resume_import_contact_email() -> None:
    from pypi_profile.importers import from_json_resume

    data = from_json_resume(JOHN_DOE_RESUME)
    emails = [c for c in data["contact_methods"] if c["kind"] == "email"]
    assert len(emails) >= 1
    assert emails[0]["value"] == "john@example.com"


def test_json_resume_import_work_experience() -> None:
    from pypi_profile.importers import from_json_resume

    data = from_json_resume(JOHN_DOE_RESUME)
    work = data["work_experience"]
    assert len(work) == 2
    assert work[0]["organization"] == "Example Corp"
    assert work[0]["title"] == "Senior Python Engineer"
    assert work[0]["end_date"] == "present"


def test_json_resume_import_projects() -> None:
    from pypi_profile.importers import from_json_resume

    data = from_json_resume(JOHN_DOE_RESUME)
    projects = data["projects"]
    assert len(projects) == 1
    assert projects[0]["name"] == "Chicago Python Users Group"


def test_json_resume_import_all_verifications_self_asserted() -> None:
    from pypi_profile.importers import from_json_resume

    data = from_json_resume(JOHN_DOE_RESUME)
    for p in data["profiles"]:
        assert p["verification"] == "self_asserted"


def test_json_resume_from_dict() -> None:
    from pypi_profile.importers import from_json_resume_dict

    raw = {
        "basics": {
            "name": "Alice",
            "email": "alice@example.com",
            "summary": "Test user.",
            "profiles": [
                {
                    "network": "GitHub",
                    "username": "alice",
                    "url": "https://github.com/alice",
                }
            ],
        }
    }
    data = from_json_resume_dict(raw)
    assert data["profile"]["display_name"] == "Alice"
    assert data["identity"]["legal_name"] == "Alice"
    assert any(p["kind"] == "github" for p in data["profiles"])


def test_funding_yml_parsing() -> None:
    from pypi_profile.importers import parse_funding_yml

    text = """
# FUNDING.yml
github: alice
patreon: alice_patreon
open_collective: alice-oc
ko_fi: aliceko
"""
    result = parse_funding_yml(text)
    assert result["github"] == "alice"
    assert result["patreon"] == "alice_patreon"
    assert result["open_collective"] == "alice-oc"
    assert result["ko_fi"] == "aliceko"


def test_funding_yml_skips_nulls() -> None:
    from pypi_profile.importers import parse_funding_yml

    text = "github: alice\npatreon: null\ntidelift: ~\n"
    result = parse_funding_yml(text)
    assert "github" in result
    assert "patreon" not in result
    assert "tidelift" not in result


def test_load_local_funding_yml_missing(tmp_path: Path) -> None:
    from pypi_profile.importers import load_local_funding_yml

    result = load_local_funding_yml(search_dirs=[tmp_path])
    assert result == {}


def test_load_local_funding_yml_found(tmp_path: Path) -> None:
    from pypi_profile.importers import load_local_funding_yml

    funding_file = tmp_path / "FUNDING.yml"
    funding_file.write_text("github: testuser\n")
    result = load_local_funding_yml(search_dirs=[tmp_path])
    assert result["github"] == "testuser"


def test_normalize_date() -> None:
    from pypi_profile.importers import normalize_date

    assert normalize_date("2021-03-01") == "2021-03"
    assert normalize_date("2021-03") == "2021-03"
    assert normalize_date("present") == "present"
    assert normalize_date("current") == "present"
    assert normalize_date("") == ""


def test_merge_live_data_fills_empty_fields() -> None:
    from pypi_profile.importers import merge_live_data_into_profile

    profile_data: dict[str, Any] = {
        "profile": {"kind": "individual", "display_name": "", "summary": ""},
        "identity": {"location": ""},
        "contact_methods": [],
        "profiles": [],
        "packages": [],
    }
    live = {
        "github": {
            "name": "Alice",
            "bio": "Python dev",
            "location": "London, UK",
            "email": "alice@example.com",
            "blog": "https://alice.dev",
            "twitter_username": "alice_dev",
        }
    }
    result = merge_live_data_into_profile(profile_data, live)
    assert result["profile"]["display_name"] == "Alice"
    assert result["profile"]["summary"] == "Python dev"
    assert result["identity"]["location"] == "London, UK"
    assert any(c["kind"] == "email" for c in result["contact_methods"])
    assert any(c["kind"] == "website" for c in result["contact_methods"])
    assert any(p["kind"] == "twitter" for p in result["profiles"])


def test_merge_live_data_does_not_overwrite_existing() -> None:
    from pypi_profile.importers import merge_live_data_into_profile

    profile_data: dict[str, Any] = {
        "profile": {
            "kind": "individual",
            "display_name": "Existing Name",
            "summary": "Existing summary",
        },
        "identity": {"location": "Existing location"},
        "contact_methods": [],
        "profiles": [],
        "packages": [],
    }
    live = {
        "github": {
            "name": "GitHub Name",
            "bio": "GitHub bio",
            "location": "GitHub location",
        }
    }
    result = merge_live_data_into_profile(profile_data, live)
    assert result["profile"]["display_name"] == "Existing Name"
    assert result["profile"]["summary"] == "Existing summary"
    assert result["identity"]["location"] == "Existing location"


def test_init_from_json_resume_produces_valid_toml(tmp_path: Path) -> None:
    """End-to-end: init --from-json-resume should produce a parseable TOML."""
    import argparse

    from pypi_profile.cli import cmd_init

    dest = tmp_path / "pypi_profile.toml"
    args = argparse.Namespace(
        kind="individual",
        username="",
        output=str(dest),
        force=False,
        from_json_resume=str(JOHN_DOE_RESUME),
        fetch=False,
    )
    cmd_init(args)
    assert dest.exists()

    from pypi_profile.loader import load_profile

    profile = load_profile(dest)
    assert profile.profile.display_name == "John Doe"
    assert len(profile.work_experience) == 2
    assert any(p.kind == "github" for p in profile.profiles)
