"""Command-line entry point for pypi-profile."""

# pylint: disable=too-many-lines

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pypi_profile.__about__ import __version__


class _LazyLogger:
    """Resolve the module logger only when a command actually uses it."""

    def __getattr__(self, name: str) -> Any:
        import logging

        return getattr(logging.getLogger(__name__), name)


logger: Any = _LazyLogger()

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_IO = 3


class CliError(Exception):
    """An expected, user-facing CLI failure."""

    def __init__(self, message: str, exit_code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def is_dry_run(args: argparse.Namespace) -> bool:
    """Return True when the current command should avoid side effects."""
    return bool(getattr(args, "dry_run", False))


def print_dry_run(action: str, details: list[str] | None = None) -> None:
    """Print a consistent dry-run summary."""
    print(f"DRY RUN: {action}")
    for detail in details or []:
        print(f"  - {detail}")


def add_dry_run_argument(command_parser: argparse.ArgumentParser) -> None:
    """Add the standard --dry-run flag to a subcommand parser."""
    command_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Describe what would happen without making changes, network calls, or launching services/UI.",
    )


def add_interactive_arguments(command_parser: argparse.ArgumentParser) -> None:
    """Add the standard interactive flags to a subcommand parser."""
    command_parser.add_argument(
        "--interactive",
        action="store_true",
        default=False,
        help="Prompt for missing or defaulted values when running in a terminal.",
    )
    command_parser.add_argument(
        "--no-interactive",
        action="store_true",
        default=False,
        help="Disable prompts and require fully specified flags for scripting/CI.",
    )


def configure_console_streams() -> None:
    """Ensure stdout/stderr can emit Unicode on Windows consoles."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _json_dumps(value: Any, **kwargs: Any) -> str:
    from pypi_profile.serialization import json_dumps

    return json_dumps(value, **kwargs)


def emit_json(value: Any) -> None:
    """Write a machine-readable JSON payload to stdout."""
    print(_json_dumps(value, indent=2, default=str))


def wants_json_output(args: argparse.Namespace) -> bool:
    """Return True when the command should emit machine-readable JSON."""
    return bool(getattr(args, "json", False))


def can_prompt() -> bool:
    """Return True when stdin/stdout are both interactive terminals."""
    return bool(sys.stdin.isatty() and sys.stdout.isatty())


def wants_interactive(args: argparse.Namespace) -> bool:
    """Return True when the command should prompt for values."""
    if getattr(args, "no_interactive", False):
        return False
    if getattr(args, "interactive", False):
        if not can_prompt():
            raise CliError(
                "--interactive requires an interactive terminal.", EXIT_USAGE
            )
        return True
    return can_prompt()


def prompt_text(
    label: str,
    *,
    default: str = "",
    required: bool = False,
    choices: Sequence[str] | None = None,
    secret: bool = False,
) -> str:
    """Prompt for a single text value."""
    options_hint = f" ({', '.join(choices)})" if choices else ""
    default_hint = f" [{default}]" if default else ""
    prompt = f"{label}{options_hint}{default_hint}: "

    while True:
        response = getpass.getpass(prompt) if secret else input(prompt)
        value = response.strip() or default
        if required and not value:
            print("A value is required.", file=sys.stderr)
            continue
        if choices and value and value not in choices:
            print(f"Choose one of: {', '.join(choices)}", file=sys.stderr)
            continue
        return value


def prompt_bool(label: str, *, default: bool = False) -> bool:
    """Prompt for a yes/no value."""
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        value = input(f"{label} {suffix}: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please enter y or n.", file=sys.stderr)


def require_value(
    args: argparse.Namespace,
    name: str,
    *,
    label: str,
    default: str = "",
    choices: Sequence[str] | None = None,
    secret: bool = False,
) -> str:
    """Return a required argument value, prompting when interactive mode is enabled."""
    current = str(getattr(args, name, "") or "").strip()
    if current:
        return current
    if wants_interactive(args):
        value = prompt_text(
            label, default=default, required=True, choices=choices, secret=secret
        )
        setattr(args, name, value)
        return value
    raise CliError(
        f"{label} is required. Re-run with --interactive to be prompted.", EXIT_USAGE
    )


def maybe_prompt_value(
    args: argparse.Namespace,
    name: str,
    *,
    label: str,
    default: str = "",
    choices: Sequence[str] | None = None,
    secret: bool = False,
) -> str:
    """Prompt for a value only when interactive mode is enabled and the argument is unset."""
    current = str(getattr(args, name, "") or "").strip()
    if current:
        return current
    if wants_interactive(args):
        value = prompt_text(label, default=default, choices=choices, secret=secret)
        setattr(args, name, value)
        return value
    return default


def maybe_prompt_bool(
    args: argparse.Namespace, name: str, *, label: str, default: bool = False
) -> bool:
    """Prompt for a boolean value only when interactive mode is enabled and the default is still in use."""
    current = bool(getattr(args, name, default))
    if current != default:
        return current
    if wants_interactive(args):
        current = prompt_bool(label, default=default)
        setattr(args, name, current)
    return current


def maybe_prompt_path(
    args: argparse.Namespace, name: str, *, label: str, default: str = ""
) -> str:
    """Prompt for a path-like argument when interactive mode is enabled."""
    return maybe_prompt_value(args, name, label=label, default=default)


def raise_invalid_profile(toml_path: Path, errors: Sequence[Any]) -> None:
    """Raise a formatted validation failure."""
    lines = [f"INVALID: {toml_path}"]
    for err in errors:
        loc = (
            " -> ".join(str(part) for part in err["loc"])
            if err.get("loc")
            else "(root)"
        )
        lines.append(f"  {loc}: {err['msg']}")
    raise CliError("\n".join(lines), EXIT_USAGE)


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the FastAPI profile server."""
    import uvicorn

    from pypi_profile.server import build_app

    maybe_prompt_path(args, "source", label="Profile source (leave blank for hub mode)")
    args.host = maybe_prompt_value(args, "host", label="Host", default="127.0.0.1")
    args.port = int(maybe_prompt_value(args, "port", label="Port", default="8000"))
    args.allow_code = maybe_prompt_bool(
        args, "allow_code", label="Allow plugin code execution", default=False
    )

    if not args.source:
        # Hub mode: no source given — discover all installed profiles.
        from pypi_profile.loader import discover_installed_profiles

        if is_dry_run(args):
            entries = discover_installed_profiles()
            print_dry_run(
                "serve would start the hub server listing all installed profiles.",
                [
                    f"profiles_found={len(entries)}",
                    f"host={args.host}",
                    f"port={args.port}",
                ],
            )
            return

        # Build a minimal stub profile just to anchor the app, then let hub routes take over.
        entries = discover_installed_profiles()
        if not entries:
            raise CliError(
                "No installed profiles found. Pass a source or install a pypi-profile-* package.",
                EXIT_USAGE,
            )
        _pkg_name, toml_path, first_profile = entries[0]
        logger.info(
            "Starting hub server on %s:%s (%d profiles)",
            args.host,
            args.port,
            len(entries),
        )
        app = build_app(first_profile, allow_code=args.allow_code, include_hub=True)
        uvicorn.run(app, host=args.host, port=args.port)
        return

    from pypi_profile.loader import find_profile, load_profile

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        raise CliError(str(exc), EXIT_USAGE) from exc
    profile = load_profile(toml_path, autopatch_public_key=not is_dry_run(args))
    if is_dry_run(args):
        print_dry_run(
            "serve would start the profile server.",
            [
                f"profile={toml_path}",
                f"display_name={profile.profile.display_name!r}",
                f"host={args.host}",
                f"port={args.port}",
                f"allow_code={args.allow_code}",
            ],
        )
        return

    logger.info(
        "Starting server for %r on %s:%s",
        profile.profile.display_name,
        args.host,
        args.port,
    )
    app = build_app(profile, allow_code=args.allow_code, include_hub=True)
    uvicorn.run(app, host=args.host, port=args.port)


