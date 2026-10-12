"""Static site generator for pypi-profile."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STATIC_ROUTES: list[tuple[str, str]] = [
    ("/", "index.html"),
    ("/packages", "packages/index.html"),
    ("/projects", "projects/index.html"),
    ("/resume", "resume/index.html"),
    ("/hiring", "hiring/index.html"),
    ("/contact", "contact/index.html"),
    ("/verification", "verification/index.html"),
    ("/succession", "succession/index.html"),
    ("/people", "people/index.html"),
]

JSON_ROUTES: list[tuple[str, str]] = [
    ("/api/profile.json", "api/profile.json"),
    ("/api/packages.json", "api/packages.json"),
    ("/api/projects.json", "api/projects.json"),
    ("/api/people.json", "api/people.json"),
    ("/api/verification.json", "api/verification.json"),
]


def find_resume(toml_path: Path) -> Path | None:
    """Look for resume.json next to the given toml, in the parent, or in a resources/ sibling."""
    candidates = [
        toml_path.parent / "resume.json",
        toml_path.parent.parent / "resume.json",
        toml_path.parent / "resources" / "resume.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def build_static_site(
    source: str,
    output: Path,
    resume_file: Path | None = None,
    base_url: str = "/",
    verbose: bool = True,
) -> dict[str, Any]:
    """Build a static site from a profile source.

    Returns a summary dict with counts of files written.
    """
    from starlette.testclient import TestClient

    from pypi_profile.loader import find_profile, load_profile
    from pypi_profile.server import build_app

    toml_path = find_profile(source)
    profile = load_profile(toml_path)

    logger.info(
        "Building static site for %r (base_url=%r)",
        profile.profile.display_name,
        base_url,
    )
    if verbose:
        print(f"Building static site for {profile.profile.display_name!r}...")

    app = build_app(
        profile,
        allow_code=False,
        static_mode=True,
        base_url=base_url.rstrip("/"),
    )
    client = TestClient(app, raise_server_exceptions=True)

    output.mkdir(parents=True, exist_ok=True)

    html_count = 0
    for route, rel_path in STATIC_ROUTES:
        resp = client.get(route)
        if resp.status_code == 404:
            logger.debug("Route %s returned 404, skipping", route)
            continue
        dest = output / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(resp.text, encoding="utf-8")
        html_count += 1
        logger.debug("Rendered %s -> %s", route, rel_path)
        if verbose:
            print(f"  rendered {route} -> {rel_path}")

    json_count = 0
    for route, rel_path in JSON_ROUTES:
        resp = client.get(route)
        if resp.status_code != 200:
            logger.warning("JSON route %s returned HTTP %s", route, resp.status_code)
        dest = output / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(resp.text, encoding="utf-8")
        json_count += 1
        logger.debug("Rendered %s -> %s", route, rel_path)

    resume_path = resume_file or find_resume(toml_path)
    resume_written = False
    if resume_path and resume_path.exists():
        resume_dest = output / "api" / "resume.json"
        resume_dest.parent.mkdir(parents=True, exist_ok=True)
        resume_dest.write_text(resume_path.read_text(encoding="utf-8"), encoding="utf-8")
        json_count += 1
        resume_written = True
        logger.debug("Copied resume.json -> api/resume.json")
        if verbose:
            print("  resume.json -> api/resume.json")

    copy_static_assets(output, verbose=verbose)

    logger.info(
        "Build complete: %d HTML pages, %d JSON files -> %s",
        html_count,
        json_count,
        output,
    )
    if verbose:
        print()
        summary_lines = [
            f"  {html_count} HTML pages",
            f"  {json_count} JSON files",
        ]
        if resume_written:
            summary_lines.append("  resume.json published at api/resume.json")
        print(f"Output: {output}/")
        for line in summary_lines:
            print(line)
        print()
        print("Next steps:")
        print("  GitHub Pages:      push contents of dist/ to your gh-pages branch")
        print("  Cloudflare Pages:  connect repo, set build output directory to dist/")
        print("  Netlify:           drag and drop the dist/ folder")

    return {
        "html_pages": html_count,
        "json_files": json_count,
        "resume_published": resume_written,
        "output": str(output),
    }


def copy_static_assets(output: Path, verbose: bool = True) -> None:
    from pypi_profile.ds.paths import static_root_path

    static_src = static_root_path()
    static_dest = output / "static" / "pypi_ds"
    logger.debug("Copying static assets %s -> %s", static_src, static_dest)
    if static_dest.exists():
        shutil.rmtree(static_dest)
    shutil.copytree(static_src, static_dest)
    if verbose:
        print("  copied static assets -> static/pypi_ds/")
