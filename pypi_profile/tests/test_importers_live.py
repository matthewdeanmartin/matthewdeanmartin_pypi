"""Tests for live data importers in importers.py, including error cases and tokens."""

from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import MagicMock

import pytest

from pypi_profile.importers import (_get_json, _get_text, _normalize_date,
                                    _open_http_url, fetch_github_funding,
                                    fetch_github_profile, fetch_github_repos,
                                    fetch_gitlab_profile,
                                    fetch_mastodon_profile,
                                    fetch_pypi_package_info,
                                    fetch_pypi_packages, from_json_resume_dict,
                                    merge_live_data_into_profile)


@pytest.fixture
def mock_urlopen(mocker: Any) -> MagicMock:
    return mocker.patch("urllib.request.urlopen")


def test_open_http_url_invalid_scheme() -> None:
    from urllib.request import Request

    req = Request("ftp://example.com")
    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        _open_http_url(req)


def test_get_json(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"key": "value"}).encode()
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    data = _get_json("https://api.example.com/data")
    assert data == {"key": "value"}


def test_get_text(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"hello world"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    text = _get_text("https://example.com/file.txt")
    assert text == "hello world"


def test_fetch_pypi_packages(mocker: Any, mock_urlopen: MagicMock) -> None:
    # Mock XML-RPC
    mock_xmlrpc = mocker.patch("xmlrpc.client.ServerProxy")
    mock_client = mock_xmlrpc.return_value
    mock_client.user_packages.return_value = [["Owner", "pkg1"]]

    # Mock JSON metadata fetch for pkg1
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {
            "info": {
                "summary": "A cool package",
                "project_url": "https://pypi.org/p/pkg1",
            }
        }
    ).encode()
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    pkgs = fetch_pypi_packages("alice")
    assert len(pkgs) == 1
    assert pkgs[0]["name"] == "pkg1"
    assert pkgs[0]["role"] == "owner"


def test_fetch_pypi_packages_xmlrpc_error(mocker: Any) -> None:
    import xmlrpc.client

    mock_xmlrpc = mocker.patch("xmlrpc.client.ServerProxy")
    mock_xmlrpc.return_value.user_packages.side_effect = xmlrpc.client.Error()

    assert fetch_pypi_packages("alice") == []


def test_fetch_pypi_packages_json_error(mocker: Any, mock_urlopen: MagicMock) -> None:
    mock_xmlrpc = mocker.patch("xmlrpc.client.ServerProxy")
    mock_xmlrpc.return_value.user_packages.return_value = [["Owner", "pkg1"]]

    mock_urlopen.side_effect = urllib.error.URLError("fail")

    pkgs = fetch_pypi_packages("alice")
    assert len(pkgs) == 1
    assert pkgs[0]["summary"] == ""


def test_fetch_pypi_package_info_error(mock_urlopen: MagicMock) -> None:
    # Must use an exception that is caught in the try-except block
    mock_urlopen.side_effect = urllib.error.URLError("boom")
    assert fetch_pypi_package_info("pkg1") == {}


