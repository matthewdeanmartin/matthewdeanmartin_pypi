"""Importers for external profile formats: JSON Resume, funding.yml, GitHub, GitLab, Mastodon, PyPI."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, cast

from schema_resume import validate_resume  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def open_http_url(request: urllib.request.Request) -> Any:
    """Open an HTTP(S) request after rejecting other URL schemes."""
    scheme = urllib.parse.urlsplit(request.full_url).scheme
    if scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {scheme}")
    return urllib.request.urlopen(request, timeout=10)  # nosec B310


def get_json(url: str, accept: str = "application/json") -> Any:
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "pypi-profile/0.1"})
    with open_http_url(req) as resp:
        return json.loads(cast(bytes, resp.read()).decode())


def get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "pypi-profile/0.1"})
    with open_http_url(req) as resp:
        return cast(bytes, resp.read()).decode()


# ---------------------------------------------------------------------------
# JSON Resume  (https://jsonresume.org/schema/)
# ---------------------------------------------------------------------------


def validate_json_resume(raw: dict[str, Any]) -> None:
    """Warn if raw dict does not conform to the JSON Resume schema."""
    result = validate_resume(raw)
    if not result["valid"]:
        import warnings

        messages = "; ".join(e.get("message", str(e)) for e in result["errors"][:5])
        warnings.warn(
            f"JSON Resume validation failed ({len(result['errors'])} error(s)): {messages}",
            stacklevel=3,
        )


def from_json_resume(path: Path) -> dict[str, Any]:
    """Convert a JSON Resume file into a pypi_profile data dict."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    validate_json_resume(raw)
    return map_json_resume(raw)