def key_status() -> str:
    """Return a one-line summary of where the signing key was found."""
    import os

    from pypi_profile.signing import (
        DEFAULT_KEY_DIR,
        DEFAULT_SK_NAME,
        keyring_is_usable,
        keyring_username,
        load_key_bytes_from_keyring,
    )

    env_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
    if env_path:
        sk_path = Path(env_path).expanduser()
        return f"found ({sk_path})" if sk_path.exists() else f"not found ({sk_path})"

    if keyring_is_usable():
        if load_key_bytes_from_keyring() is not None:
            return f"found in keyring (username={keyring_username()!r})"
        return f"not found in keyring (username={keyring_username()!r})"

    sk_path = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
    if sk_path.exists():
        return f"found ({sk_path})"
    return f"not found (expected {sk_path})"


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate a pypi_profile.toml — thin shim kept for backward compatibility."""
    args.path = maybe_prompt_path(
        args, "path", label="Profile source", default="pypi_profile.toml"
    )
    args.source = getattr(args, "source", None) or getattr(
        args, "path", "pypi_profile.toml"
    )
    args.no_validate = False
    cmd_inspect(args)


def cmd_init(args: argparse.Namespace) -> None:
    """Create a starter pypi_profile.toml, optionally importing live data."""
    dest = Path(args.output or "pypi_profile.toml")
    username = args.username or ""
    kind = args.kind or "individual"
    from_skip_trace = str(getattr(args, "from_skip_trace", "") or "")

    if is_dry_run(args):
        if dest.exists() and not args.force:
            logger.error(
                "Output file %s already exists (use --force to overwrite)", dest
            )
            raise CliError(
                f"{dest} already exists. Use --force to overwrite.", EXIT_USAGE
            )
        if args.from_json_resume:
            jrp = Path(args.from_json_resume)
            if not jrp.exists():
                logger.error("JSON Resume file not found: %s", jrp)
                raise CliError(f"JSON Resume file not found: {jrp}", EXIT_USAGE)
        if from_skip_trace:
            stp = Path(from_skip_trace)
            if not stp.exists():
                logger.error("skip_trace export file not found: %s", stp)
                raise CliError(f"skip_trace export file not found: {stp}", EXIT_USAGE)
        details = [
            f"output={dest}",
            f"kind={kind}",
            f"username={username or '(auto/default)'}",
            f"from_json_resume={args.from_json_resume or '(none)'}",
            f"from_skip_trace={from_skip_trace or '(none)'}",
            f"fetch_live_data={args.fetch}",
            f"force={args.force}",
        ]
        if sys.stdin.isatty() and not getattr(args, "no_interactive", False):
            details.append("interactive wizard would normally run")
        print_dry_run("init would create a starter pypi_profile.toml.", details)
        return

    # Interactive wizard: runs when stdin is a TTY and --no-interactive is not set
    use_wizard = wants_interactive(args)

    if use_wizard:
        try:
            from pypi_profile.wizard import run_wizard

            data = run_wizard(dest, from_json_resume=args.from_json_resume or "")
            write_toml_from_data(
                dest,
                data,
                username=data.get("identity", {}).get("pypi_username", ""),
                kind=data.get("profile", {}).get("kind", "individual"),
            )
            print(f"\nCreated {dest}")
            print("Run  pypi-profile serve .  to preview your profile.")
            return
        except (ImportError, KeyboardInterrupt):
            logger.debug("Interactive wizard unavailable or interrupted", exc_info=True)
            print()  # newline after ^C

    # Non-interactive / scripted path (unchanged behaviour)
    if dest.exists() and not args.force:
        logger.error("Output file %s already exists (use --force to overwrite)", dest)
        raise CliError(f"{dest} already exists. Use --force to overwrite.", EXIT_USAGE)

    profile_data: dict[str, Any] = {}

    # Import from JSON Resume or skip_trace export if provided
    if args.from_json_resume:
        from pypi_profile.importers import from_json_resume

        jrp = Path(args.from_json_resume)
        if not jrp.exists():
            logger.error("JSON Resume file not found: %s", jrp)
            raise CliError(f"JSON Resume file not found: {jrp}", EXIT_USAGE)
        print(f"Importing JSON Resume from {jrp} ...")
        profile_data = from_json_resume(jrp)
        if args.kind:
            profile_data.setdefault("profile", {})["kind"] = kind
    elif from_skip_trace:
        from pypi_profile.importers import from_skip_trace_export

        stp = Path(from_skip_trace)
        if not stp.exists():
            logger.error("skip_trace export file not found: %s", stp)
            raise CliError(f"skip_trace export file not found: {stp}", EXIT_USAGE)
        print(f"Importing skip_trace export from {stp} ...")
        profile_data = from_skip_trace_export(stp)
        if args.kind:
            profile_data.setdefault("profile", {})["kind"] = kind

    # --username always wins over whatever the JSON resume inferred
    if username:
        profile_data.setdefault("identity", {})["pypi_username"] = username

    # Detect local funding.yml
    from pypi_profile.importers import load_local_funding_yml

    funding = load_local_funding_yml()
    if funding:
        print(f"Found local FUNDING.yml: {list(funding.keys())}")
        profile_data["funding"] = funding

    # Optionally fetch live data
    if args.fetch:
        pypi_username = (
            profile_data.get("identity", {}).get("pypi_username", "") or username
        )
        github_url = ""
        for p in profile_data.get("profiles", []):
            if p.get("kind") == "github":
                github_url = p.get("url", "")
                break
        if not pypi_username and not github_url:
            print(
                "WARNING: --fetch requires --username or a GitHub profile in JSON Resume. Skipping live fetch."
            )
        else:
            import re

            from pypi_profile.importers import (
                fetch_github_funding,
                fetch_github_profile,
                fetch_github_repos,
                fetch_pypi_user_packages,
                merge_live_data_into_profile,
            )

            live: dict[str, Any] = {}
            if pypi_username:
                print(f"Fetching PyPI packages for {pypi_username!r} ...")
                live["pypi_packages"] = fetch_pypi_user_packages(pypi_username)
                print(f"  Found {len(live['pypi_packages'])} packages on PyPI.")
            if github_url:
                m = re.match(r"https?://github\.com/([^/]+)/?$", github_url)
                if m:
                    gh_user = m.group(1)
                    print(f"Fetching GitHub profile for {gh_user!r} ...")
                    live["github"] = fetch_github_profile(gh_user)
                    print(f"Fetching GitHub repos for {gh_user!r} ...")
                    live["github_repos"] = fetch_github_repos(gh_user)
                    print(
                        f"  Found {len(live.get('github_repos', []))} repos on GitHub."
                    )
                    print(f"Fetching FUNDING.yml from GitHub for {gh_user!r} ...")
                    gh_funding = fetch_github_funding(gh_user)
                    if gh_funding:
                        print(f"  Found funding platforms: {list(gh_funding.keys())}")
                        profile_data["funding"] = {
                            **profile_data.get("funding", {}),
                            **gh_funding,
                        }
            profile_data = merge_live_data_into_profile(profile_data, live)
            if live.get("pypi_packages"):
                profile_data["packages"] = live["pypi_packages"]

    write_toml_from_data(dest, profile_data, username=username, kind=kind)
    print(f"Created {dest}")
    if not args.fetch:
        print(
            "Tip: run with --fetch to pre-fill data from PyPI/GitHub/GitLab/Mastodon."
        )


def write_toml_from_data(
    dest: Path, data: dict[str, Any], username: str = "", kind: str = "individual"
) -> None:
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
    funding = data.get("funding", {})

    display_name = (
        profile_sec.get("display_name", "")
        or identity_sec.get("display_name", "")
        or "Your Name"
    )
    summary = (
        profile_sec.get("summary", "") or "Python developer and package publisher."
    )
    legal_name = identity_sec.get("legal_name", "") or display_name
    pypi_username = (
        identity_sec.get("pypi_username", "") or username or "your-pypi-username"
    )
    timezone = identity_sec.get("timezone", "") or "UTC"
    location = identity_sec.get("location", "") or ""

    lines: list[str] = []

    lines.append("[profile]")
    lines.append(f'kind = "{kind}"')
    lines.append(f"display_name = {toml_str(display_name)}")
    lines.append(f"summary = {toml_str(summary)}")
    lines.append("")

    lines.append("[identity]")
    lines.append(f"legal_name = {toml_str(legal_name)}")
    lines.append(f"display_name = {toml_str(display_name)}")
    lines.append(f"pypi_username = {toml_str(pypi_username)}")
    lines.append('pronouns = ""')
    lines.append(f"timezone = {toml_str(timezone)}")
    lines.append(f"location = {toml_str(location)}")
    lines.append("")

    # Humans
    if not humans:
        humans = [{"id": pypi_username, "display_name": display_name, "role": "Owner"}]
    for h in humans:
        lines.append("[[humans]]")
        lines.append(f'id = {toml_str(h.get("id", pypi_username))}')
        lines.append(f'display_name = {toml_str(h.get("display_name", display_name))}')
        lines.append(f'role = {toml_str(h.get("role", "Owner"))}')
        if h.get("bio"):
            lines.append(f'bio = {toml_str(h["bio"])}')
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
        lines.append(f'kind = {toml_str(p.get("kind", "website"))}')
        lines.append(f'label = {toml_str(p.get("label", ""))}')
        lines.append(f'url = {toml_str(p.get("url", ""))}')
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
        lines.append(f'kind = {toml_str(c.get("kind", "email"))}')
        lines.append(f'label = {toml_str(c.get("label", ""))}')
        lines.append(f'value = {toml_str(c.get("value", ""))}')
        audience = c.get("audience", [])
        lines.append(f"audience = {_json_dumps(audience)}")
        lines.append(f'visibility = {toml_str(c.get("visibility", "public"))}')
        lines.append("")

    # Packages
    if packages:
        for pkg in packages:
            lines.append("[[packages]]")
            lines.append(f'name = {toml_str(pkg.get("name", ""))}')
            lines.append(f'role = {toml_str(pkg.get("role", "maintainer"))}')
            lines.append(f'state = {toml_str(pkg.get("state", "active"))}')
            if pkg.get("summary"):
                lines.append(f'summary = {toml_str(pkg["summary"])}')
            if pkg.get("url"):
                lines.append(f'url = {toml_str(pkg["url"])}')
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
        lines.append(f'name = {toml_str(proj.get("name", ""))}')
        lines.append(f'url = {toml_str(proj.get("url", ""))}')
        lines.append(f'role = {toml_str(proj.get("role", "creator"))}')
        lines.append(f'state = {toml_str(proj.get("state", "active"))}')
        if proj.get("summary"):
            lines.append(f'summary = {toml_str(proj["summary"])}')
        lines.append("")

    # Work experience
    for w in work_experience:
        lines.append("[[work_experience]]")
        lines.append(f'organization = {toml_str(w.get("organization", ""))}')
        lines.append(f'title = {toml_str(w.get("title", ""))}')
        lines.append(f'start_date = {toml_str(w.get("start_date", ""))}')
        lines.append(f'end_date = {toml_str(w.get("end_date", "present"))}')
        if w.get("summary"):
            lines.append(f'summary = {toml_str(w["summary"])}')
        lines.append("")

    # Hiring
    lines.append("[hiring]")
    lines.append(
        f'open_to_work_since = {toml_str(hiring.get("open_to_work_since", ""))}'
    )
    et = hiring.get("employment_types", [])
    lines.append(f"employment_types = {_json_dumps(et)}")
    wm = hiring.get("work_model", [])
    lines.append(f"work_model = {_json_dumps(wm)}")
    jur = hiring.get("jurisdiction", [])
    lines.append(f"jurisdiction = {_json_dumps(jur)}")
    lines.append(f'speaking = {toml_bool(hiring.get("speaking", False))}')
    lines.append(f'sponsorship = {toml_bool(hiring.get("sponsorship", False))}')
    lines.append("")

    # Contracting
    if contracting:
        lines.append("[contracting]")
        lines.append(f'legal_entity = {toml_str(contracting.get("legal_entity", ""))}')
        et = contracting.get("engagement_types", [])
        lines.append(f"engagement_types = {_json_dumps(et)}")
        lines.append("")

    # Contact preferences
    if contact_prefs:
        lines.append("[contact_preferences]")
        dca = contact_prefs.get("do_contact_about", [])
        dnca = contact_prefs.get("do_not_contact_about", [])
        if dca:
            lines.append(f"do_contact_about = {_json_dumps(dca)}")
        if dnca:
            lines.append(f"do_not_contact_about = {_json_dumps(dnca)}")
        lines.append("")

    # Succession
    succ_policy = succession.get("policy", "") if succession else ""
    succ_reviewed = succession.get("last_reviewed", "") if succession else ""
    lines.append("[succession]")
    lines.append(f"policy = {toml_str(succ_policy)}")
    lines.append(f"last_reviewed = {toml_str(succ_reviewed)}")
    lines.append("")

    # Verification
    lines.append("[verification]")
    lines.append(
        f'public_key = {toml_str(verification.get("public_key", "") if verification else "")}'
    )
    lines.append('preferred_signature_backend = "minisign"')
    lines.append("")

    # Funding annotation (as TOML comment block)
    if funding:
        lines.append("# Funding / sponsorship platforms (from FUNDING.yml):")
        for platform, handle in funding.items():
            lines.append(f"# {platform}: {handle}")
        lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")


def toml_str(s: object) -> str:
    s = str(s) if s is not None else ""
    return _json_dumps(s)


def toml_bool(b: object) -> str:
    return "true" if b else "false"


def cmd_inspect(args: argparse.Namespace) -> None:
    """Inspect a profile and optionally validate it against the schema."""
    from pydantic import ValidationError

    from pypi_profile.loader import find_profile, load_profile

    source_arg = getattr(args, "source", None) or getattr(args, "path", "")
    if not source_arg:
        source_arg = require_value(args, "source", label="Profile source")
    source = str(source_arg)
    no_validate: bool = getattr(args, "no_validate", False)

    try:
        toml_path = find_profile(source)
    except FileNotFoundError as exc:
        logger.error("Profile not found: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    if is_dry_run(args):
        print_dry_run(
            "inspect would read the resolved profile without executing plugin code.",
            [
                f"profile={toml_path}",
                f"validate={not no_validate}",
            ],
        )
        return

    try:
        profile = load_profile(toml_path, autopatch_public_key=False)
    except ValidationError as exc:
        if no_validate:
            logger.debug(
                "Schema validation failed (ignored due to --no-validate): %s", exc
            )
            print(
                "WARNING: schema errors present (run without --no-validate to see them)"
            )
            # Load raw TOML for partial display
            from pypi_profile.serialization import TOMLDecodeError, toml_load_path

            try:
                raw = toml_load_path(toml_path)
                print(f"Profile file: {toml_path}")
                print(
                    f"Principal:    {raw.get('profile', {}).get('display_name', '?')!r}"
                )
            except (OSError, TOMLDecodeError) as raw_exc:
                logger.debug(
                    "Could not read raw TOML for inspect fallback: %s", raw_exc
                )
            return
        logger.error("Profile validation failed: %s", exc)
        raise_invalid_profile(toml_path, exc.errors())
    except FileNotFoundError as exc:
        logger.error("Profile file not found: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    if wants_json_output(args):
        emit_json(
            {
                "profile_file": str(toml_path),
                "principal": profile.profile.display_name,
                "kind": profile.profile.kind,
                "pypi_username": profile.identity.pypi_username,
                "counts": {
                    "packages": len(profile.packages),
                    "projects": len(profile.projects),
                    "humans": len(profile.humans),
                    "profiles": len(profile.profiles),
                },
                "verification": {
                    "public_key_present": bool(profile.verification.public_key),
                    "preferred_signature_backend": profile.verification.preferred_signature_backend,
                    "signing_key": key_status(),
                },
                "schema_ok": not no_validate,
            }
        )
        return

    print(f"Profile file: {toml_path}")
    print(f"Principal:    {profile.profile.display_name!r} ({profile.profile.kind})")
    print(f"PyPI user:    {profile.identity.pypi_username}")
    print(f"Packages:     {len(profile.packages)}")
    print(f"Projects:     {len(profile.projects)}")
    print(f"Humans:       {len(profile.humans)}")
    print(f"Profiles:     {len(profile.profiles)}")
    print(f"Public key:   {'yes' if profile.verification.public_key else 'no'}")
    print(f"Sig backend:  {profile.verification.preferred_signature_backend}")
    print(f"Signing key:  {key_status()}")

    if not no_validate:
        print("Schema:       OK")


def cmd_doctor(args: argparse.Namespace) -> None:
    """Diagnose local configuration and profile health."""
    if is_dry_run(args):
        print_dry_run(
            "doctor would inspect config files, signing keys, and bundled resources.",
            [
                "checks=config file, public key, signing key, bundled templates/static assets, optional deps"
            ],
        )
        return

    ok = True
    findings: list[dict[str, str]] = []
    json_mode = wants_json_output(args)

    def report(status: str, label: str, detail: str = "") -> None:
        suffix = f" — {detail}" if detail else ""
        findings.append({"status": status, "label": label, "detail": detail})
        if not json_mode:
            print(f"  {status}  {label}{suffix}")

    def ok_check(label: str, detail: str = "") -> None:
        report("OK", label, detail)

    def warn_check(label: str, detail: str = "") -> None:
        nonlocal ok
        report("!!", label, detail)
        ok = False

    def info_check(label: str, detail: str = "") -> None:
        report("--", label, detail)

    if not json_mode:
        print("pypi-profile doctor")
        print(f"  version: {__version__}")
        print(f"  python:  {sys.version}")
        print()

    # --- Config file ---
    if not json_mode:
        print("Configuration:")
    from pypi_profile.finder import find_profile_files

    found_configs = find_profile_files()
    if found_configs:
        for p in found_configs:
            ok_check("profile config", str(p))
        if len(found_configs) > 1:
            info_check(
                "multiple configs found", "only the first will be used by most commands"
            )
    else:
        info_check(
            "no pypi_profile.toml found in current directory", "run: pypi-profile init"
        )
    if not json_mode:
        print()

    # --- Public key in TOML ---
    if not json_mode:
        print("Public key (in TOML):")
    toml_path = Path("pypi_profile.toml")
    if toml_path.exists():
        from pydantic import ValidationError

        try:
            from pypi_profile.loader import load_profile

            profile = load_profile(toml_path, autopatch_public_key=False)
            if profile.verification.public_key:
                ok_check("public_key present in [verification]")
            else:
                info_check(
                    "public_key missing from [verification]", "run: pypi-profile keygen"
                )
        except (OSError, ValidationError, ValueError):
            info_check("could not parse pypi_profile.toml to check public key")
    else:
        info_check("no pypi_profile.toml to check")
    if not json_mode:
        print()

    # --- Signing key ---
    if not json_mode:
        print("Signing key:")
    from pypi_profile.signing import (
        DEFAULT_KEY_DIR,
        DEFAULT_SK_NAME,
        keyring_is_usable,
        keyring_username,
        load_key_bytes_from_keyring,
    )

    if keyring_is_usable():
        import keyring as kr

        backend_name = type(kr.get_keyring()).__name__
        ok_check(f"keyring backend: {backend_name}", f"username={keyring_username()!r}")
        if load_key_bytes_from_keyring() is not None:
            ok_check("secret key found in keyring")
        else:
            info_check("no secret key in keyring", "run: pypi-profile keygen")
    else:
        info_check("no usable keyring backend; falling back to disk")
        sk_path = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
        if sk_path.exists():
            ok_check("secret key on disk", str(sk_path))
        else:
            info_check(f"no secret key at {sk_path}", "run: pypi-profile keygen")
    if not json_mode:
        print()

    # --- Bundled resources ---
    if not json_mode:
        print("Bundled resources:")
    from pypi_profile.ds.paths import static_root_path, template_root_path

    tmpl_dir = template_root_path()
    static_dir = static_root_path()
    if tmpl_dir.is_dir() and any(tmpl_dir.rglob("*.html")):
        ok_check("templates", str(tmpl_dir))
    else:
        warn_check("templates missing or empty", str(tmpl_dir))

    css_file = static_dir / "css" / "pypi_ds.css"
    if css_file.exists():
        ok_check("static assets (CSS)", str(css_file))
    else:
        warn_check("pypi_ds.css missing", str(css_file))

    favicon = static_dir / "images" / "favicon.ico"
    if favicon.exists():
        ok_check("static assets (favicon)", str(favicon))
    else:
        warn_check("favicon.ico missing", str(favicon))
    if not json_mode:
        print()

    # --- Optional deps ---
    if not json_mode:
        print("Optional dependencies:")
    from importlib import util

    if util.find_spec("yaml") is not None:
        ok_check("pyyaml (FUNDING.yml support)")
    else:
        info_check("pyyaml not installed", "needed for FUNDING.yml import")
    if util.find_spec("orjson") is not None:
        ok_check("orjson (faster JSON parsing)")
    else:
        info_check(
            "orjson not installed",
            "install with pypi-profile[fast] for faster JSON work",
        )
    if util.find_spec("rtoml") is not None:
        ok_check("rtoml (faster TOML parsing)")
    else:
        info_check(
            "rtoml not installed",
            "install with pypi-profile[fast] for faster TOML work",
        )
    if not json_mode:
        print()

    summary = "All required checks passed." if ok else "Some required checks failed."
    if wants_json_output(args):
        emit_json(
            {"ok": ok, "version": __version__, "checks": findings, "summary": summary}
        )
        return
    print(summary)
    if not ok:
        raise CliError(summary, EXIT_IO)


def cmd_fetch(args: argparse.Namespace) -> None:
    """Fetch live metadata from PyPI, GitHub, GitLab, and Mastodon."""
    from pypi_profile.loader import find_profile, load_profile

    if not getattr(args, "source", ""):
        args.source = require_value(args, "source", label="Profile source")
    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        logger.error("Profile not found: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    profile = load_profile(toml_path, autopatch_public_key=not is_dry_run(args))
    if is_dry_run(args):
        print_dry_run(
            "fetch would request live metadata from external services.",
            [
                f"profile={toml_path}",
                f"principal={profile.profile.display_name!r}",
                f"profiles={len(profile.profiles)}",
                f"json_output={args.json}",
            ],
        )
        return

    from pypi_profile.fetcher import compare_packages, fetch_all

    if not wants_json_output(args):
        print(f"Fetching live data for: {profile.profile.display_name!r}")
        print()

    live = fetch_all(
        profile, verbose=True, include_owned=getattr(args, "include_owned", False)
    )
    report = compare_packages(profile, live)

    if wants_json_output(args):
        emit_json(
            {
                **live,
                "profile_file": str(toml_path),
                "profile_name": profile.profile.display_name,
                "package_comparison": report,
            }
        )
        return

    print()
    print("=== PyPI Package Comparison ===")
    for item in report:
        status_icon = {
            "confirmed": "✅",
            "not_found": "❌",
            "no_data": "❓",
            "unverified": "❓",
        }.get(item["status"], "❓")
        print(
            f"  {status_icon} {item['name']!r} (asserted: {item['asserted_role']}) — {item['note']}"
        )
        if item.get("pypi_version"):
            print(
                f"      latest version: {item['pypi_version']}  {item.get('pypi_summary', '')[:80]}"
            )

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

    build_idents = live.get("build_identities") or []
    if build_idents:
        print()
        print("=== Build identities (PyPI Trusted Publishers) ===")
        for ident in build_idents:
            label = (
                f"{ident.get('kind', '')}:{ident.get('repository', '') or '(unknown)'}"
            )
            extras = []
            if ident.get("workflow"):
                extras.append(f"workflow={ident['workflow']}")
            if ident.get("environment"):
                extras.append(f"env={ident['environment']}")
            suffix = f"  ({', '.join(extras)})" if extras else ""
            print(f"  {label}{suffix}")
            pkgs = ident.get("packages") or []
            print(
                f"      {ident.get('file_count', 0)} file(s) across {len(pkgs)} package(s): {', '.join(pkgs)}"
            )
            if ident.get("identity_url"):
                print(f"      {ident['identity_url']}")


def cmd_keygen(args: argparse.Namespace) -> None:
    """Generate a minisign keypair for signing profile claims."""
    import os

    from pypi_profile.signing import DEFAULT_KEY_DIR, DEFAULT_PK_NAME, DEFAULT_SK_NAME

    args.key_dir = maybe_prompt_path(args, "key_dir", label="Key directory", default="")
    args.password = maybe_prompt_value(
        args, "password", label="Key password", default="", secret=True
    )
    args.keyring_identity = maybe_prompt_value(
        args, "keyring_identity", label="Keyring identity", default=""
    )
    args.no_keyring = maybe_prompt_bool(
        args, "no_keyring", label="Store only on disk", default=False
    )
    args.force = maybe_prompt_bool(
        args, "force", label="Overwrite existing keys", default=False
    )

    env_key_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
    if args.key_dir:
        key_dir = Path(args.key_dir).expanduser()
    elif env_key_path:
        key_dir = Path(env_key_path).expanduser().parent
    else:
        key_dir = None
    password = args.password or os.environ.get("PYPI_PROFILE_KEY_PASSWORD", "")

    keyring_identity_arg = getattr(args, "keyring_identity", "")
    # Default keyring identity to the PyPI username from any local profile TOML,
    # so each account's key is stored separately without explicit --keyring-identity.
    if not keyring_identity_arg:
        toml_path_check = Path("pypi_profile.toml")
        if toml_path_check.exists():
            from pypi_profile.serialization import TOMLDecodeError, toml_load_path

            try:
                data = toml_load_path(toml_path_check)
                identity = data.get("identity", {})
                if isinstance(identity, dict):
                    username = identity.get("pypi_username", "")
                    if isinstance(username, str):
                        keyring_identity_arg = username
            except (OSError, TOMLDecodeError) as exc:
                logger.debug(
                    "Could not derive keyring identity from local TOML: %s", exc
                )
    keyring_identity: str | None = keyring_identity_arg or None
    store_in_keyring: bool = not getattr(args, "no_keyring", False)

    effective_key_dir = key_dir or DEFAULT_KEY_DIR
    sk_path = effective_key_dir / DEFAULT_SK_NAME
    pk_path = effective_key_dir / DEFAULT_PK_NAME

    if is_dry_run(args):
        details = [
            f"secret_key={sk_path}",
            f"public_key={pk_path}",
            f"store_in_keyring={store_in_keyring}",
            f"keyring_identity={keyring_identity or '(pypi username or default)'}",
            f"force={args.force}",
        ]
        if Path("pypi_profile.toml").exists():
            details.append(
                "would also patch pypi_profile.toml with the generated public key if needed"
            )
        print_dry_run("keygen would generate a minisign keypair.", details)
        return

    from pypi_profile.signing import (
        generate_keypair,
        keyring_is_usable,
        keyring_username,
    )

    if store_in_keyring and not keyring_is_usable():
        print(
            "Note: no usable keyring backend found — secret key will be stored on disk only.\n"
            "      Install a keyring backend (e.g. 'pip install keyring') to enable keyring storage.",
            file=sys.stderr,
        )
        store_in_keyring = False

    try:
        sk_path, pk_path, pub_b64 = generate_keypair(
            key_dir=key_dir,
            password=password,
            force=args.force,
            keyring_identity=keyring_identity,
            store_in_keyring=store_in_keyring,
        )
    except FileExistsError as exc:
        logger.error("Key already exists: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc
    except ImportError as exc:
        logger.error("Missing dependency for keygen: %s", exc)
        raise CliError(str(exc), EXIT_IO) from exc

    print(f"Secret key: {sk_path}")
    print(f"Public key: {pk_path}")

    if store_in_keyring and keyring_is_usable():
        username = keyring_username(keyring_identity)
        print(
            f"Key storage: system keyring (service='pypi-profile', username={username!r})"
        )
        print(f"  Disk copy also kept at {sk_path} as a fallback.")
        if not keyring_identity:
            print(
                "  Tip: use --keyring-identity to give this key a name (e.g. 'work' or 'personal')\n"
                "  so you can store multiple keys for different PyPI accounts."
            )
    else:
        print(f"Key storage: disk only ({sk_path})")
        print(
            "  Tip: use a keyring backend to avoid keeping the secret key as a plaintext file."
        )
    print()

    # Auto-patch public_key into any pypi_profile.toml found in the cwd.
    toml_path = Path("pypi_profile.toml")
    if toml_path.exists():
        text = toml_path.read_text(encoding="utf-8")
        import re

        patched = re.sub(
            r'(?m)^(public_key\s*=\s*)""',
            f'public_key = "{pub_b64}"',
            text,
        )
        if patched != text:
            toml_path.write_text(patched, encoding="utf-8")
            print(f"Updated {toml_path} with public key.")
        else:
            print(f"Add this public key to {toml_path} [verification] section:")
            print(f'public_key = "{pub_b64}"')
    else:
        print("Add this public key to pypi_profile.toml [verification] section:")
        print(f'public_key = "{pub_b64}"')

    print()
    print("Keep your secret key private. Never commit it to version control.")


def cmd_sign(args: argparse.Namespace) -> None:
    """Sign a controls-url claim and print the proof string."""
    import os

    from pypi_profile.loader import find_profile, load_profile

    args.claim_type = getattr(args, "claim_type", "") or "controls-url"
    args.source = require_value(args, "source", label="Profile source")
    args.url = require_value(args, "url", label="Controlled URL")
    args.key = maybe_prompt_path(args, "key", label="Secret key path", default="")
    args.password = maybe_prompt_value(
        args, "password", label="Key password", default="", secret=True
    )
    args.profile_package = maybe_prompt_value(
        args, "profile_package", label="Profile package override", default=""
    )
    if (
        getattr(args, "format", None) is None
        and not getattr(args, "compact", False)
        and wants_interactive(args)
    ):
        args.format = prompt_text(
            "Token format",
            default="full",
            choices=["full", "compact", "tiny", "fingerprint"],
        )

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        logger.error("Profile not found: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    profile = load_profile(toml_path, autopatch_public_key=not is_dry_run(args))
    profile_package = profile.identity.pypi_username or "unknown"
    pypi_username = profile.identity.pypi_username

    sk_path = Path(args.key).expanduser() if args.key else None
    password = args.password or os.environ.get("PYPI_PROFILE_KEY_PASSWORD", "")

    resolved_profile_package = args.profile_package or f"pypi-profile-{profile_package}"
    # Resolve --format / --compact precedence: explicit --format wins; else fall back to --compact alias.
    chosen_format = args.format or ("compact" if args.compact else "full")
    if is_dry_run(args):
        print_dry_run(
            "sign would generate a proof-of-control token.",
            [
                f"profile={toml_path}",
                f"profile_package={resolved_profile_package}",
                f"pypi_username={pypi_username}",
                f"url={args.url}",
                f"key={sk_path or '(default key path)'}",
                f"format={chosen_format}",
                f"password_supplied={bool(password)}",
            ],
        )
        return

    from pypi_profile.signing import sign_controls_url

    try:
        proof = sign_controls_url(
            profile_package=resolved_profile_package,
            pypi_username=pypi_username,
            subject_url=args.url,
            sk_path=sk_path,
            password=password,
            format=chosen_format,
        )
    except FileNotFoundError as exc:
        logger.error("Secret key not found: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc
    except ImportError as exc:
        logger.error("Missing dependency for signing: %s", exc)
        raise CliError(str(exc), EXIT_IO) from exc

    if wants_json_output(args):
        emit_json(
            {
                "claim_type": args.claim_type,
                "profile_file": str(toml_path),
                "profile_package": resolved_profile_package,
                "pypi_username": pypi_username,
                "url": args.url,
                "format": chosen_format,
                "proof": proof,
            }
        )
        return

    print("Copy and paste the following proof string into your external profile page:")
    print()
    print(proof)
    print(f"\n({len(proof)} chars — {chosen_format} format)")
    if chosen_format == "tiny" and len(proof) + len(pypi_username) + 1 > 100:
        print(
            f"WARNING: '{pypi_username}' + space + token = {len(proof) + len(pypi_username) + 1} chars; "
            "PyPI display-name fields cap at ~100 chars. Place the token in a field with more room, "
            "or shorten the surrounding text.",
            file=sys.stderr,
        )
    print()
    print(f"Place it at: {args.url}")


def cmd_verify(args: argparse.Namespace) -> None:
    """Verify proof-of-control claims for all listed [[profiles]] entries."""
    from pypi_profile.loader import find_profile, load_profile

    args.source = require_value(args, "source", label="Profile source")
    args.profile_package = maybe_prompt_value(
        args, "profile_package", label="Profile package override", default=""
    )

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        logger.error("Profile not found: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    profile = load_profile(toml_path, autopatch_public_key=not is_dry_run(args))
    profile_package = (
        args.profile_package or f"pypi-profile-{profile.identity.pypi_username}"
    )

    if is_dry_run(args):
        print_dry_run(
            "verify would fetch external pages and validate proof-of-control claims.",
            [
                f"profile={toml_path}",
                f"profile_package={profile_package}",
                f"profiles={len(profile.profiles)}",
                f"public_key_present={bool(profile.verification.public_key)}",
            ],
        )
        return

    # If the toml has no public key, try loading it from disk.
    if not profile.verification.public_key:
        from pypi_profile.signing import read_public_key_b64

        pub_b64 = read_public_key_b64()
        if pub_b64:
            profile.verification.public_key = pub_b64
            logger.info("Loaded public key from disk")
            print("Loaded public key from disk.")
        else:
            logger.warning("No public key in [verification] and none found on disk")
            print(
                "⚠️  No public key in [verification] and none found on disk. Verification requires a public key.",
                file=sys.stderr,
            )

    from pypi_profile.verifier import diagnose_all_profiles

    try:
        results = diagnose_all_profiles(profile, profile_package=profile_package)
    except ImportError as exc:
        logger.error("Missing dependency for verification: %s", exc)
        raise CliError(str(exc), EXIT_IO) from exc

    verified = sum(1 for r in results if r["status"] == "verified")
    if wants_json_output(args):
        emit_json(
            {
                "profile_file": str(toml_path),
                "profile_name": profile.profile.display_name,
                "profile_package": profile_package,
                "verified": verified,
                "total": len(results),
                "results": results,
            }
        )
        return

    status_icons = {
        "verified": "✅",
        "unverified": "❓",
        "invalid": "❌",
        "expired": "⚠️",
        "self_asserted": "🔵",
        "unknown": "❓",
    }

    print(f"Verifying claims for: {profile.profile.display_name!r}")
    print()
    for item in results:
        icon = status_icons.get(item["status"], "❓")
        print(f"  {icon} {item['label']} ({item['url']}) — {item['status']}")
        if item["status"] not in ("verified", "self_asserted"):
            for step in item.get("detail", []):
                print(f"      {step}")

    print()
    print(f"{verified}/{len(results)} claims verified.")


def cmd_api_dump(args: argparse.Namespace) -> None:
    """Dump profile data as JSON (for debugging/inspection)."""
    from pypi_profile.loader import find_profile, load_profile

    args.source = require_value(args, "source", label="Profile source")
    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        raise CliError(str(exc), EXIT_USAGE) from exc
    profile = load_profile(toml_path, autopatch_public_key=not is_dry_run(args))
    if is_dry_run(args):
        print_dry_run(
            "dump would serialize the profile model as JSON.",
            [
                f"profile={toml_path}",
                f"principal={profile.profile.display_name!r}",
            ],
        )
        return
    print(_json_dumps(profile.model_dump(), indent=2, default=str))


def cmd_find_profiles(args: argparse.Namespace) -> None:
    """Scan for pypi_profile.toml files and pyproject.toml with [tool.pypi-profile]."""
    from pypi_profile.finder import find_profile_files

    args.root = maybe_prompt_path(
        args, "root", label="Root directory to scan", default=""
    )
    root = Path(args.root).expanduser().resolve() if args.root else None
    found = find_profile_files(root=root)
    if is_dry_run(args):
        print_dry_run(
            "find-profiles would scan for profile configuration files.",
            [
                f"root={root or Path.cwd()}",
                f"matches={len(found)}",
            ],
        )
        return
    if not found:
        if wants_json_output(args):
            emit_json({"root": str(root or Path.cwd()), "matches": []})
            return
        print("No profile files found.")
        return
    if wants_json_output(args):
        emit_json(
            {"root": str(root or Path.cwd()), "matches": [str(path) for path in found]}
        )
        return
    for p in found:
        print(p)


def cmd_generate_missing(args: argparse.Namespace) -> None:
    """Generate starter profiles for discovered PyPI usernames across a venv."""
    from pypi_profile.finder import find_profile_files
    from pypi_profile.importers import merge_skip_trace_exports
    from pypi_profile.loader import load_profile
    from pypi_profile.skip_trace_bridge import (
        collect_skip_trace_exports,
        group_exports_by_username,
        list_installed_package_names,
    )

    output_dir = Path(args.output_dir).expanduser().resolve()
    target = Path(args.venv).expanduser().resolve() if args.venv else None
    packages = list_installed_package_names(target)
    if args.limit:
        packages = packages[: args.limit]

    existing_usernames: set[str] = set()
    if output_dir.exists():
        for path in find_profile_files(root=output_dir):
            try:
                profile = load_profile(path, autopatch_public_key=False)
            except (OSError, ValueError):
                continue
            if profile.identity.pypi_username:
                existing_usernames.add(profile.identity.pypi_username)

    if is_dry_run(args):
        print_dry_run(
            "generate-missing would analyze installed packages with skip_trace and write starter profiles.",
            [
                f"venv={target or '(current environment)'}",
                f"output_dir={output_dir}",
                f"packages_to_analyze={len(packages)}",
                f"existing_profiles={len(existing_usernames)}",
                f"force={args.force}",
            ],
        )
        return

    exports, failures = collect_skip_trace_exports(packages)
    grouped = group_exports_by_username(exports)
    created: list[str] = []
    skipped: list[str] = []
    for username, grouped_exports in sorted(grouped.items()):
        dest = output_dir / username / "pypi_profile.toml"
        if (username in existing_usernames or dest.exists()) and not args.force:
            skipped.append(username)
            continue
        profile_data = merge_skip_trace_exports(grouped_exports)
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_toml_from_data(
            dest,
            profile_data,
            username=profile_data.get("identity", {}).get("pypi_username", username),
            kind=profile_data.get("profile", {}).get("kind", "individual"),
        )
        created.append(str(dest))

    summary = {
        "venv": str(target) if target else "",
        "output_dir": str(output_dir),
        "packages_analyzed": len(packages),
        "exports_with_usernames": len(grouped),
        "created": created,
        "skipped": skipped,
        "failures": failures,
    }
    if wants_json_output(args):
        emit_json(summary)
        return
    print(f"Analyzed {len(packages)} installed packages.")
    print(f"Created {len(created)} profile file(s).")
    if skipped:
        print(f"Skipped {len(skipped)} existing profile(s).")
    if failures:
        print(f"Failed to analyze {len(failures)} package(s).")


def cmd_update_proofs(args: argparse.Namespace) -> None:
    """Sign all [[profiles]] URLs and write stored_proof values into the TOML."""
    import os

    from pypi_profile.loader import find_profile, load_profile

    args.source = require_value(args, "source", label="Profile source")
    args.key = maybe_prompt_path(args, "key", label="Secret key path", default="")
    args.password = maybe_prompt_value(
        args, "password", label="Key password", default="", secret=True
    )
    args.profile_package = maybe_prompt_value(
        args, "profile_package", label="Profile package override", default=""
    )
    args.force = maybe_prompt_bool(
        args, "force", label="Re-sign existing stored proofs", default=False
    )

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        logger.error("Profile not found: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    profile = load_profile(toml_path, autopatch_public_key=not is_dry_run(args))
    pypi_username = profile.identity.pypi_username
    profile_package = args.profile_package or f"pypi-profile-{pypi_username}"

    sk_path = Path(args.key).expanduser() if args.key else None
    password = args.password or os.environ.get("PYPI_PROFILE_KEY_PASSWORD", "")

    if is_dry_run(args):
        pending = len(
            [link for link in profile.profiles if args.force or not link.stored_proof]
        )
        print_dry_run(
            "update-proofs would sign profile URLs and write stored_proof values.",
            [
                f"profile={toml_path}",
                f"profile_package={profile_package}",
                f"candidate_urls={pending}",
                f"force={args.force}",
                f"key={sk_path or '(default key path)'}",
                f"password_supplied={bool(password)}",
            ],
        )
        return

    from pypi_profile.signing import patch_proofs_in_toml

    try:
        updated = patch_proofs_in_toml(
            toml_path=toml_path,
            profile_package=profile_package,
            pypi_username=pypi_username,
            sk_path=sk_path,
            password=password or None,
            force=args.force,
        )
    except ImportError as exc:
        logger.error("Missing dependency for signing: %s", exc)
        raise CliError(str(exc), EXIT_IO) from exc

    if wants_json_output(args):
        emit_json(
            {
                "profile_file": str(toml_path),
                "profile_package": profile_package,
                "updated_urls": updated,
                "updated_count": len(updated),
            }
        )
        return

    if updated:
        print(f"Updated stored_proof for {len(updated)} URL(s) in {toml_path}:")
        for url in updated:
            print(f"  {url}")
        print()
        print(
            "Commit the updated TOML so the static build can use these proofs without the private key."
        )
    else:
        print(
            "No URLs needed updating (all already have stored_proof, or no key found)."
        )


def cmd_key_info(args: argparse.Namespace) -> None:
    """Print information about the active signing key without modifying anything."""
    from pypi_profile.key_management import key_info

    sk_path = Path(args.key).expanduser() if getattr(args, "key", "") else None

    if is_dry_run(args):
        print_dry_run(
            "key-info would display signing key details.",
            [f"key={sk_path or '(default)'}"],
        )
        return

    info = key_info(sk_path=sk_path)

    if info.get("not_found"):
        if wants_json_output(args):
            emit_json(info)
            return
        print("No signing key found.")
        print(f"  ({info.get('source', 'unknown location')})")
        print()
        print("Run  pypi-profile keygen  to generate one.")
        return

    if info.get("error"):
        raise CliError(f"Key found but unreadable: {info['error']}", EXIT_IO)

    if wants_json_output(args):
        emit_json(info)
        return

    pub = info.get("public_key", "")
    pub_display = (pub[:20] + "…") if len(pub) > 20 else pub

    print("Signing key info")
    print(f"  source:      {info['source']}")
    print(f"  key ID:      {info.get('key_id', 'unknown')}")
    print(f"  generated:   {info.get('generated', 'unknown')}")
    print(f"  public key:  {pub_display}")
    print()
    print("Profile binding")
    print(f"  {info.get('profile_binding', 'no profile found')}")


def cmd_key_list(args: argparse.Namespace) -> None:
    """List all known signing keys across the keyring and disk."""
    from pypi_profile.key_management import key_list

    if is_dry_run(args):
        print_dry_run("key-list would enumerate all known signing keys.")
        return

    entries = key_list()

    if not entries:
        if wants_json_output(args):
            emit_json([])
            return
        print("No signing keys found.")
        return

    if wants_json_output(args):
        emit_json(entries)
        return

    col_w = 44
    print(f"{'Identity / path':<{col_w}}  {'Key ID':<16}  {'Source'}")
    print("-" * (col_w + 32))
    for e in entries:
        label = e["identity_or_path"]
        if len(label) > col_w:
            label = "…" + label[-(col_w - 1) :]
        kid = e.get("key_id", "—")
        source = e.get("source", "")
        binding = e.get("binding", "")
        suffix = f"  ({binding})" if binding else ""
        print(f"{label:<{col_w}}  {kid:<16}  {source}{suffix}")


def cmd_key_rotate(args: argparse.Namespace) -> None:
    """Replace the active signing key and re-sign all profile proofs."""
    import os

    from pypi_profile.key_management import key_rotate
    from pypi_profile.loader import find_profile, load_profile

    args.source = require_value(args, "source", label="Profile source")
    args.key_dir = maybe_prompt_path(
        args, "key_dir", label="New key directory", default=""
    )
    args.keyring_identity = maybe_prompt_value(
        args, "keyring_identity", label="New keyring identity", default=""
    )
    args.password = maybe_prompt_value(
        args, "password", label="New key password", default="", secret=True
    )
    args.profile_package = maybe_prompt_value(
        args, "profile_package", label="Profile package override", default=""
    )
    args.no_keep_old = maybe_prompt_bool(
        args, "no_keep_old", label="Skip archiving the old key", default=False
    )

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        logger.error("Profile not found: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    profile = load_profile(toml_path, autopatch_public_key=False)
    pypi_username = profile.identity.pypi_username
    profile_package = args.profile_package or f"pypi-profile-{pypi_username}"
    key_dir = Path(args.key_dir).expanduser() if getattr(args, "key_dir", "") else None
    keyring_identity = getattr(args, "keyring_identity", "") or None
    password = (
        getattr(args, "password", "")
        or os.environ.get("PYPI_PROFILE_KEY_PASSWORD", "")
        or None
    )

    if is_dry_run(args):
        print_dry_run(
            "key-rotate would generate a new keypair, update TOML, and re-sign all proofs.",
            [
                f"profile={toml_path}",
                f"profile_package={profile_package}",
                f"key_dir={key_dir or '(default ~/.pypi_profile/)'}",
                f"keyring_identity={keyring_identity or '(default)'}",
                f"no_keep_old={getattr(args, 'no_keep_old', False)}",
            ],
        )
        return

    if not getattr(args, "force", False) and not prompt_bool(
        "Rotate the key and re-sign all profile proofs?", default=False
    ):
        print("Aborted.")
        return

    try:
        result = key_rotate(
            toml_path=toml_path,
            profile_package=profile_package,
            pypi_username=pypi_username,
            key_dir=key_dir,
            keyring_identity=keyring_identity,
            password=password,
            no_keep_old=getattr(args, "no_keep_old", False),
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        logger.error("key-rotate failed: %s", exc)
        raise CliError(str(exc), EXIT_IO) from exc

    if wants_json_output(args):
        emit_json(result)
        return

    print(f"Old key ID:  {result['old_key_id']}")
    print(f"New key ID:  {result['new_key_id']}")
    if result.get("archived_path"):
        print(f"Old key archived to: {result['archived_path']}")
    if result.get("updated_urls"):
        print(f"\nRe-signed {len(result['updated_urls'])} URL(s):")
        for url in result["updated_urls"]:
            print(f"  {url}")
    print()
    print("NOTE: stored_proof values published on external pages before this rotation")
    print(
        "      will appear invalid until those pages are updated with the new proof strings."
    )
    print("Commit the updated TOML to source control.")


def cmd_key_recover(args: argparse.Namespace) -> None:
    """Guide the user through recovery when the secret key is lost."""
    import os

    from pypi_profile.key_management import key_recover
    from pypi_profile.loader import find_profile, load_profile

    args.source = require_value(args, "source", label="Profile source")
    args.key_dir = maybe_prompt_path(
        args, "key_dir", label="New key directory", default=""
    )
    args.keyring_identity = maybe_prompt_value(
        args, "keyring_identity", label="New keyring identity", default=""
    )
    args.password = maybe_prompt_value(
        args, "password", label="New key password", default="", secret=True
    )
    args.profile_package = maybe_prompt_value(
        args, "profile_package", label="Profile package override", default=""
    )

    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        logger.error("Profile not found: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    profile = load_profile(toml_path, autopatch_public_key=False)
    pypi_username = profile.identity.pypi_username
    profile_package = args.profile_package or f"pypi-profile-{pypi_username}"
    key_dir = Path(args.key_dir).expanduser() if getattr(args, "key_dir", "") else None
    keyring_identity = getattr(args, "keyring_identity", "") or None
    password = (
        getattr(args, "password", "")
        or os.environ.get("PYPI_PROFILE_KEY_PASSWORD", "")
        or None
    )

    if is_dry_run(args):
        print_dry_run(
            "key-recover would diagnose missing key and guide through recovery.",
            [
                f"profile={toml_path}",
                f"profile_package={profile_package}",
            ],
        )
        return

    try:
        result = key_recover(
            toml_path=toml_path,
            profile_package=profile_package,
            pypi_username=pypi_username,
            key_dir=key_dir,
            keyring_identity=keyring_identity,
            password=password,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        logger.error("key-recover failed: %s", exc)
        raise CliError(str(exc), EXIT_IO) from exc

    if wants_json_output(args):
        emit_json(result)
        return

    if result.get("key_was_present"):
        print("Key is present — no recovery needed.")
        print(result.get("message", ""))
        print("Use  pypi-profile key-rotate  to replace it.")
        return

    print(f"New key ID:      {result.get('new_key_id', 'unknown')}")
    print(f"New public key:  {result.get('new_public_key', '')[:20]}…")
    if result.get("updated_urls"):
        print(f"\nRe-signed {len(result['updated_urls'])} URL(s):")
        for url in result["updated_urls"]:
            print(f"  {url}")
    if result.get("urls_needing_update"):
        print()
        print("The following URLs had stored proofs from the lost key.")
        print("Update those external pages with the new proof strings:")
        for url in result["urls_needing_update"]:
            print(f"  {url}")
    print()
    print("Commit the updated TOML to source control and push it.")


def cmd_key_export(args: argparse.Namespace) -> None:
    """Export the raw secret key to a file for secure transfer."""
    from pypi_profile.key_management import key_export

    args.key = maybe_prompt_path(args, "key", label="Secret key path", default="")
    if is_dry_run(args):
        args.output = maybe_prompt_path(args, "output", label="Export file", default="")
    else:
        args.output = require_value(args, "output", label="Export file")
    sk_path = Path(args.key).expanduser() if getattr(args, "key", "") else None
    output_path = (
        Path(args.output).expanduser() if getattr(args, "output", "") else None
    )

    if is_dry_run(args):
        print_dry_run(
            "key-export would write the secret key to a file.",
            [
                f"key={sk_path or '(default)'}",
                f"output={output_path or '(stdout — not allowed without --dry-run)'}",
            ],
        )
        return

    try:
        result = key_export(output_path=output_path, sk_path=sk_path)
    except FileNotFoundError as exc:
        logger.error("key-export: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    if wants_json_output(args):
        emit_json(result)
        return

    print(f"Exported key ID {result['key_id']} to {result['written_to']}")
    print()
    print(f"WARNING: {result['warning']}")


def cmd_key_import(args: argparse.Namespace) -> None:
    """Install a previously exported key file into the keyring and/or disk."""
    from pypi_profile.key_management import key_import

    args.file = require_value(args, "file", label="Exported key file")
    args.key_dir = maybe_prompt_path(
        args, "key_dir", label="Disk key directory", default=""
    )
    args.keyring_identity = maybe_prompt_value(
        args, "keyring_identity", label="Keyring identity", default=""
    )
    args.no_keyring = maybe_prompt_bool(
        args, "no_keyring", label="Store only on disk", default=False
    )
    args.force = maybe_prompt_bool(
        args, "force", label="Overwrite existing disk key", default=False
    )

    import_path = Path(args.file).expanduser()
    key_dir = Path(args.key_dir).expanduser() if getattr(args, "key_dir", "") else None
    keyring_identity = getattr(args, "keyring_identity", "") or None
    no_keyring: bool = getattr(args, "no_keyring", False)
    force: bool = getattr(args, "force", False)

    if is_dry_run(args):
        print_dry_run(
            "key-import would install a secret key from a file.",
            [
                f"file={import_path}",
                f"key_dir={key_dir or '(default ~/.pypi_profile/)'}",
                f"keyring_identity={keyring_identity or '(default)'}",
                f"no_keyring={no_keyring}",
                f"force={force}",
            ],
        )
        return

    try:
        result = key_import(
            import_path=import_path,
            keyring_identity=keyring_identity,
            key_dir=key_dir,
            no_keyring=no_keyring,
            force=force,
        )
    except (FileNotFoundError, FileExistsError, OSError) as exc:
        logger.error("key-import: %s", exc)
        raise CliError(str(exc), EXIT_IO) from exc

    if wants_json_output(args):
        emit_json(result)
        return

    print(f"Imported key ID: {result['key_id']}")
    print(f"Stored on disk:  {result['disk_path']}")
    if result.get("stored_in_keyring"):
        print(f"Stored in keyring: yes (identity={keyring_identity or 'default'})")
    else:
        print("Stored in keyring: no")


def cmd_build(args: argparse.Namespace) -> None:
    """Generate a static site from a profile."""
    from pypi_profile.loader import find_profile, load_profile

    args.source = require_value(args, "source", label="Profile source")
    args.output = maybe_prompt_value(
        args, "output", label="Output directory", default="dist"
    )
    args.base_url = maybe_prompt_value(
        args, "base_url", label="Base URL prefix", default=""
    )
    args.resume_file = maybe_prompt_path(
        args, "resume_file", label="JSON Resume file", default=""
    )
    output = Path(args.output)
    resume_file = Path(args.resume_file).expanduser() if args.resume_file else None
    try:
        toml_path = find_profile(args.source)
    except FileNotFoundError as exc:
        logger.error("Profile not found for build: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc

    profile = load_profile(toml_path, autopatch_public_key=not is_dry_run(args))
    if resume_file and not resume_file.exists():
        logger.error("Resume file not found for build: %s", resume_file)
        raise CliError(f"Resume file not found: {resume_file}", EXIT_USAGE)

    if is_dry_run(args):
        print_dry_run(
            "build would generate a static site.",
            [
                f"profile={toml_path}",
                f"principal={profile.profile.display_name!r}",
                f"output={output}",
                f"base_url={args.base_url or '(root)'}",
                f"resume_file={resume_file or '(auto-discover)'}",
            ],
        )
        return

    from pypi_profile.builder import build_static_site

    try:
        build_static_site(
            source=args.source,
            output=output,
            resume_file=resume_file,
            base_url=args.base_url,
            verbose=True,
        )
    except FileNotFoundError as exc:
        logger.error("Profile not found for build: %s", exc)
        raise CliError(str(exc), EXIT_USAGE) from exc
    except OSError as exc:
        logger.error("I/O error during build: %s", exc)
        raise CliError(f"ERROR writing output: {exc}", EXIT_IO) from exc


def build_parser() -> argparse.ArgumentParser:
    """Build the pypi-profile argument parser."""
    parser = argparse.ArgumentParser(
        prog="pypi-profile",
        description=(
            "The missing PyPI profile page. Commands can prompt for missing/defaulted values "
            "in an interactive terminal; use --no-interactive for CI and scripts."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        metavar="LEVEL",
        help="Set logging level (default: WARNING). Choices: DEBUG INFO WARNING ERROR CRITICAL",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable DEBUG logging (shorthand for --log-level DEBUG)",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    serve_p = subparsers.add_parser("serve", help="Start the profile web server")
    add_dry_run_argument(serve_p)
    add_interactive_arguments(serve_p)
    serve_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path (omit to list all installed profiles)",
    )
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.add_argument(
        "--allow-code", action="store_true", help="Enable plugin code execution"
    )
    serve_p.set_defaults(func=cmd_serve)

    validate_p = subparsers.add_parser(
        "validate", help="Validate a pypi_profile.toml (alias for inspect)"
    )
    add_dry_run_argument(validate_p)
    add_interactive_arguments(validate_p)
    validate_p.add_argument(
        "path",
        nargs="?",
        default="pypi_profile.toml",
        help="Profile path or package name (also accepted as SOURCE for GUI compatibility)",
    )
    validate_p.set_defaults(func=cmd_validate)

    init_p = subparsers.add_parser("init", help="Create a starter pypi_profile.toml")
    add_dry_run_argument(init_p)
    add_interactive_arguments(init_p)
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
    init_p.add_argument(
        "--output", default="", help="Output path (default: pypi_profile.toml)"
    )
    init_p.add_argument("--force", action="store_true", help="Overwrite existing file")
    init_import_group = init_p.add_mutually_exclusive_group()
    init_import_group.add_argument(
        "--from-json-resume",
        default="",
        metavar="PATH",
        help="Import from a JSON Resume file (resume.json)",
    )
    init_import_group.add_argument(
        "--from-skip-trace",
        default="",
        metavar="PATH",
        help="Import from skip_trace's pypi_profile exchange JSON",
    )
    init_p.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch live data from PyPI, GitHub, GitLab, Mastodon",
    )
    init_p.set_defaults(func=cmd_init)

    inspect_p = subparsers.add_parser(
        "inspect", help="Inspect a profile (and validate schema by default)"
    )
    add_dry_run_argument(inspect_p)
    add_interactive_arguments(inspect_p)
    inspect_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    inspect_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    inspect_p.add_argument(
        "--no-validate",
        action="store_true",
        default=False,
        help="Skip Pydantic schema validation (faster; shows summary even if schema errors exist)",
    )
    inspect_p.set_defaults(func=cmd_inspect)

    doctor_p = subparsers.add_parser("doctor", help="Diagnose local setup")
    add_dry_run_argument(doctor_p)
    add_interactive_arguments(doctor_p)
    doctor_p.add_argument("--json", action="store_true", help="Emit JSON for scripting")
    doctor_p.set_defaults(func=cmd_doctor)

    fetch_p = subparsers.add_parser(
        "fetch-claims",
        help="Fetch live verification claims from PyPI, GitHub, GitLab, Mastodon",
    )
    add_dry_run_argument(fetch_p)
    add_interactive_arguments(fetch_p)
    fetch_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    fetch_p.add_argument("--json", action="store_true", help="Emit JSON for scripting")
    fetch_p.add_argument(
        "--include-owned",
        action="store_true",
        help="Also fetch provenance for packages owned via pypi_username (not just declared ones)",
    )
    fetch_p.set_defaults(func=cmd_fetch)

    fetch_alias_p = subparsers.add_parser(
        "fetch", help="Alias for fetch-claims (deprecated)"
    )
    add_dry_run_argument(fetch_alias_p)
    add_interactive_arguments(fetch_alias_p)
    fetch_alias_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    fetch_alias_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    fetch_alias_p.add_argument(
        "--include-owned",
        action="store_true",
        help="Also fetch provenance for packages owned via pypi_username (not just declared ones)",
    )
    fetch_alias_p.set_defaults(func=cmd_fetch)

    dump_p = subparsers.add_parser("dump", help="Dump profile data as JSON")
    add_dry_run_argument(dump_p)
    add_interactive_arguments(dump_p)
    dump_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    dump_p.set_defaults(func=cmd_api_dump)

    keygen_p = subparsers.add_parser(
        "keygen", help="Generate a minisign keypair for signing claims"
    )
    add_dry_run_argument(keygen_p)
    add_interactive_arguments(keygen_p)
    keygen_p.add_argument(
        "--key-dir",
        default="",
        help="Directory to write key files (default: ~/.pypi_profile/)",
    )
    keygen_p.add_argument(
        "--password",
        default="",
        help="Password to encrypt the secret key (default: none)",
    )
    keygen_p.add_argument(
        "--keyring-identity",
        default="",
        metavar="NAME",
        help=(
            "Name for this key in the system keyring (default: 'default'). "
            "Use distinct names for multiple PyPI identities, e.g. 'work' or 'personal'."
        ),
    )
    keygen_p.add_argument(
        "--no-keyring",
        action="store_true",
        default=False,
        help="Skip storing the secret key in the system keyring; write to disk only.",
    )
    keygen_p.add_argument(
        "--force", action="store_true", help="Overwrite existing key files"
    )
    keygen_p.set_defaults(func=cmd_keygen)

    sign_p = subparsers.add_parser(
        "sign", help="Sign a proof-of-control claim for an external URL"
    )
    add_dry_run_argument(sign_p)
    add_interactive_arguments(sign_p)
    sign_p.add_argument(
        "claim_type",
        nargs="?",
        default="",
        choices=["controls-url"],
        help="Claim type to sign",
    )
    sign_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    sign_p.add_argument("--url", default="", help="URL to assert control over")
    sign_p.add_argument(
        "--key",
        default="",
        help="Path to secret key file (default: ~/.pypi_profile/minisign.key)",
    )
    sign_p.add_argument("--password", default="", help="Password for the secret key")
    sign_p.add_argument(
        "--profile-package", default="", help="Profile package name override"
    )
    sign_p.add_argument(
        "--format",
        choices=["full", "compact", "tiny", "fingerprint"],
        default=None,
        help=(
            "Token format: full (~600 chars), compact (~360 chars, Mastodon-sized), "
            "tiny (~88 chars, sig-only for PyPI display-name slot), or fingerprint "
            "(~35 chars, pointer to a full proof published elsewhere)."
        ),
    )
    sign_p.add_argument(
        "--compact",
        action="store_true",
        default=False,
        help="Deprecated alias for --format compact",
    )
    sign_p.add_argument("--json", action="store_true", help="Emit JSON for scripting")
    sign_p.set_defaults(func=cmd_sign)

    verify_p = subparsers.add_parser(
        "verify", help="Verify proof-of-control claims for declared profile URLs"
    )
    add_dry_run_argument(verify_p)
    add_interactive_arguments(verify_p)
    verify_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    verify_p.add_argument(
        "--profile-package", default="", help="Profile package name override"
    )
    verify_p.add_argument("--json", action="store_true", help="Emit JSON for scripting")
    verify_p.set_defaults(func=cmd_verify)

    update_proofs_p = subparsers.add_parser(
        "update-proofs",
        help="Sign all [[profiles]] URLs and write stored_proof values into the TOML",
    )
    add_dry_run_argument(update_proofs_p)
    add_interactive_arguments(update_proofs_p)
    update_proofs_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    update_proofs_p.add_argument(
        "--key",
        default="",
        help="Path to secret key file (default: ~/.pypi_profile/minisign.key)",
    )
    update_proofs_p.add_argument(
        "--password", default="", help="Password for the secret key"
    )
    update_proofs_p.add_argument(
        "--profile-package", default="", help="Profile package name override"
    )
    update_proofs_p.add_argument(
        "--force",
        action="store_true",
        help="Re-sign even if stored_proof is already present",
    )
    update_proofs_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    update_proofs_p.set_defaults(func=cmd_update_proofs)

    build_p = subparsers.add_parser(
        "build", help="Generate a static site from a profile"
    )
    add_dry_run_argument(build_p)
    add_interactive_arguments(build_p)
    build_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    build_p.add_argument(
        "--output", default="dist", help="Output directory (default: dist/)"
    )
    build_p.add_argument(
        "--base-url",
        default="",
        metavar="URL",
        help="Base URL prefix for asset/nav paths, e.g. /myuser for GitHub Pages subpaths",
    )
    build_p.add_argument(
        "--resume-file",
        default="",
        metavar="PATH",
        help="Path to JSON Resume file (auto-discovered if not given)",
    )
    build_p.set_defaults(func=cmd_build)

    find_profiles_p = subparsers.add_parser(
        "find-profiles",
        help="Scan for pypi_profile.toml files and pyproject.toml with [tool.pypi-profile]",
    )
    add_dry_run_argument(find_profiles_p)
    add_interactive_arguments(find_profiles_p)
    find_profiles_p.add_argument(
        "root",
        nargs="?",
        default="",
        help="Root directory to scan (default: current directory)",
    )
    find_profiles_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    find_profiles_p.set_defaults(func=cmd_find_profiles)

    generate_missing_p = subparsers.add_parser(
        "generate-missing",
        help="Generate starter profiles for missing PyPI identities across a venv",
    )
    add_dry_run_argument(generate_missing_p)
    add_interactive_arguments(generate_missing_p)
    generate_missing_p.add_argument(
        "--venv",
        default="",
        metavar="PATH",
        help="Venv root, python executable, or site-packages path (default: current environment)",
    )
    generate_missing_p.add_argument(
        "--output-dir",
        default="generated-profiles",
        metavar="PATH",
        help="Directory where per-username profile folders will be created",
    )
    generate_missing_p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit how many installed packages to analyze",
    )
    generate_missing_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite generated profiles even when a matching destination exists",
    )
    generate_missing_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    generate_missing_p.set_defaults(func=cmd_generate_missing)

    gui_p = subparsers.add_parser("gui", help="Launch the Tkinter GUI")
    add_dry_run_argument(gui_p)
    add_interactive_arguments(gui_p)
    gui_p.set_defaults(func=cmd_gui)

    key_info_p = subparsers.add_parser(
        "key-info", help="Inspect the active signing key (read-only)"
    )
    add_dry_run_argument(key_info_p)
    add_interactive_arguments(key_info_p)
    key_info_p.add_argument(
        "--key",
        default="",
        metavar="PATH",
        help="Path to secret key file (default: keyring or ~/.pypi_profile/minisign.key)",
    )
    key_info_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    key_info_p.set_defaults(func=cmd_key_info)

    key_list_p = subparsers.add_parser("key-list", help="List all known signing keys")
    add_dry_run_argument(key_list_p)
    add_interactive_arguments(key_list_p)
    key_list_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    key_list_p.set_defaults(func=cmd_key_list)

    key_rotate_p = subparsers.add_parser(
        "key-rotate", help="Replace the active signing key and re-sign all proofs"
    )
    add_dry_run_argument(key_rotate_p)
    add_interactive_arguments(key_rotate_p)
    key_rotate_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    key_rotate_p.add_argument(
        "--key-dir",
        default="",
        metavar="PATH",
        help="Directory for new key files (default: ~/.pypi_profile/)",
    )
    key_rotate_p.add_argument(
        "--keyring-identity",
        default="",
        metavar="NAME",
        help="Keyring identity name for the new key",
    )
    key_rotate_p.add_argument(
        "--password", default="", help="Password for the new secret key"
    )
    key_rotate_p.add_argument(
        "--profile-package", default="", help="Profile package name override"
    )
    key_rotate_p.add_argument(
        "--no-keep-old",
        action="store_true",
        default=False,
        help="Do not archive the old key (default: archive to a .bak file)",
    )
    key_rotate_p.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Skip interactive confirmation prompt",
    )
    key_rotate_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    key_rotate_p.set_defaults(func=cmd_key_rotate)

    key_recover_p = subparsers.add_parser(
        "key-recover", help="Recover from a lost signing key"
    )
    add_dry_run_argument(key_recover_p)
    add_interactive_arguments(key_recover_p)
    key_recover_p.add_argument(
        "source",
        nargs="?",
        default="",
        help="Profile package name, directory, or .toml path",
    )
    key_recover_p.add_argument(
        "--key-dir",
        default="",
        metavar="PATH",
        help="Directory for the new key files (default: ~/.pypi_profile/)",
    )
    key_recover_p.add_argument(
        "--keyring-identity",
        default="",
        metavar="NAME",
        help="Keyring identity name for the new key",
    )
    key_recover_p.add_argument(
        "--password", default="", help="Password for the new secret key"
    )
    key_recover_p.add_argument(
        "--profile-package", default="", help="Profile package name override"
    )
    key_recover_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    key_recover_p.set_defaults(func=cmd_key_recover)

    key_export_p = subparsers.add_parser(
        "key-export", help="Export the secret key to a file for secure transfer"
    )
    add_dry_run_argument(key_export_p)
    add_interactive_arguments(key_export_p)
    key_export_p.add_argument(
        "--key",
        default="",
        metavar="PATH",
        help="Path to secret key file to export (default: keyring or ~/.pypi_profile/minisign.key)",
    )
    key_export_p.add_argument(
        "--output",
        default="",
        metavar="FILE",
        help="Output file path (required unless --dry-run)",
    )
    key_export_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    key_export_p.set_defaults(func=cmd_key_export)

    key_import_p = subparsers.add_parser(
        "key-import", help="Install an exported key file into keyring/disk"
    )
    add_dry_run_argument(key_import_p)
    add_interactive_arguments(key_import_p)
    key_import_p.add_argument(
        "file", nargs="?", default="", help="Path to the exported key file"
    )
    key_import_p.add_argument(
        "--keyring-identity",
        default="",
        metavar="NAME",
        help="Keyring identity name (default: 'default')",
    )
    key_import_p.add_argument(
        "--key-dir",
        default="",
        metavar="PATH",
        help="Directory for the disk copy (default: ~/.pypi_profile/)",
    )
    key_import_p.add_argument(
        "--no-keyring",
        action="store_true",
        default=False,
        help="Store only on disk; skip keyring",
    )
    key_import_p.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing key on disk",
    )
    key_import_p.add_argument(
        "--json", action="store_true", help="Emit JSON for scripting"
    )
    key_import_p.set_defaults(func=cmd_key_import)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the pypi-profile CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return EXIT_OK

    configure_console_streams()

    from pypi_profile.log import configure_logging

    configure_logging("DEBUG" if args.verbose else args.log_level)

    logger.debug("Running command %r", args.command)
    try:
        args.func(args)
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code
    return EXIT_OK


def launch_gui() -> None:
    from pypi_profile.gui import main as gui_main

    gui_main()


def cmd_gui(args: argparse.Namespace) -> None:
    """Launch the GUI unless dry-run mode is active."""
    if is_dry_run(args):
        print_dry_run("gui would launch the Tkinter desktop app.")
        return
    launch_gui()


if __name__ == "__main__":
    raise SystemExit(main())