def test_fetch_github_profile_error(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
    assert fetch_github_profile("alice") == {}


def test_fetch_github_repos_error(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = TimeoutError()
    assert fetch_github_repos("alice") == []


def test_fetch_gitlab_profile_error(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = ValueError()
    assert fetch_gitlab_profile("alice") == {}


def test_fetch_mastodon_profile_error(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"invalid json"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    assert fetch_mastodon_profile("https://masto.com/@alice") == {}


def test_map_json_resume_more_networks() -> None:
    raw = {
        "basics": {
            "name": "Alice",
            "phone": "123-456",
            "profiles": [
                {"network": "LinkedIn", "url": "https://linkedin.com/in/alice"},
                {"network": "Twitter", "url": "https://twitter.com/alice"},
                {"network": "GitLab", "url": "https://gitlab.com/alice"},
                {"network": "Other", "url": "https://other.com/alice"},
                {"network": "PyPI", "url": "https://pypi.org/user/alice_p/"},
            ],
        }
    }
    data = from_json_resume_dict(raw)
    kinds = [p["kind"] for p in data["profiles"]]
    assert "linkedin" in kinds
    assert "twitter" in kinds
    assert "gitlab" in kinds
    assert "website" in kinds
    assert data["identity"]["pypi_username"] == "alice_p"
    assert any(c["kind"] == "phone" for c in data["contact_methods"])


def test_normalize_date_aliases() -> None:
    assert _normalize_date("current") == "present"
    assert _normalize_date("now") == "present"
    assert _normalize_date("2021-03-01T12:00:00") == "2021-03"


def test_fetch_github_funding_with_repo(mocker: Any) -> None:
    mock_get_text = mocker.patch("pypi_profile.importers._get_text")
    # First call fails, triggers 'continue'
    mock_get_text.side_effect = [urllib.error.URLError("fail"), "github: alice"]

    res = fetch_github_funding("alice", repo="myrepo")
    assert res["github"] == "alice"
    assert mock_get_text.call_count == 2


def test_fetch_github_funding_all_fail(mocker: Any) -> None:
    mock_get_text = mocker.patch("pypi_profile.importers._get_text")
    mock_get_text.side_effect = urllib.error.URLError("fail")
    assert fetch_github_funding("alice") == {}


def test_fetch_gitlab_profile_no_users(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"[]"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    assert fetch_gitlab_profile("alice") == {}


def test_merge_live_data_existing_blog() -> None:
    profile_data = {
        "contact_methods": [{"kind": "website", "value": "https://alice.dev"}]
    }
    live = {"github": {"blog": "alice.dev"}}
    res = merge_live_data_into_profile(profile_data, live)
    assert len(res["contact_methods"]) == 1


def test_merge_live_data_pypi_packages() -> None:
    profile_data = {"packages": []}
    live = {"pypi_packages": [{"name": "pkg1"}]}
    res = merge_live_data_into_profile(profile_data, live)
    assert len(res["packages"]) == 1


def test_fetch_pypi_package_info(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {
            "info": {
                "summary": "desc",
                "version": "1.2.3",
                "maintainers": [{"username": "alice"}],
            }
        }
    ).encode()
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    info = fetch_pypi_package_info("pkg1")
    assert info["name"] == "pkg1"
    assert info["version"] == "1.2.3"
    assert "alice" in info["maintainers"]


def test_fetch_github_profile(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {"name": "Alice GH", "login": "alice", "bio": "Developer"}
    ).encode()
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    # With token to hit line 401
    profile = fetch_github_profile("alice", token="secret")
    assert profile["name"] == "Alice GH"
    assert profile["login"] == "alice"


def test_fetch_github_repos(mock_urlopen: MagicMock) -> None:
    # Page 1
    mock_resp1 = MagicMock()
    mock_resp1.read.return_value = json.dumps(
        [{"name": "repo1", "fork": False}]
    ).encode()
    mock_resp1.headers = {"Link": '<https://api.github.com/...>; rel="next"'}
    mock_resp1.__enter__.return_value = mock_resp1

    # Page 2
    mock_resp2 = MagicMock()
    mock_resp2.read.return_value = json.dumps(
        [{"name": "repo2", "fork": False}]
    ).encode()
    mock_resp2.headers = {}
    mock_resp2.__enter__.return_value = mock_resp2

    mock_urlopen.side_effect = [mock_resp1, mock_resp2]

    # With token to hit branch in fetch_github_repos
    repos = fetch_github_repos("alice", token="secret")
    assert len(repos) == 2
    assert repos[0]["name"] == "repo1"
    assert repos[1]["name"] == "repo2"


def test_fetch_github_funding(mocker: Any) -> None:
    mock_get_text = mocker.patch("pypi_profile.importers._get_text")
    mock_get_text.side_effect = [OSError("Failed"), "github: alice\npatreon: alicep"]

    funding = fetch_github_funding("alice")
    assert funding["github"] == "alice"
    assert funding["patreon"] == "alicep"


def test_fetch_gitlab_profile(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        [{"name": "Alice GL", "username": "alice"}]
    ).encode()
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    # With token to hit line 498
    profile = fetch_gitlab_profile("alice", token="secret")
    assert profile["name"] == "Alice GL"


def test_fetch_mastodon_profile(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {
            "username": "alice",
            "display_name": "Alice M",
            "note": "<p>Hello</p>",
            "fields": [{"name": "Web", "value": "alice.dev"}],
        }
    ).encode()
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    profile = fetch_mastodon_profile("https://fosstodon.org/@alice")
    assert profile["display_name"] == "Alice M"
    assert profile["note"] == "Hello"
    assert profile["fields"][0]["name"] == "Web"


def test_fetch_mastodon_profile_invalid_url() -> None:
    assert fetch_mastodon_profile("invalid-url") == {}
