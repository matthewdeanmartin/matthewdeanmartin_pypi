"""Tests for the live metadata fetcher."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from pypi_profile.fetcher import (
    collect_build_identities,
    compare_packages,
    extract_github_username,
    extract_gitlab_username,
    fetch_all,
)
from pypi_profile.models import (
    IdentitySection,
    PackageEntry,
    ProfileData,
    ProfileLink,
    ProfileSection,
)


@pytest.fixture
def mock_cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cache_dir = tmp_path / ".pypi_profile_cache"
    monkeypatch.setattr("pypi_profile.fetcher.CACHE_DIR", cache_dir)
    return cache_dir


@pytest.fixture
def sample_profile() -> ProfileData:
    return ProfileData(
        profile=ProfileSection(display_name="Alice"),
        identity=IdentitySection(pypi_username="alice_pypi"),
        profiles=[
            ProfileLink(kind="github", label="GitHub", url="https://github.com/alice"),
            ProfileLink(kind="gitlab", label="GitLab", url="https://gitlab.com/alice_gl"),
            ProfileLink(
                kind="mastodon",
                label="Mastodon",
                url="https://fosstodon.org/@alice_masto",
            ),
        ],
        packages=[PackageEntry(name="my-cool-pkg", role="owner")],
    )


def test_fetch_all_calls_importers(mocker: Any, mock_cache_dir: Path, sample_profile: ProfileData) -> None:
    # Mock all importer functions
    mock_pypi_user = mocker.patch(
        "pypi_profile.fetcher.fetch_pypi_user_packages",
        return_value=[{"name": "pkg1"}],
    )
    mock_pypi_pkg = mocker.patch("pypi_profile.fetcher.fetch_pypi_package_info", return_value={"summary": "desc"})
    mock_gh_profile = mocker.patch("pypi_profile.fetcher.fetch_github_profile", return_value={"name": "Alice GH"})
    mocker.patch("pypi_profile.fetcher.fetch_github_repos", return_value=[{"name": "repo1"}])
    mocker.patch("pypi_profile.fetcher.fetch_github_funding", return_value={"github": "alice"})
    mock_gl_profile = mocker.patch("pypi_profile.fetcher.fetch_gitlab_profile", return_value={"name": "Alice GL"})
    mocker.patch(
        "pypi_profile.fetcher.fetch_mastodon_profile",
        return_value={"display_name": "Alice M"},
    )
    mocker.patch("pypi_profile.fetcher.fetch_pypi_provenance", return_value=[])

    results = fetch_all(sample_profile, verbose=True)

    assert results["pypi_packages"] == [{"name": "pkg1"}]
    assert results["package_meta"]["my-cool-pkg"] == {"summary": "desc"}
    assert results["github"] == {"name": "Alice GH"}
    assert results["github_repos"] == [{"name": "repo1"}]
    assert results["github_funding"] == {"github": "alice"}
    assert results["gitlab"] == {"name": "Alice GL"}
    assert results["mastodon"] == {"display_name": "Alice M"}

    # Verify calls
    mock_pypi_user.assert_called_once_with("alice_pypi")
    mock_pypi_pkg.assert_called_once_with("my-cool-pkg")
    mock_gh_profile.assert_called_once_with("alice")
    mock_gl_profile.assert_called_once_with("alice_gl")


def test_fetch_all_uses_cache(mocker: Any, mock_cache_dir: Path, sample_profile: ProfileData) -> None:
    # Pre-populate cache
    mock_cache_dir.mkdir(parents=True, exist_ok=True)

    # GitHub profile
    cache_file = mock_cache_dir / "github_profile_alice.json"
    cache_data = {"ts": time.time(), "payload": {"name": "Cached Alice"}}
    cache_file.write_text(json.dumps(cache_data))

    # PyPI packages
    cache_file_pypi = mock_cache_dir / "pypi_packages_alice_pypi.json"
    cache_data_pypi = {"ts": time.time(), "payload": [{"name": "cached-pkg"}]}
    cache_file_pypi.write_text(json.dumps(cache_data_pypi))

    # GitHub funding
    cache_file_funding = mock_cache_dir / "github_funding_alice.json"
    cache_data_funding = {"ts": time.time(), "payload": {"github": "alice"}}
    cache_file_funding.write_text(json.dumps(cache_data_funding))

    # GitLab profile
    cache_file_gl = mock_cache_dir / "gitlab_profile_alice_gl.json"
    cache_data_gl = {"ts": time.time(), "payload": {"name": "Cached GL"}}
    cache_file_gl.write_text(json.dumps(cache_data_gl))

    # Mastodon profile
    cache_file_masto = mock_cache_dir / "mastodon_https___fosstodon.org__at_alice_masto.json"
    cache_data_masto = {"ts": time.time(), "payload": {"display_name": "Cached M"}}
    cache_file_masto.write_text(json.dumps(cache_data_masto))

    # Mock importer functions - they should NOT be called
    mock_gh_profile = mocker.patch("pypi_profile.fetcher.fetch_github_profile")
    mocker.patch("pypi_profile.fetcher.fetch_pypi_user_packages")
    mocker.patch("pypi_profile.fetcher.fetch_pypi_package_info", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_github_repos", return_value=[])
    mocker.patch("pypi_profile.fetcher.fetch_github_funding")
    mocker.patch("pypi_profile.fetcher.fetch_gitlab_profile")
    mocker.patch("pypi_profile.fetcher.fetch_mastodon_profile")
    mocker.patch("pypi_profile.fetcher.fetch_pypi_provenance", return_value=[])

    results = fetch_all(sample_profile, verbose=True)

    assert results["github"] == {"name": "Cached Alice"}
    assert results["pypi_packages"] == [{"name": "cached-pkg"}]
    assert results["github_funding"] == {"github": "alice"}
    assert results["gitlab"] == {"name": "Cached GL"}
    assert results["mastodon"] == {"display_name": "Cached M"}
    mock_gh_profile.assert_not_called()


def test_fetch_all_cache_expiry(mocker: Any, mock_cache_dir: Path, sample_profile: ProfileData) -> None:
    # Pre-populate cache with expired data
    cache_file = mock_cache_dir / "github_profile_alice.json"
    mock_cache_dir.mkdir(parents=True, exist_ok=True)
    cache_data = {"ts": time.time() - 4000, "payload": {"name": "Old Alice"}}
    cache_file.write_text(json.dumps(cache_data))

    # Mock importer functions - GH profile SHOULD be called
    mock_gh_profile = mocker.patch("pypi_profile.fetcher.fetch_github_profile", return_value={"name": "New Alice"})
    mocker.patch("pypi_profile.fetcher.fetch_pypi_user_packages", return_value=[])
    mocker.patch("pypi_profile.fetcher.fetch_pypi_package_info", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_github_repos", return_value=[])
    mocker.patch("pypi_profile.fetcher.fetch_github_funding", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_gitlab_profile", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_mastodon_profile", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_pypi_provenance", return_value=[])

    results = fetch_all(sample_profile)

    assert results["github"] == {"name": "New Alice"}
    mock_gh_profile.assert_called_once_with("alice")


def test_compare_packages() -> None:
    profile = ProfileData(
        identity=IdentitySection(pypi_username="alice"),
        packages=[
            PackageEntry(name="pkg-ok", role="owner"),
            PackageEntry(name="pkg-wrong", role="maintainer"),
            PackageEntry(name="pkg-missing", role="owner"),
        ],
    )

    live_results = {
        # pypi_packages is the authoritative ownership list from XML-RPC user_packages()
        "pypi_packages": [
            {"name": "pkg-ok", "role": "owner"},
            # pkg-wrong and pkg-missing are absent — not owned by alice on PyPI
        ],
        "package_meta": {
            "pkg-ok": {
                "summary": "OK",
                "version": "1.0",
            },
            "pkg-wrong": {
                "summary": "Wrong",
                "version": "2.0",
            },
            # pkg-missing has no metadata
        },
    }

    report = compare_packages(profile, live_results)

    assert len(report) == 3

    ok = next(r for r in report if r["name"] == "pkg-ok")
    assert ok["status"] == "confirmed"
    assert ok["pypi_version"] == "1.0"

    wrong = next(r for r in report if r["name"] == "pkg-wrong")
    assert wrong["status"] == "not_found"
    assert "alice" in wrong["note"]

    missing = next(r for r in report if r["name"] == "pkg-missing")
    assert missing["status"] == "no_data"


def test_compare_packages_no_username() -> None:
    profile = ProfileData(
        identity=IdentitySection(pypi_username=""),
        packages=[
            PackageEntry(name="pkg-any", role="owner"),
        ],
    )
    live_results = {
        "package_meta": {
            "pkg-any": {"maintainers": ["bob"], "summary": "OK", "version": "1.0"},
        }
    }
    report = compare_packages(profile, live_results)
    assert report[0]["status"] == "unverified"


def test_extract_usernames() -> None:
    assert extract_github_username("https://github.com/alice") == "alice"
    assert extract_github_username("https://github.com/alice/") == "alice"
    assert extract_github_username("http://github.com/bob") == "bob"
    assert extract_github_username("https://notgithub.com/alice") == ""

    assert extract_gitlab_username("https://gitlab.com/alice") == "alice"
    assert extract_gitlab_username("https://gitlab.com/alice/") == "alice"
    assert extract_gitlab_username("https://notgitlab.com/alice") == ""


def test_collect_build_identities_dedupes_across_packages() -> None:
    provenance_by_package = {
        "pkg-a": [
            {
                "filename": "pkg_a-1.0-py3-none-any.whl",
                "publishers": [
                    {
                        "kind": "GitHub",
                        "repository": "alice/pkg-a",
                        "workflow": "release.yml",
                        "environment": "",
                        "identity_url": "https://github.com/alice/pkg-a",
                        "claims": {},
                    }
                ],
            },
            {
                "filename": "pkg_a-1.0.tar.gz",
                "publishers": [
                    {
                        "kind": "GitHub",
                        "repository": "alice/pkg-a",
                        "workflow": "release.yml",
                        "environment": "",
                        "identity_url": "https://github.com/alice/pkg-a",
                        "claims": {},
                    }
                ],
            },
        ],
        "pkg-b": [
            {
                "filename": "pkg_b-2.0-py3-none-any.whl",
                "publishers": [
                    {
                        "kind": "GitLab",
                        "repository": "alice/pkg-b",
                        "workflow": ".gitlab-ci.yml",
                        "environment": "",
                        "identity_url": "https://gitlab.com/alice/pkg-b",
                        "claims": {},
                    }
                ],
            }
        ],
    }

    identities = collect_build_identities(provenance_by_package)

    # Two distinct identities (GitHub repo + GitLab repo), GitHub one covers 2 files.
    assert len(identities) == 2
    github = next(i for i in identities if i["kind"] == "GitHub")
    assert github["repository"] == "alice/pkg-a"
    assert github["file_count"] == 2
    assert github["packages"] == ["pkg-a"]
    assert github["identity_url"] == "https://github.com/alice/pkg-a"

    gitlab = next(i for i in identities if i["kind"] == "GitLab")
    assert gitlab["file_count"] == 1
    assert gitlab["packages"] == ["pkg-b"]


def test_collect_build_identities_groups_same_repo_across_packages() -> None:
    # Two packages published from the same monorepo workflow → one identity, file_count 2.
    provenance_by_package = {
        "lib-x": [
            {
                "filename": "lib_x-0.1.tar.gz",
                "publishers": [
                    {
                        "kind": "GitHub",
                        "repository": "alice/monorepo",
                        "workflow": "publish.yml",
                        "environment": "pypi",
                        "identity_url": "https://github.com/alice/monorepo",
                        "claims": {},
                    }
                ],
            }
        ],
        "lib-y": [
            {
                "filename": "lib_y-0.1.tar.gz",
                "publishers": [
                    {
                        "kind": "GitHub",
                        "repository": "alice/monorepo",
                        "workflow": "publish.yml",
                        "environment": "pypi",
                        "identity_url": "https://github.com/alice/monorepo",
                        "claims": {},
                    }
                ],
            }
        ],
    }

    identities = collect_build_identities(provenance_by_package)
    assert len(identities) == 1
    assert identities[0]["file_count"] == 2
    assert sorted(identities[0]["packages"]) == ["lib-x", "lib-y"]
    assert identities[0]["environment"] == "pypi"


def test_fetch_all_include_owned_extends_provenance_set(
    mocker: Any, mock_cache_dir: Path, sample_profile: ProfileData
) -> None:
    mocker.patch(
        "pypi_profile.fetcher.fetch_pypi_user_packages",
        return_value=[{"name": "my-cool-pkg"}, {"name": "other-owned-pkg"}],
    )
    mocker.patch("pypi_profile.fetcher.fetch_pypi_package_info", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_github_profile", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_github_repos", return_value=[])
    mocker.patch("pypi_profile.fetcher.fetch_github_funding", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_gitlab_profile", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_mastodon_profile", return_value={})
    prov_mock = mocker.patch("pypi_profile.fetcher.fetch_pypi_provenance", return_value=[])

    fetch_all(sample_profile, include_owned=True)

    called_names = sorted(c.args[0] for c in prov_mock.call_args_list)
    assert called_names == ["my-cool-pkg", "other-owned-pkg"]


def test_fetch_all_default_only_declared_packages(
    mocker: Any, mock_cache_dir: Path, sample_profile: ProfileData
) -> None:
    mocker.patch(
        "pypi_profile.fetcher.fetch_pypi_user_packages",
        return_value=[{"name": "my-cool-pkg"}, {"name": "other-owned-pkg"}],
    )
    mocker.patch("pypi_profile.fetcher.fetch_pypi_package_info", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_github_profile", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_github_repos", return_value=[])
    mocker.patch("pypi_profile.fetcher.fetch_github_funding", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_gitlab_profile", return_value={})
    mocker.patch("pypi_profile.fetcher.fetch_mastodon_profile", return_value={})
    prov_mock = mocker.patch("pypi_profile.fetcher.fetch_pypi_provenance", return_value=[])

    fetch_all(sample_profile)

    called_names = [c.args[0] for c in prov_mock.call_args_list]
    assert called_names == ["my-cool-pkg"]