def from_json_resume_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert a JSON Resume dict into a pypi_profile data dict."""
    validate_json_resume(raw)
    return map_json_resume(raw)


def map_json_resume(r: dict[str, Any]) -> dict[str, Any]:
    basics = r.get("basics", {})
    name = basics.get("name", "")
    email = basics.get("email", "")
    summary = basics.get("summary", "")
    location_obj = basics.get("location", {})
    location = ", ".join(
        v
        for v in [
            location_obj.get("city", ""),
            location_obj.get("region", ""),
            location_obj.get("countryCode", ""),
        ]
        if v
    )
    profiles_raw = basics.get("profiles", [])

    profiles: list[dict[str, Any]] = []
    pypi_username = ""
    github_url = ""
    mastodon_url = ""
    gitlab_url = ""

    for p in profiles_raw:
        network = p.get("network", "").lower()
        url = p.get("url", "")
        username = p.get("username", "")
        if network == "pypi":
            pypi_username = username or url.rstrip("/").rsplit("/", 1)[-1]
        elif network == "github":
            github_url = url or f"https://github.com/{username}"
            profiles.append(
                {
                    "kind": "github",
                    "label": "GitHub",
                    "url": github_url,
                    "verification": "self_asserted",
                }
            )
        elif network == "mastodon":
            mastodon_url = url
            profiles.append(
                {
                    "kind": "mastodon",
                    "label": "Mastodon",
                    "url": mastodon_url,
                    "verification": "self_asserted",
                }
            )
        elif network == "gitlab":
            gitlab_url = url or f"https://gitlab.com/{username}"
            profiles.append(
                {
                    "kind": "gitlab",
                    "label": "GitLab",
                    "url": gitlab_url,
                    "verification": "self_asserted",
                }
            )
        elif network == "linkedin":
            profiles.append(
                {
                    "kind": "linkedin",
                    "label": "LinkedIn",
                    "url": url,
                    "verification": "self_asserted",
                }
            )
        elif network in ("twitter", "x"):
            profiles.append(
                {
                    "kind": "twitter",
                    "label": "Twitter/X",
                    "url": url,
                    "verification": "self_asserted",
                }
            )
        elif url:
            profiles.append(
                {
                    "kind": "website",
                    "label": p.get("network", "Website"),
                    "url": url,
                    "verification": "self_asserted",
                }
            )

    contact_methods: list[dict[str, Any]] = []
    if email:
        contact_methods.append(
            {
                "kind": "email",
                "label": "Professional email",
                "value": email,
                "audience": ["hiring", "consulting", "security"],
                "visibility": "public",
            }
        )
    website = basics.get("url", "")
    if website:
        contact_methods.append(
            {
                "kind": "website",
                "label": "Personal website",
                "value": website,
                "audience": ["general"],
                "visibility": "public",
            }
        )
    phone = basics.get("phone", "")
    if phone:
        contact_methods.append(
            {
                "kind": "phone",
                "label": "Phone",
                "value": phone,
                "audience": ["hiring"],
                "visibility": "public",
            }
        )

    work_raw = r.get("work", [])
    work_experience: list[dict[str, Any]] = []
    for w in work_raw:
        work_experience.append(
            {
                "organization": w.get("name", w.get("company", "")),
                "title": w.get("position", ""),
                "start_date": normalize_date(w.get("startDate", "")),
                "end_date": normalize_date(w.get("endDate", "present")) or "present",
                "summary": w.get("summary", ""),
            }
        )

    skills_raw = r.get("skills", [])
    skills = [s.get("name", "") for s in skills_raw if s.get("name")]

    projects_raw = r.get("projects", [])
    projects: list[dict[str, Any]] = []
    for p in projects_raw:
        projects.append(
            {
                "name": p.get("name", ""),
                "url": p.get("url", ""),
                "role": "creator",
                "state": "active",
                "summary": p.get("description", ""),
            }
        )

    data: dict[str, Any] = {
        "profile": {
            "kind": "individual",
            "display_name": name,
            "summary": summary,
        },
        "identity": {
            "legal_name": name,
            "display_name": name,
            "pypi_username": pypi_username,
            "timezone": "",
            "location": location,
        },
        "profiles": profiles,
        "contact_methods": contact_methods,
        "work_experience": work_experience,
        "projects": projects,
        "packages": [],
        "hiring": {
            "open_to_work_since": "",
            "employment_types": [],
            "work_model": [],
            "jurisdiction": [],
            "speaking": False,
            "sponsorship": False,
        },
    }
    if github_url:
        data["github_url"] = github_url
    if mastodon_url:
        data["mastodon_url"] = mastodon_url
    if gitlab_url:
        data["gitlab_url"] = gitlab_url
    if skills:
        data["skills"] = skills
    return data


def normalize_date(d: str) -> str:
    if not d:
        return ""
    if d.lower() in ("present", "current", "now"):
        return "present"
    # Already YYYY-MM or YYYY — keep as is
    return d[:7] if len(d) > 7 else d


# ---------------------------------------------------------------------------
# PyPI live data
# ---------------------------------------------------------------------------


def fetch_pypi_packages(username: str) -> list[dict[str, Any]]:
    """Return list of package dicts for packages where username is a maintainer/owner."""
    return fetch_pypi_user_packages(username)


def fetch_pypi_user_packages(username: str) -> list[dict[str, Any]]:
    """Fetch packages owned/maintained by a PyPI user via the PyPI XML-RPC API."""
    # PyPI exposes maintainer package data through this trusted upstream API.
    import xmlrpc.client  # nosec B411

    results: list[dict[str, Any]] = []
    logger.debug("Fetching PyPI package list for user %r", username)
    try:
        client = xmlrpc.client.ServerProxy("https://pypi.org/pypi")
        role_pkg_pairs = cast(list[list[str]], client.user_packages(username))
    except (OSError, xmlrpc.client.Error):
        logger.warning("Failed to fetch PyPI package list for %r", username, exc_info=False)
        return []

    for role, name in role_pkg_pairs:
        try:
            meta = get_json(f"https://pypi.org/pypi/{name}/json")
            info = meta.get("info", {})
            results.append(
                {
                    "name": name,
                    "role": role.lower(),
                    "state": "active",
                    "summary": (info.get("summary") or "")[:200],
                    "url": info.get("project_url") or f"https://pypi.org/project/{name}/",
                }
            )
        except (
            json.JSONDecodeError,
            OSError,
            TimeoutError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            ValueError,
        ):
            logger.warning("Failed to fetch PyPI metadata for package %r", name, exc_info=False)
            results.append(
                {
                    "name": name,
                    "role": role.lower(),
                    "state": "active",
                    "summary": "",
                    "url": f"https://pypi.org/project/{name}/",
                }
            )
    return results


def fetch_pypi_package_info(package_name: str) -> dict[str, Any]:
    """Fetch metadata for a single PyPI package."""
    logger.debug("Fetching PyPI metadata for package %r", package_name)
    try:
        data = get_json(f"https://pypi.org/pypi/{package_name}/json")
        info = data.get("info", {})
        return {
            "name": package_name,
            "summary": info.get("summary", ""),
            "version": info.get("version", ""),
            "author": info.get("author", ""),
            "author_email": info.get("author_email", ""),
            "home_page": info.get("home_page", ""),
            "project_url": info.get("project_url", ""),
            "maintainers": [m.get("username", "") for m in (info.get("maintainers") or [])]
            + ([info["author"]] if info.get("author") else []),
            "classifiers": info.get("classifiers", []),
            "requires_python": info.get("requires_python", ""),
        }
    except (
        json.JSONDecodeError,
        OSError,
        TimeoutError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        ValueError,
    ):
        logger.warning("Failed to fetch PyPI metadata for package %r", package_name, exc_info=False)
        return {}


# ---------------------------------------------------------------------------
# GitHub live data
# ---------------------------------------------------------------------------


def fetch_github_profile(username: str, token: str | None = None) -> dict[str, Any]:
    """Fetch public GitHub user profile data."""
    logger.debug("Fetching GitHub profile for %r", username)
    try:
        url = f"https://api.github.com/users/{username}"
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "pypi-profile/0.1")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with open_http_url(req) as resp:
            data = json.loads(resp.read().decode())
        return {
            "name": data.get("name", ""),
            "login": data.get("login", ""),
            "bio": data.get("bio", ""),
            "email": data.get("email", ""),
            "location": data.get("location", ""),
            "blog": data.get("blog", ""),
            "company": data.get("company", ""),
            "public_repos": data.get("public_repos", 0),
            "followers": data.get("followers", 0),
            "avatar_url": data.get("avatar_url", ""),
            "html_url": data.get("html_url", f"https://github.com/{username}"),
            "twitter_username": data.get("twitter_username", ""),
        }
    except (
        json.JSONDecodeError,
        OSError,
        TimeoutError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        ValueError,
    ):
        logger.warning("Failed to fetch GitHub profile for %r", username, exc_info=False)
        return {}


def fetch_github_repos(username: str, token: str | None = None) -> list[dict[str, Any]]:
    """Fetch all public non-fork repos for a GitHub user, paginating through all results."""
    logger.debug("Fetching GitHub repos for %r", username)
    results: list[dict[str, Any]] = []
    page = 1
    try:
        while True:
            url = f"https://api.github.com/users/{username}/repos?sort=stars&per_page=100&type=owner&page={page}"
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("User-Agent", "pypi-profile/0.1")
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with open_http_url(req) as resp:
                repos = json.loads(resp.read().decode())
                link_header = resp.headers.get("Link", "")
            for r in repos:
                if not r.get("fork", False):
                    results.append(
                        {
                            "name": r.get("name", ""),
                            "full_name": r.get("full_name", ""),
                            "description": r.get("description", ""),
                            "html_url": r.get("html_url", ""),
                            "homepage": r.get("homepage", ""),
                            "stars": r.get("stargazers_count", 0),
                            "language": r.get("language", ""),
                            "archived": r.get("archived", False),
                            "fork": False,
                        }
                    )
            if not repos or 'rel="next"' not in link_header:
                break
            page += 1
    except (
        json.JSONDecodeError,
        OSError,
        TimeoutError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        ValueError,
    ):
        logger.warning(
            "Failed to fetch GitHub repos for %r (partial results may be returned)",
            username,
            exc_info=False,
        )
    return results


def fetch_github_funding(username: str, repo: str = "", token: str | None = None) -> dict[str, Any]:
    """Fetch FUNDING.yml from a GitHub user's .github or specified repo."""
    targets = []
    if repo:
        targets.append(f"https://raw.githubusercontent.com/{username}/{repo}/main/.github/FUNDING.yml")
        targets.append(f"https://raw.githubusercontent.com/{username}/{repo}/master/.github/FUNDING.yml")
    targets.append(f"https://raw.githubusercontent.com/{username}/.github/main/FUNDING.yml")
    targets.append(f"https://raw.githubusercontent.com/{username}/.github/master/FUNDING.yml")

    for url in targets:
        try:
            text = get_text(url)
            logger.debug("Found FUNDING.yml at %s", url)
            return parse_funding_yml(text)
        except (
            OSError,
            TimeoutError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            ValueError,
        ):
            logger.debug("No FUNDING.yml at %s", url)
            continue
    logger.debug("No FUNDING.yml found for %r", username)
    return {}


