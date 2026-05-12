"""Live metadata fetcher for pypi-profile: PyPI, GitHub, GitLab, Mastodon."""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
from pathlib import Path
from typing import Any

from pypi_profile.importers import (
    fetch_github_funding,
    fetch_github_profile,
    fetch_github_repos,
    fetch_gitlab_profile,
    fetch_mastodon_profile,
    fetch_pypi_package_info,
    fetch_pypi_user_packages,
)
from pypi_profile.models import ProfileData

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".pypi_profile_cache")
CACHE_TTL = 3600  # seconds
FETCH_ERRORS = (
    json.JSONDecodeError,
    OSError,
    TimeoutError,
    urllib.error.HTTPError,
    urllib.error.URLError,
    ValueError,
)


def cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    safe = key.replace("/", "_").replace(":", "_").replace("@", "_at_")
    return CACHE_DIR / f"{safe}.json"


def cache_read(key: str) -> Any | None:
    p = cache_path(key)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if time.time() - data.get("ts", 0) > CACHE_TTL:
            logger.debug("Cache expired for key derived from %s", p.name)
            return None
        return data.get("payload")
    except FETCH_ERRORS:
        logger.warning("Failed to read cache file %s", p, exc_info=True)
        return None


def cache_write(key: str, payload: Any) -> None:
    p = cache_path(key)
    p.write_text(json.dumps({"ts": time.time(), "payload": payload}), encoding="utf-8")


def fetch_all(profile: ProfileData, verbose: bool = False) -> dict[str, Any]:
    """Fetch live data for all services referenced in the profile."""
    results: dict[str, Any] = {}

    username = profile.identity.pypi_username
    if username:
        key = f"pypi_packages_{username}"
        cached = cache_read(key)
        if cached is not None:
            results["pypi_packages"] = cached
            logger.debug("[cache] PyPI packages for %s", username)
            if verbose:
                print(f"  [cache] PyPI packages for {username}")
        else:
            logger.debug("[fetch] PyPI packages for %s", username)
            if verbose:
                print(f"  [fetch] PyPI packages for {username} ...")
            pkgs = fetch_pypi_user_packages(username)
            cache_write(key, pkgs)
            results["pypi_packages"] = pkgs

    # Enrich each declared package with live PyPI metadata
    package_meta: dict[str, Any] = {}
    for pkg in profile.packages:
        key = f"pypi_pkg_{pkg.name}"
        cached = cache_read(key)
        if cached is not None:
            package_meta[pkg.name] = cached
        else:
            logger.debug("[fetch] PyPI package metadata: %s", pkg.name)
            if verbose:
                print(f"  [fetch] PyPI package metadata: {pkg.name} ...")
            meta = fetch_pypi_package_info(pkg.name)
            cache_write(key, meta)
            package_meta[pkg.name] = meta
    results["package_meta"] = package_meta

    # GitHub
    github_profile = {}
    github_repos = []
    for link in profile.profiles:
        if link.kind == "github" and link.url:
            gh_username = extract_github_username(link.url)
            if gh_username:
                key = f"github_profile_{gh_username}"
                cached = cache_read(key)
                if cached is not None:
                    github_profile = cached
                    logger.debug("[cache] GitHub profile for %s", gh_username)
                    if verbose:
                        print(f"  [cache] GitHub profile for {gh_username}")
                else:
                    logger.debug("[fetch] GitHub profile for %s", gh_username)
                    if verbose:
                        print(f"  [fetch] GitHub profile for {gh_username} ...")
                    github_profile = fetch_github_profile(gh_username)
                    cache_write(key, github_profile)

                key = f"github_repos_{gh_username}"
                cached = cache_read(key)
                if cached is not None:
                    github_repos = cached
                    logger.debug("[cache] GitHub repos for %s", gh_username)
                else:
                    logger.debug("[fetch] GitHub repos for %s", gh_username)
                    if verbose:
                        print(f"  [fetch] GitHub repos for {gh_username} ...")
                    github_repos = fetch_github_repos(gh_username)
                    cache_write(key, github_repos)

                key = f"github_funding_{gh_username}"
                cached = cache_read(key)
                if cached is not None:
                    results["github_funding"] = cached
                    logger.debug("[cache] GitHub FUNDING.yml for %s", gh_username)
                else:
                    logger.debug("[fetch] GitHub FUNDING.yml for %s", gh_username)
                    if verbose:
                        print(f"  [fetch] GitHub FUNDING.yml for {gh_username} ...")
                    funding = fetch_github_funding(gh_username)
                    cache_write(key, funding)
                    results["github_funding"] = funding
                break
    results["github"] = github_profile
    results["github_repos"] = github_repos

    # GitLab
    for link in profile.profiles:
        if link.kind == "gitlab" and link.url:
            gl_username = extract_gitlab_username(link.url)
            if gl_username:
                key = f"gitlab_profile_{gl_username}"
                cached = cache_read(key)
                if cached is not None:
                    results["gitlab"] = cached
                    logger.debug("[cache] GitLab profile for %s", gl_username)
                    if verbose:
                        print(f"  [cache] GitLab profile for {gl_username}")
                else:
                    logger.debug("[fetch] GitLab profile for %s", gl_username)
                    if verbose:
                        print(f"  [fetch] GitLab profile for {gl_username} ...")
                    gl = fetch_gitlab_profile(gl_username)
                    cache_write(key, gl)
                    results["gitlab"] = gl
                break

    # Mastodon
    for link in profile.profiles:
        if link.kind == "mastodon" and link.url:
            key = f"mastodon_{link.url}"
            cached = cache_read(key)
            if cached is not None:
                results["mastodon"] = cached
                logger.debug("[cache] Mastodon profile for %s", link.url)
                if verbose:
                    print(f"  [cache] Mastodon profile for {link.url}")
            else:
                logger.debug("[fetch] Mastodon profile for %s", link.url)
                if verbose:
                    print(f"  [fetch] Mastodon profile for {link.url} ...")
                masto = fetch_mastodon_profile(link.url)
                cache_write(key, masto)
                results["mastodon"] = masto
            break

    return results


def compare_packages(profile: ProfileData, live_results: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare self-asserted package roles against PyPI live data."""
    pypi_username = profile.identity.pypi_username
    package_meta = live_results.get("package_meta", {})
    report = []
    for pkg in profile.packages:
        meta = package_meta.get(pkg.name, {})
        maintainers = meta.get("maintainers", [])
        status = "unverified"
        note = ""
        if not meta:
            status = "no_data"
            note = "Could not fetch PyPI metadata"
        elif pypi_username and pypi_username in maintainers:
            status = "confirmed"
            note = f"PyPI confirms {pypi_username!r} is a maintainer/owner"
        elif pypi_username:
            status = "not_found"
            note = f"{pypi_username!r} not in PyPI maintainer list: {maintainers}"
        report.append(
            {
                "name": pkg.name,
                "asserted_role": pkg.role,
                "status": status,
                "note": note,
                "pypi_summary": meta.get("summary", ""),
                "pypi_version": meta.get("version", ""),
            }
        )
    return report


def extract_github_username(url: str) -> str:
    m = re.match(r"https?://github\.com/([^/]+)/?$", url)
    return m.group(1) if m else ""


def extract_gitlab_username(url: str) -> str:
    m = re.match(r"https?://gitlab\.com/([^/]+)/?$", url)
    return m.group(1) if m else ""
