"""Importers for external profile formats: JSON Resume, funding.yml, GitHub, GitLab, Mastodon, PyPI."""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, cast

from schema_resume import validate_resume  # type: ignore[import-untyped]

from pypi_profile.serialization import JSONDecodeError, json_loads

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
        return json_loads(cast(bytes, resp.read()))


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
    raw = json_loads(path.read_bytes())
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
            JSONDecodeError,
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


def _publisher_identity_url(publisher: dict[str, Any]) -> str:
    """Best-effort link to the publisher's home page (GitHub repo, GitLab project, etc.)."""
    kind = (publisher.get("kind") or "").lower()
    repo = publisher.get("repository") or ""
    if kind == "github" and repo:
        return f"https://github.com/{repo}"
    if kind == "gitlab" and repo:
        return f"https://gitlab.com/{repo}"
    if kind == "google":
        claims = publisher.get("claims") or {}
        return claims.get("iss", "") or ""
    return ""


def fetch_pypi_provenance(package_name: str) -> list[dict[str, Any]]:
    """Fetch per-file build provenance for a PyPI package.

    Uses the Simple API to enumerate files, then the Integrity API to fetch
    each file's provenance bundle. Returns a list of file-level records:

        [{
            "filename": "foo-1.0-py3-none-any.whl",
            "version": "1.0",
            "file_url": "https://files.pythonhosted.org/...",
            "provenance_url": "https://pypi.org/integrity/foo/1.0/foo-1.0.../provenance",
            "publishers": [
                {"kind": "GitHub", "repository": "org/foo", "workflow": "release.yml",
                 "environment": "", "identity_url": "https://github.com/org/foo"},
            ],
        }, ...]

    Trust posture: this code does NOT cryptographically verify the bundles; it
    relies on PyPI's server-side verification gate. Suitable for surfacing the
    publisher identity as reported by PyPI, not for independent assurance.
    """
    normalized = package_name.replace("_", "-").lower()
    simple_url = f"https://pypi.org/simple/{normalized}/"
    logger.debug("Fetching PyPI Simple API for %r", package_name)
    try:
        simple = get_json(simple_url, accept="application/vnd.pypi.simple.v1+json")
    except (
        JSONDecodeError,
        OSError,
        TimeoutError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        ValueError,
    ):
        logger.warning("Failed to fetch PyPI Simple API for %r", package_name, exc_info=False)
        return []

    records: list[dict[str, Any]] = []
    for file_info in simple.get("files", []):
        provenance_url = file_info.get("provenance")
        if not provenance_url:
            continue
        try:
            bundle = get_json(provenance_url, accept="application/vnd.pypi.integrity.v1+json")
        except (
            JSONDecodeError,
            OSError,
            TimeoutError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            ValueError,
        ):
            logger.warning("Failed to fetch provenance for %s", provenance_url, exc_info=False)
            continue

        publishers: list[dict[str, Any]] = []
        for ab in bundle.get("attestation_bundles", []):
            raw_pub = ab.get("publisher") or {}
            publishers.append(
                {
                    "kind": raw_pub.get("kind", ""),
                    "repository": raw_pub.get("repository", ""),
                    "workflow": raw_pub.get("workflow", ""),
                    "environment": raw_pub.get("environment", ""),
                    "claims": raw_pub.get("claims") or {},
                    "identity_url": _publisher_identity_url(raw_pub),
                    "attestation_count": len(ab.get("attestations", []) or []),
                }
            )

        records.append(
            {
                "filename": file_info.get("filename", ""),
                "version": file_info.get("version", ""),
                "file_url": file_info.get("url", ""),
                "provenance_url": provenance_url,
                "publishers": publishers,
            }
        )

    return records


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
            "maintainers": [m.get("username", "") for m in (info.get("maintainers") or [])],
            "classifiers": info.get("classifiers", []),
            "requires_python": info.get("requires_python", ""),
        }
    except (
        JSONDecodeError,
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
            data = json_loads(resp.read())
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
        JSONDecodeError,
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
                repos = json_loads(resp.read())
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
        JSONDecodeError,
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
            users = json_loads(resp.read())
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
        JSONDecodeError,
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
            data = json_loads(resp.read())
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
        JSONDecodeError,
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


def _validate_skip_trace_export(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate a skip_trace export when the defining model is available."""
    try:
        from skip_trace.pypi_profile_export import PypiProfileExchange
    except ImportError:
        return raw
    return PypiProfileExchange.model_validate(raw).model_dump(mode="json")


def from_skip_trace_export(path: Path) -> dict[str, Any]:
    """Convert a skip_trace pypi_profile exchange JSON file into profile data."""
    raw = json_loads(path.read_bytes())
    if not isinstance(raw, dict):
        raise ValueError("skip_trace export must be a JSON object")
    return from_skip_trace_export_dict(raw)


def from_skip_trace_export_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert one skip_trace pypi_profile exchange object into profile data."""
    return merge_skip_trace_exports([raw])


def merge_skip_trace_exports(raw_exports: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge one or more skip_trace exchange payloads into pypi_profile data."""
    exports = [_validate_skip_trace_export(raw) for raw in raw_exports]
    usernames: list[str] = []
    display_name = ""
    legal_name = ""
    summary = ""
    kind = "individual"
    organizations: list[str] = []
    contact_methods: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = []
    contact_keys: set[tuple[str, str]] = set()
    profile_urls: set[str] = set()
    package_names: set[str] = set()
    org_names: set[str] = set()

    for export in exports:
        subject = export.get("subject", {})
        subject_usernames = [str(value) for value in subject.get("pypi_usernames", []) if value]
        usernames.extend(subject_usernames)
        display_name = display_name or str(subject.get("display_name", "") or "")
        legal_name = legal_name or str(subject.get("legal_name", "") or "")
        summary = summary or str(subject.get("summary", "") or "")
        subject_kind = str(subject.get("kind", "") or "")
        if subject_kind in {"team", "company", "llc", "foundation", "collective", "project", "other"}:
            kind = subject_kind
        for organization in subject.get("organizations", []):
            org_value = str(organization or "")
            if org_value and org_value not in org_names:
                org_names.add(org_value)
                organizations.append(org_value)
        for contact in subject.get("contacts", []):
            kind_value = str(contact.get("kind", "") or "")
            value = str(contact.get("value", "") or "")
            key = (kind_value, value)
            if not kind_value or not value or key in contact_keys:
                continue
            contact_keys.add(key)
            contact_methods.append(
                {
                    "kind": kind_value,
                    "label": str(contact.get("label", "") or kind_value.title()),
                    "value": value,
                    "audience": ["general"],
                    "visibility": "public",
                }
            )
        for profile in subject.get("profiles", []):
            url = str(profile.get("url", "") or "")
            if not url or url in profile_urls:
                continue
            profile_urls.add(url)
            profiles.append(
                {
                    "kind": str(profile.get("kind", "") or "website"),
                    "label": str(profile.get("label", "") or "Website"),
                    "url": url,
                    "verification": "self_asserted",
                }
            )
        for package in subject.get("packages", []):
            name = str(package.get("name", "") or "")
            if not name or name in package_names:
                continue
            package_names.add(name)
            packages.append(
                {
                    "name": name,
                    "role": str(package.get("role", "") or "maintainer"),
                    "state": "active",
                    "summary": str(package.get("summary", "") or ""),
                    "url": str(package.get("url", "") or ""),
                }
            )

    username = next((username for username in usernames if username), "")
    if not display_name and organizations:
        display_name = organizations[0]
    if not legal_name:
        legal_name = display_name
    if not summary:
        if packages:
            package_list = ", ".join(pkg["name"] for pkg in packages[:3])
            summary = f"Maintains Python packages including {package_list}."
        else:
            summary = "Maintains Python packages."

    human_id = username or re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-") or "profile-owner"
    human_name = display_name or username
    profile_data: dict[str, Any] = {
        "profile": {
            "kind": kind,
            "display_name": human_name,
            "summary": summary,
        },
        "identity": {
            "legal_name": legal_name or human_name,
            "display_name": human_name,
            "pypi_username": username,
            "timezone": "",
            "location": "",
        },
        "humans": [
            {
                "id": human_id,
                "display_name": human_name,
                "role": "Owner",
            }
        ],
        "profiles": profiles,
        "contact_methods": contact_methods,
        "packages": packages,
    }
    return profile_data