def parse_funding_yml(text: str) -> dict[str, Any]:
    """Parse a FUNDING.yml file into a dict of platform→handle."""
    result: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip().strip('"').strip("'")
            if value and value.lower() not in ("null", "~", ""):
                result[key.strip()] = value
    return result


def load_local_funding_yml(search_dirs: list[Path] | None = None) -> dict[str, Any]:
    """Search for a local FUNDING.yml file and parse it."""
    if search_dirs is None:
        search_dirs = [Path.cwd(), Path.cwd() / ".github"]
    for directory in search_dirs:
        for name in ("FUNDING.yml", "FUNDING.yaml", "funding.yml", "funding.yaml"):
            candidate = directory / name
            if candidate.exists():
                return parse_funding_yml(candidate.read_text(encoding="utf-8"))
    return {}


# ---------------------------------------------------------------------------
# GitLab live data
# ---------------------------------------------------------------------------


def fetch_gitlab_profile(username: str, token: str | None = None) -> dict[str, Any]:
    """Fetch public GitLab user profile data."""
    logger.debug("Fetching GitLab profile for %r", username)
    try:
        url = f"https://gitlab.com/api/v4/users?username={username}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "pypi-profile/0.1")
        if token:
            req.add_header("PRIVATE-TOKEN", token)
        with open_http_url(req) as resp:
            users = json.loads(resp.read().decode())
        if not users:
            return {}
        user = users[0]
        return {
            "name": user.get("name", ""),
            "username": user.get("username", ""),
            "bio": user.get("bio", ""),
            "location": user.get("location", ""),
            "website_url": user.get("website_url", ""),
            "organization": user.get("organization", ""),
            "avatar_url": user.get("avatar_url", ""),
            "web_url": user.get("web_url", f"https://gitlab.com/{username}"),
        }
    except (
        json.JSONDecodeError,
        OSError,
        TimeoutError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        ValueError,
    ):
        logger.warning("Failed to fetch GitLab profile for %r", username, exc_info=False)
        return {}


