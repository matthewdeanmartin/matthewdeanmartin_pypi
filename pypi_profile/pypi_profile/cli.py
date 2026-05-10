"""Command-line entry point for pypi-profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pypi_profile.__about__ import __version__


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the FastAPI profile server."""
    import uvicorn

    from pypi_profile.loader import find_profile, load_profile
    from pypi_profile.server import build_app

    toml_path = find_profile(args.source)
    profile = load_profile(toml_path)
    app = build_app(profile, allow_code=args.allow_code)
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate a pypi_profile.toml file."""
    from pydantic import ValidationError

    from pypi_profile.loader import load_profile

    path = Path(args.path)
    try:
        profile = load_profile(path)
        print(f"OK: {path}")
        print(f"  principal: {profile.profile.display_name!r} ({profile.profile.kind})")
        print(f"  packages:  {len(profile.packages)}")
        print(f"  projects:  {len(profile.projects)}")
        print(f"  humans:    {len(profile.humans)}")
    except ValidationError as exc:
        print(f"INVALID: {path}", file=sys.stderr)
        print(exc, file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_init(args: argparse.Namespace) -> None:
    """Create a starter pypi_profile.toml, optionally importing live data."""
    dest = Path(args.output or "pypi_profile.toml")
    if dest.exists() and not args.force:
        print(f"ERROR: {dest} already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    username = args.username or ""
    kind = args.kind or "individual"
    data: dict[str, Any] = {}

    # Import from JSON Resume if provided
    if args.from_json_resume:
        from pypi_profile.importers import from_json_resume

        jrp = Path(args.from_json_resume)
        if not jrp.exists():
            print(f"ERROR: JSON Resume file not found: {jrp}", file=sys.stderr)
            sys.exit(1)
        print(f"Importing JSON Resume from {jrp} ...")
        data = from_json_resume(jrp)
        # Override kind and username if explicitly specified
        if args.kind:
            data.setdefault("profile", {})["kind"] = kind
        if username:
            data.setdefault("identity", {})["pypi_username"] = username

    # Detect local funding.yml
    from pypi_profile.importers import load_local_funding_yml

    funding = load_local_funding_yml()
    if funding:
        print(f"Found local FUNDING.yml: {list(funding.keys())}")
        data["_funding"] = funding

    # Optionally fetch live data
    if args.fetch:
        pypi_username = username or data.get("identity", {}).get("pypi_username", "")
        github_url = ""
        for p in data.get("profiles", []):
            if p.get("kind") == "github":
                github_url = p.get("url", "")
                break
        if not pypi_username and not github_url:
            print("WARNING: --fetch requires --username or a GitHub profile in JSON Resume. Skipping live fetch.")
        else:
            import re

            from pypi_profile.importers import (
                _fetch_pypi_user_packages,
                fetch_github_funding,
                fetch_github_profile,
                fetch_github_repos,
                merge_live_data_into_profile,
            )

            live: dict[str, Any] = {}
            if pypi_username:
                print(f"Fetching PyPI packages for {pypi_username!r} ...")
                live["pypi_packages"] = _fetch_pypi_user_packages(pypi_username)
                print(f"  Found {len(live['pypi_packages'])} packages on PyPI.")
            if github_url:
                m = re.match(r"https?://github\.com/([^/]+)/?$", github_url)
                if m:
                    gh_user = m.group(1)
                    print(f"Fetching GitHub profile for {gh_user!r} ...")
                    live["github"] = fetch_github_profile(gh_user)
                    print(f"Fetching GitHub repos for {gh_user!r} ...")
                    live["github_repos"] = fetch_github_repos(gh_user)
                    print(f"  Found {len(live.get('github_repos', []))} repos on GitHub.")
                    print(f"Fetching FUNDING.yml from GitHub for {gh_user!r} ...")
                    gh_funding = fetch_github_funding(gh_user)
                    if gh_funding:
                        print(f"  Found funding platforms: {list(gh_funding.keys())}")
                        data["_funding"] = {**data.get("_funding", {}), **gh_funding}
            data = merge_live_data_into_profile(data, live)
            if live.get("pypi_packages"):
                data["packages"] = live["pypi_packages"]

    _write_toml_from_data(dest, data, username=username, kind=kind)
    print(f"Created {dest}")
    if not args.fetch:
        print("Tip: run with --fetch to pre-fill data from PyPI/GitHub/GitLab/Mastodon.")


def _write_toml_from_data(dest: Path, data: dict[str, Any], username: str = "", kind: str = "individual") -> None:
    """Write a pypi_profile.toml from a merged data dict."""

    profile_sec = data.get("profile", {})
    identity_sec = data.get("identity", {})
    humans = data.get("humans", [])
    profiles = data.get("profiles", [])
    contact_methods = data.get("contact_methods", [])
    packages = data.get("packages", [])
    projects = data.get("projects", [])
    work_experience = data.get("work_experience", [])
    hiring = data.get("hiring", {})
    contracting = data.get("contracting", {})
    contact_prefs = data.get("contact_preferences", {})
    succession = data.get("succession", {})
    verification = data.get("verification", {})
    funding = data.get("_funding", {})

    display_name = profile_sec.get("display_name", "") or identity_sec.get("display_name", "") or "Your Name"
    summary = profile_sec.get("summary", "") or "Python developer and package publisher."
    legal_name = identity_sec.get("legal_name", "") or display_name
    pypi_username = identity_sec.get("pypi_username", "") or username or "your-pypi-username"
    timezone = identity_sec.get("timezone", "") or "UTC"
    location = identity_sec.get("location", "") or ""

    lines: list[str] = []

    lines.append("[profile]")
    lines.append(f'kind = "{kind}"')
    lines.append(f"display_name = {_toml_str(display_name)}")
    lines.append(f"summary = {_toml_str(summary)}")
    lines.append("")

    lines.append("[identity]")
    lines.append(f"legal_name = {_toml_str(legal_name)}")
    lines.append(f"display_name = {_toml_str(display_name)}")
    lines.append(f"pypi_username = {_toml_str(pypi_username)}")
    lines.append('pronouns = ""')
    lines.append(f"timezone = {_toml_str(timezone)}")
    lines.append(f"location = {_toml_str(location)}")
    lines.append("")

    # Humans
    if not humans:
        humans = [{"id": pypi_username, "display_name": display_name, "role": "Owner"}]
    for h in humans:
        lines.append("[[humans]]")
        lines.append(f'id = {_toml_str(h.get("id", pypi_username))}')
        lines.append(f'display_name = {_toml_str(h.get("display_name", display_name))}')
        lines.append(f'role = {_toml_str(h.get("role", "Owner"))}')
        if h.get("bio"):
            lines.append(f'bio = {_toml_str(h["bio"])}')
        lines.append("")

    # Profiles (external links)
    if not profiles:
        profiles = [
            {
                "kind": "github",
                "label": "GitHub",
                "url": f"https://github.com/{pypi_username}",
                "verification": "self_asserted",
            }
        ]
    for p in profiles:
        lines.append("[[profiles]]")
        lines.append(f'kind = {_toml_str(p.get("kind", "website"))}')
        lines.append(f'label = {_toml_str(p.get("label", ""))}')
        lines.append(f'url = {_toml_str(p.get("url", ""))}')
        lines.append('verification = "self_asserted"')
        lines.append("")

    # Contact methods
    if not contact_methods:
        contact_methods = [
            {
                "kind": "email",
                "label": "Professional email",
                "value": "you@example.com",
                "audience": ["hiring", "consulting", "security"],
                "visibility": "public",
            }
        ]
    for c in contact_methods:
        lines.append("[[contact_methods]]")
        lines.append(f'kind = {_toml_str(c.get("kind", "email"))}')
        lines.append(f'label = {_toml_str(c.get("label", ""))}')
        lines.append(f'value = {_toml_str(c.get("value", ""))}')
        audience = c.get("audience", [])
        lines.append(f"audience = {json.dumps(audience)}")
        lines.append(f'visibility = {_toml_str(c.get("visibility", "public"))}')
        lines.append("")

    # Packages
    if packages:
        for pkg in packages:
            lines.append("[[packages]]")
            lines.append(f'name = {_toml_str(pkg.get("name", ""))}')
            lines.append(f'role = {_toml_str(pkg.get("role", "maintainer"))}')
            lines.append(f'state = {_toml_str(pkg.get("state", "active"))}')
            if pkg.get("summary"):
                lines.append(f'summary = {_toml_str(pkg["summary"])}')
            if pkg.get("url"):
                lines.append(f'url = {_toml_str(pkg["url"])}')
            lines.append("")
    else:
        lines.append("[[packages]]")
        lines.append('name = "your-package"')
        lines.append('role = "maintainer"')
        lines.append('state = "active"')
        lines.append('summary = "A Python package."')
        lines.append("")

    # Projects
    for proj in projects:
        lines.append("[[projects]]")
        lines.append(f'name = {_toml_str(proj.get("name", ""))}')
        lines.append(f'url = {_toml_str(proj.get("url", ""))}')
        lines.append(f'role = {_toml_str(proj.get("role", "creator"))}')
        lines.append(f'state = {_toml_str(proj.get("state", "active"))}')
        if proj.get("summary"):
            lines.append(f'summary = {_toml_str(proj["summary"])}')
        lines.append("")

    # Work experience
    for w in work_experience:
        lines.append("[[work_experience]]")
        lines.append(f'organization = {_toml_str(w.get("organization", ""))}')
        lines.append(f'title = {_toml_str(w.get("title", ""))}')
        lines.append(f'start_date = {_toml_str(w.get("start_date", ""))}')
        lines.append(f'end_date = {_toml_str(w.get("end_date", "present"))}')
        if w.get("summary"):
            lines.append(f'summary = {_toml_str(w["summary"])}')
        lines.append("")

    # Hiring
    lines.append("[hiring]")
    lines.append(f'open_to_work = {_toml_bool(hiring.get("open_to_work", False))}')
    lines.append(f'employment = {_toml_bool(hiring.get("employment", False))}')
    lines.append(f'contracting = {_toml_bool(hiring.get("contracting", False))}')
    lines.append(f'consulting = {_toml_bool(hiring.get("consulting", False))}')
    lines.append(f'speaking = {_toml_bool(hiring.get("speaking", False))}')
    lines.append(f'sponsorship = {_toml_bool(hiring.get("sponsorship", False))}')
    lines.append("")

    # Contracting
    if contracting:
        lines.append("[contracting]")
        lines.append(f'legal_entity = {_toml_str(contracting.get("legal_entity", ""))}')
        et = contracting.get("engagement_types", [])
        lines.append(f"engagement_types = {json.dumps(et)}")
        lines.append("")

    # Contact preferences
    if contact_prefs:
        lines.append("[contact_preferences]")
        dca = contact_prefs.get("do_contact_about", [])
        dnca = contact_prefs.get("do_not_contact_about", [])
        if dca:
            lines.append(f"do_contact_about = {json.dumps(dca)}")
        if dnca:
            lines.append(f"do_not_contact_about = {json.dumps(dnca)}")
        lines.append("")

    # Succession
    succ_policy = succession.get("policy", "") if succession else ""
    succ_reviewed = succession.get("last_reviewed", "") if succession else ""
    lines.append("[succession]")
    lines.append(f"policy = {_toml_str(succ_policy)}")
    lines.append(f"last_reviewed = {_toml_str(succ_reviewed)}")
    lines.append("")

    # Verification
    lines.append("[verification]")
    lines.append(f'public_key = {_toml_str(verification.get("public_key", "") if verification else "")}')
    lines.append('preferred_signature_backend = "minisign"')
    lines.append("")

    # Funding annotation (as TOML comment block)
    if funding:
        lines.append("# Funding / sponsorship platforms (from FUNDING.yml):")
        for platform, handle in funding.items():
            lines.append(f"# {platform}: {handle}")
        lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")


def _toml_str(s: object) -> str:
    s = str(s) if s is not None else ""
    return json.dumps(s)


def _toml_bool(b: object) -> str:
    return "true" if b else "false"


def cmd_inspect(args: argparse.Namespace) -> None:
    """Inspect a profile package or TOML file without executing code."""
    from pypi_profile.loader import find_profile, load_profile

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Profile file: {toml_path}")
    profile = load_profile(toml_path)
    print(f"Principal:    {profile.profile.display_name!r} ({profile.profile.kind})")
    print(f"PyPI user:    {profile.identity.pypi_username}")
    print(f"Packages:     {len(profile.packages)}")
    print(f"Projects:     {len(profile.projects)}")
    print(f"Humans:       {len(profile.humans)}")
    print(f"Profiles:     {len(profile.profiles)}")
    print(f"Public key:   {'yes' if profile.verification.public_key else 'no'}")
    print(f"Sig backend:  {profile.verification.preferred_signature_backend}")


def cmd_doctor(args: argparse.Namespace) -> None:
    """Diagnose local configuration and profile health."""
    import importlib

    ok = True

    def check(label: str, importable: str) -> None:
        nonlocal ok
        try:
            importlib.import_module(importable)
            print(f"  OK  {label}")
        except ImportError:
            print(f"  !!  {label} — not installed")
            ok = False

    def check_optional(label: str, importable: str) -> None:
        try:
            importlib.import_module(importable)
            print(f"  OK  {label} (optional)")
        except ImportError:
            print(f"  --  {label} — not installed (optional)")

    print("pypi-profile doctor")
    print(f"  version: {__version__}")
    print(f"  python:  {sys.version}")
    print()
    print("Required dependencies:")
    check("fastapi", "fastapi")
    check("uvicorn", "uvicorn")
    check("jinja2", "jinja2")
    check("pydantic", "pydantic")
    check("pluggy", "pluggy")
    check("pypi_ds", "pypi_ds")
    print()
    print("Optional dependencies:")
    check_optional("httpx (faster HTTP)", "httpx")
    check_optional("py-minisign (signing)", "minisign")
    check_optional("pyyaml (FUNDING.yml)", "yaml")
    print()
    print("Signing setup:")
    from pypi_profile.signing import DEFAULT_KEY_DIR, DEFAULT_SK_NAME

    sk_path = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
    if sk_path.exists():
        print(f"  OK  Secret key found at {sk_path}")
    else:
        print(f"  --  No secret key at {sk_path} (run: pypi-profile keygen)")
    print()
    if ok:
        print("All required checks passed.")
    else:
        print("Some required checks failed. Install missing dependencies.")
        sys.exit(1)


def cmd_fetch(args: argparse.Namespace) -> None:
    """Fetch live metadata from PyPI, GitHub, GitLab, and Mastodon."""
    from pypi_profile.fetcher import compare_packages, fetch_all
    from pypi_profile.loader import find_profile, load_profile

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    profile = load_profile(toml_path)
    print(f"Fetching live data for: {profile.profile.display_name!r}")
    print()

    live = fetch_all(profile, verbose=True)

    print()
    print("=== PyPI Package Comparison ===")
    report = compare_packages(profile, live)
    for item in report:
        status_icon = {
            "confirmed": "✓",
            "not_found": "✗",
            "no_data": "?",
            "unverified": "?",
        }.get(item["status"], "?")
        print(f"  {status_icon} {item['name']!r} (asserted: {item['asserted_role']}) — {item['note']}")
        if item.get("pypi_version"):
            print(f"      latest version: {item['pypi_version']}  {item.get('pypi_summary', '')[:80]}")

    if live.get("github"):
        gh = live["github"]
        print()
        print("=== GitHub ===")
        print(f"  Name:     {gh.get('name', '')}")
        print(f"  Bio:      {gh.get('bio', '')}")
        print(f"  Location: {gh.get('location', '')}")
        print(f"  Repos:    {len(live.get('github_repos', []))}")

    if live.get("gitlab"):
        gl = live["gitlab"]
        print()
        print("=== GitLab ===")
        print(f"  Name:     {gl.get('name', '')}")
        print(f"  Bio:      {gl.get('bio', '')}")
        print(f"  Location: {gl.get('location', '')}")

    if live.get("mastodon"):
        masto = live["mastodon"]
        print()
        print("=== Mastodon ===")
        print(f"  Display:  {masto.get('display_name', '')}")
        print(f"  Note:     {(masto.get('note', '') or '')[:120]}")
        print(f"  Followers:{masto.get('followers_count', 0)}")

    if live.get("github_funding"):
        print()
        print("=== Funding platforms (FUNDING.yml) ===")
        for platform, handle in live["github_funding"].items():
            print(f"  {platform}: {handle}")

    if args.json:
        print()
        print("=== Raw JSON ===")
        print(json.dumps(live, indent=2, default=str))


def cmd_keygen(args: argparse.Namespace) -> None:
    """Generate a minisign keypair for signing profile claims."""
    from pathlib import Path

    from pypi_profile.signing import generate_keypair

    key_dir = Path(args.key_dir).expanduser() if args.key_dir else None
    try:
        sk_path, pk_path, pub_b64 = generate_keypair(
            key_dir=key_dir,
            password=args.password,
            force=args.force,
        )
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Secret key: {sk_path}")
    print(f"Public key: {pk_path}")
    print()
    print("Add this public key to pypi_profile.toml [verification] section:")
    print(f'public_key = "{pub_b64}"')
    print()
    print("Keep your secret key private. Never commit it to version control.")


def cmd_sign(args: argparse.Namespace) -> None:
    """Sign a controls-url claim and print the proof string."""
    from pathlib import Path

    from pypi_profile.loader import find_profile, load_profile
    from pypi_profile.signing import sign_controls_url

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    profile = load_profile(toml_path)
    profile_package = profile.identity.pypi_username or "unknown"
    pypi_username = profile.identity.pypi_username

    sk_path = Path(args.key).expanduser() if args.key else None

    try:
        proof = sign_controls_url(
            profile_package=args.profile_package or f"pypi-profile-{profile_package}",
            pypi_username=pypi_username,
            subject_url=args.url,
            sk_path=sk_path,
            password=args.password,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Copy and paste the following proof string into your external profile page:")
    print()
    print(proof)
    print()
    print(f"Place it at: {args.url}")


def cmd_verify(args: argparse.Namespace) -> None:
    """Verify proof-of-control claims for all listed [[profiles]] entries."""
    from pypi_profile.loader import find_profile, load_profile
    from pypi_profile.verifier import verify_all_profiles

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    profile = load_profile(toml_path)

    if not profile.verification.public_key:
        print("WARNING: No public key in [verification]. Verification requires a public key.", file=sys.stderr)

    profile_package = args.profile_package or f"pypi-profile-{profile.identity.pypi_username}"

    try:
        results = verify_all_profiles(profile, profile_package=profile_package)
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    status_icons = {
        "verified": "✓",
        "unverified": "?",
        "invalid": "✗",
        "expired": "!",
        "self_asserted": "-",
        "unknown": "?",
    }

    print(f"Verifying claims for: {profile.profile.display_name!r}")
    print()
    for item in results:
        icon = status_icons.get(item["status"], "?")
        print(f"  [{icon}] {item['label']} ({item['url']}) — {item['status']}")

    verified = sum(1 for r in results if r["status"] == "verified")
    print()
    print(f"{verified}/{len(results)} claims verified.")


def cmd_api_dump(args: argparse.Namespace) -> None:
    """Dump profile data as JSON (for debugging/inspection)."""
    from pypi_profile.loader import find_profile, load_profile

    toml_path = find_profile(args.source)
    profile = load_profile(toml_path)
    print(json.dumps(profile.model_dump(), indent=2, default=str))


def main() -> None:
    """Run the pypi-profile CLI."""
    parser = argparse.ArgumentParser(
        prog="pypi-profile",
        description="The missing PyPI profile page.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    serve_p = subparsers.add_parser("serve", help="Start the profile web server")
    serve_p.add_argument("source", help="Profile package name, directory, or .toml path")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.add_argument("--allow-code", action="store_true", help="Enable plugin code execution")
    serve_p.set_defaults(func=cmd_serve)

    validate_p = subparsers.add_parser("validate", help="Validate a pypi_profile.toml")
    validate_p.add_argument("path", nargs="?", default="pypi_profile.toml")
    validate_p.set_defaults(func=cmd_validate)

    init_p = subparsers.add_parser("init", help="Create a starter pypi_profile.toml")
    init_p.add_argument(
        "--kind",
        default="individual",
        choices=[
            "individual",
            "team",
            "company",
            "llc",
            "foundation",
            "collective",
            "project",
            "other",
        ],
    )
    init_p.add_argument("--username", default="", help="PyPI username")
    init_p.add_argument("--output", default="", help="Output path (default: pypi_profile.toml)")
    init_p.add_argument("--force", action="store_true", help="Overwrite existing file")
    init_p.add_argument(
        "--from-json-resume",
        default="",
        metavar="PATH",
        help="Import from a JSON Resume file (resume.json)",
    )
    init_p.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch live data from PyPI, GitHub, GitLab, Mastodon",
    )
    init_p.set_defaults(func=cmd_init)

    inspect_p = subparsers.add_parser("inspect", help="Inspect a profile without executing code")
    inspect_p.add_argument("source", help="Profile package name, directory, or .toml path")
    inspect_p.set_defaults(func=cmd_inspect)

    doctor_p = subparsers.add_parser("doctor", help="Diagnose local setup")
    doctor_p.set_defaults(func=cmd_doctor)

    fetch_p = subparsers.add_parser("fetch", help="Fetch live metadata from PyPI, GitHub, GitLab, Mastodon")
    fetch_p.add_argument("source", help="Profile package name, directory, or .toml path")
    fetch_p.add_argument("--json", action="store_true", help="Also print raw JSON results")
    fetch_p.set_defaults(func=cmd_fetch)

    dump_p = subparsers.add_parser("dump", help="Dump profile data as JSON")
    dump_p.add_argument("source", help="Profile package name, directory, or .toml path")
    dump_p.set_defaults(func=cmd_api_dump)

    keygen_p = subparsers.add_parser("keygen", help="Generate a minisign keypair for signing claims")
    keygen_p.add_argument("--key-dir", default="", help="Directory to write key files (default: ~/.pypi_profile/)")
    keygen_p.add_argument("--password", default="", help="Password to encrypt the secret key (default: none)")
    keygen_p.add_argument("--force", action="store_true", help="Overwrite existing key files")
    keygen_p.set_defaults(func=cmd_keygen)

    sign_p = subparsers.add_parser("sign", help="Sign a proof-of-control claim for an external URL")
    sign_p.add_argument("claim_type", choices=["controls-url"], help="Claim type to sign")
    sign_p.add_argument("source", help="Profile package name, directory, or .toml path")
    sign_p.add_argument("--url", required=True, help="URL to assert control over")
    sign_p.add_argument("--key", default="", help="Path to secret key file (default: ~/.pypi_profile/minisign.key)")
    sign_p.add_argument("--password", default="", help="Password for the secret key")
    sign_p.add_argument("--profile-package", default="", help="Profile package name override")
    sign_p.set_defaults(func=cmd_sign)

    verify_p = subparsers.add_parser("verify", help="Verify proof-of-control claims for declared profile URLs")
    verify_p.add_argument("source", help="Profile package name, directory, or .toml path")
    verify_p.add_argument("--profile-package", default="", help="Profile package name override")
    verify_p.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
