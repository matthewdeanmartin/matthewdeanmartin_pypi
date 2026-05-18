"""Live metadata fetcher for pypi-profile: PyPI, GitHub, GitLab, Mastodon."""

from __future__ import annotations

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
    fetch_pypi_provenance,
    fetch_pypi_user_packages,
)
from pypi_profile.models import ProfileData
from pypi_profile.serialization import JSONDecodeError, json_dumps, json_loads

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".pypi_profile_cache")
CACHE_TTL = 3600  # seconds


def cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    safe = key.replace("/", "_").replace(":", "_").replace("@", "_at_")
    return CACHE_DIR / f"{safe}.json"


def cache_read(key: str) -> Any | None:
    p = cache_path(key)
    if not p.exists():
        return None
    try:
        data = json_loads(p.read_bytes())
        if time.time() - data.get("ts", 0) > CACHE_TTL:
            logger.debug("Cache expired for key derived from %s", p.name)
            return None
        return data.get("payload")
    except (JSONDecodeError, OSError, TimeoutError, urllib.error.HTTPError, urllib.error.URLError, ValueError):
        logger.warning("Failed to read cache file %s", p, exc_info=True)
        return None


def cache_write(key: str, payload: Any) -> None:
    p = cache_path(key)
    p.write_text(json_dumps({"ts": time.time(), "payload": payload}), encoding="utf-8")


def fetch_provenance_for_packages(package_names: list[str], verbose: bool = False) -> dict[str, list[dict[str, Any]]]:
    """Fetch per-file provenance for each package, cached per package name."""
    out: dict[str, list[dict[str, Any]]] = {}
    for name in package_names:
        key = f"pypi_provenance_{name}"
        cached = cache_read(key)
        if cached is not None:
            out[name] = cached
            logger.debug("[cache] PyPI provenance for %s", name)
            if verbose:
                print(f"  [cache] PyPI provenance for {name}")
            continue
        logger.debug("[fetch] PyPI provenance for %s", name)
        if verbose:
            print(f"  [fetch] PyPI provenance for {name} ...")
        records = fetch_pypi_provenance(name)
        cache_write(key, records)
        out[name] = records
    return out


def collect_build_identities(
    provenance_by_package: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Collapse all per-file publishers across all packages into a deduped identity list.

    Each entry represents one (kind, repository, workflow, environment) tuple — i.e.
    one distinct build server identity that has published any wheel/sdist tracked here.

    The result is what you'd surface on a profile as "this person publishes from
    these CI accounts / repos" — independent of any single package.
    """
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for package_name, records in provenance_by_package.items():
        for rec in records:
            for pub in rec.get("publishers", []):
                key = (
                    (pub.get("kind") or "").lower(),
                    pub.get("repository") or "",
                    pub.get("workflow") or "",
                    pub.get("environment") or "",
                )
                entry = grouped.setdefault(
                    key,
                    {
                        "kind": pub.get("kind", ""),
                        "repository": pub.get("repository", ""),
                        "workflow": pub.get("workflow", ""),
                        "environment": pub.get("environment", ""),
                        "identity_url": pub.get("identity_url", ""),
                        "claims": pub.get("claims", {}),
                        "file_count": 0,
                        "packages": [],
                    },
                )
                entry["file_count"] += 1
                if package_name not in entry["packages"]:
                    entry["packages"].append(package_name)

    return sorted(
        grouped.values(),
        key=lambda e: (e["kind"].lower(), e["repository"], e["workflow"]),
    )


def fetch_all(
    profile: ProfileData,
    verbose: bool = False,
    include_owned: bool = False,
) -> dict[str, Any]:
    """Fetch live data for all services referenced in the profile.

    When include_owned is True, provenance is also fetched for every package
    returned by pypi_user_packages() — not just the ones explicitly declared
    in [[packages]]. This produces a more complete build-identity picture at
    the cost of roughly 2x more requests.
    """
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

    # Build provenance / publisher identities.
    package_names: list[str] = [pkg.name for pkg in profile.packages]
    if include_owned:
        for owned in results.get("pypi_packages", []):
            owned_name = owned.get("name") or ""
            if owned_name and owned_name not in package_names:
                package_names.append(owned_name)

    provenance_by_package = fetch_provenance_for_packages(package_names, verbose=verbose)
    results["provenance"] = provenance_by_package
    results["build_identities"] = collect_build_identities(provenance_by_package)

    return results


def compare_packages(profile: ProfileData, live_results: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare self-asserted package roles against PyPI live data."""
    pypi_username = profile.identity.pypi_username
    package_meta = live_results.get("package_meta", {})

    # Build a set of package names the user actually owns/maintains according to
    # the XML-RPC user_packages() endpoint — the authoritative source for ownership.
    # Per-package JSON info.maintainers is often empty for sole-owner packages.
    owned_names: set[str] = {p["name"].lower() for p in live_results.get("pypi_packages", [])}

    report = []
    for pkg in profile.packages:
        meta = package_meta.get(pkg.name, {})
        status = "unverified"
        note = ""
        if not meta:
            status = "no_data"
            note = "Could not fetch PyPI metadata"
        elif pypi_username and pkg.name.lower() in owned_names:
            status = "confirmed"
            note = f"PyPI confirms {pypi_username!r} is a maintainer/owner"
        elif pypi_username:
            status = "not_found"
            note = f"{pypi_username!r} not found as owner/maintainer on PyPI"
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