# ---------------------------------------------------------------------------
# Mastodon live data
# ---------------------------------------------------------------------------


def fetch_mastodon_profile(account_url: str) -> dict[str, Any]:
    """Fetch a Mastodon user profile given a profile URL like https://fosstodon.org/@user."""
    logger.debug("Fetching Mastodon profile for %r", account_url)
    try:
        # Parse instance and username from URL
        m = re.match(r"https?://([^/]+)/@([^/]+)", account_url)
        if not m:
            return {}
        instance, username = m.group(1), m.group(2)
        url = f"https://{instance}/api/v1/accounts/lookup?acct={username}"
        req = urllib.request.Request(url, headers={"User-Agent": "pypi-profile/0.1"})
        with open_http_url(req) as resp:
            data = json.loads(resp.read().decode())
        # Parse metadata fields (e.g., verification links)
        fields = []
        for field in data.get("fields", []):
            fields.append(
                {
                    "name": field.get("name", ""),
                    "value": field.get("value", ""),
                    "verified_at": field.get("verified_at"),
                }
            )
        return {
            "username": data.get("username", ""),
            "display_name": data.get("display_name", ""),
            "note": re.sub(r"<[^>]+>", "", data.get("note", "")),
            "url": data.get("url", account_url),
            "followers_count": data.get("followers_count", 0),
            "fields": fields,
        }
    except (
        json.JSONDecodeError,
        OSError,
        TimeoutError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        ValueError,
    ):
        logger.warning("Failed to fetch Mastodon profile for %r", account_url, exc_info=False)
        return {}


# ---------------------------------------------------------------------------
# Profile assembly helpers
# ---------------------------------------------------------------------------


def merge_live_data_into_profile(profile_data: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    """Merge fetched live data into a profile dict, preferring existing non-empty values."""

    def fill(section: str, field: str, value: Any) -> None:
        if not profile_data.get(section, {}).get(field) and value:
            profile_data.setdefault(section, {})[field] = value

    github = live.get("github", {})
    gitlab = live.get("gitlab", {})
    mastodon = live.get("mastodon", {})
    pypi_packages = live.get("pypi_packages", [])

    # Fill identity from GitHub
    fill("identity", "location", github.get("location", "") or gitlab.get("location", ""))
    fill(
        "profile",
        "summary",
        github.get("bio", "") or gitlab.get("bio", "") or mastodon.get("note", ""),
    )
    fill("profile", "display_name", github.get("name", "") or gitlab.get("name", ""))
    fill("identity", "display_name", github.get("name", "") or gitlab.get("name", ""))
    fill("identity", "legal_name", github.get("name", "") or gitlab.get("name", ""))

    # Email from GitHub
    if github.get("email"):
        existing_emails = [c["value"] for c in profile_data.get("contact_methods", []) if c.get("kind") == "email"]
        if github["email"] not in existing_emails:
            profile_data.setdefault("contact_methods", []).append(
                {
                    "kind": "email",
                    "label": "GitHub email",
                    "value": github["email"],
                    "audience": ["general"],
                    "visibility": "public",
                }
            )

    # Twitter from GitHub
    if github.get("twitter_username"):
        existing_kinds = [p["kind"] for p in profile_data.get("profiles", [])]
        if "twitter" not in existing_kinds:
            profile_data.setdefault("profiles", []).append(
                {
                    "kind": "twitter",
                    "label": "Twitter/X",
                    "url": f"https://twitter.com/{github['twitter_username']}",
                    "verification": "self_asserted",
                }
            )

    # Blog/website from GitHub
    if github.get("blog"):
        blog = github["blog"]
        if not blog.startswith("http"):
            blog = f"https://{blog}"
        existing_contact = [c["value"] for c in profile_data.get("contact_methods", [])]
        if blog not in existing_contact:
            profile_data.setdefault("contact_methods", []).append(
                {
                    "kind": "website",
                    "label": "Personal website",
                    "value": blog,
                    "audience": ["general"],
                    "visibility": "public",
                }
            )

    # PyPI packages
    if pypi_packages and not profile_data.get("packages"):
        profile_data["packages"] = pypi_packages

    return profile_data
