"""Tests for the static site builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

JOHN_DOE_TOML = Path(__file__).parent.parent.parent / "john_doe" / "john_doe" / "pypi_profile.toml"
JOHN_DOE_RESUME = Path(__file__).parent.parent.parent / "john_doe" / "resume.json"
MDM_TOML = Path(__file__).parent.parent.parent / "matthewdeanmartin" / "matthewdeanmartin" / "pypi_profile.toml"
MDM_RESUME = Path(__file__).parent.parent.parent / "matthewdeanmartin" / "resume.json"


@pytest.fixture()
def built_site(tmp_path: Path) -> Path:
    from pypi_profile.builder import build_static_site

    build_static_site(str(JOHN_DOE_TOML), output=tmp_path, verbose=False)
    return tmp_path


def test_build_creates_index(built_site: Path) -> None:
    assert (built_site / "index.html").exists()


def test_build_creates_all_pages(built_site: Path) -> None:
    expected = [
        "index.html",
        "packages/index.html",
        "projects/index.html",
        "resume/index.html",
        "hiring/index.html",
        "contact/index.html",
        "verification/index.html",
        "succession/index.html",
    ]
    for page in expected:
        assert (built_site / page).exists(), f"Missing: {page}"


def test_build_creates_json_files(built_site: Path) -> None:
    for name in (
        "profile.json",
        "packages.json",
        "projects.json",
        "people.json",
        "verification.json",
    ):
        dest = built_site / "api" / name
        assert dest.exists(), f"Missing: api/{name}"
        data = json.loads(dest.read_text())
        assert data is not None


def test_build_copies_static_assets(built_site: Path) -> None:
    assert (built_site / "static" / "pypi_ds").is_dir()
    css = list((built_site / "static" / "pypi_ds").rglob("*.css"))
    assert css, "No CSS files in static/pypi_ds/"


def test_build_html_contains_profile_name(built_site: Path) -> None:
    index = (built_site / "index.html").read_text()
    assert "John Doe" in index


def test_build_profile_json_valid(built_site: Path) -> None:
    data = json.loads((built_site / "api" / "profile.json").read_text())
    assert "profile" in data
    assert "identity" in data


@pytest.mark.skipif(not JOHN_DOE_RESUME.exists(), reason="john_doe/resume.json not present")
def test_build_resume_json_copied(tmp_path: Path) -> None:
    from pypi_profile.builder import build_static_site

    build_static_site(str(JOHN_DOE_TOML), output=tmp_path, resume_file=JOHN_DOE_RESUME, verbose=False)
    dest = tmp_path / "api" / "resume.json"
    assert dest.exists()
    data = json.loads(dest.read_text())
    assert "basics" in data


def test_build_resume_json_skipped_when_absent(tmp_path: Path) -> None:
    from pypi_profile.builder import build_static_site

    nonexistent = tmp_path / "nope.json"
    build_static_site(
        str(JOHN_DOE_TOML),
        output=tmp_path / "out",
        resume_file=nonexistent,
        verbose=False,
    )
    assert not (tmp_path / "out" / "api" / "resume.json").exists()


def test_build_base_url_prefix(tmp_path: Path) -> None:
    from pypi_profile.builder import build_static_site

    build_static_site(str(JOHN_DOE_TOML), output=tmp_path, base_url="/myuser", verbose=False)
    index = (tmp_path / "index.html").read_text()
    assert "/myuser/static/pypi_ds" in index
    assert "/myuser/packages" in index


def test_build_returns_summary(tmp_path: Path) -> None:
    from pypi_profile.builder import build_static_site

    result = build_static_site(str(JOHN_DOE_TOML), output=tmp_path, verbose=False)
    assert result["html_pages"] >= 8
    assert result["json_files"] >= 5
    assert result["output"] == str(tmp_path)


@pytest.mark.skipif(not MDM_TOML.exists(), reason="matthewdeanmartin profile not present")
def test_build_mdm_profile(tmp_path: Path) -> None:
    from pypi_profile.builder import build_static_site

    result = build_static_site(str(MDM_TOML), output=tmp_path, verbose=False)
    assert (tmp_path / "index.html").exists()
    assert result["html_pages"] >= 8


@pytest.mark.skipif(not MDM_RESUME.exists(), reason="matthewdeanmartin/resume.json not present")
def test_build_mdm_resume_auto_discovered(tmp_path: Path) -> None:
    from pypi_profile.builder import build_static_site

    result = build_static_site(str(MDM_TOML), output=tmp_path, verbose=False)
    assert result["resume_published"]
    assert (tmp_path / "api" / "resume.json").exists()
