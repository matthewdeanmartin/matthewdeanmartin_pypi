"""Tkinter GUI for pypi-profile CLI commands."""

# pylint: disable=too-many-lines

from __future__ import annotations

import contextlib

# The GUI launches the local pypi-profile CLI without shell=True.
import subprocess  # nosec B404
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from tkinter import filedialog, font, scrolledtext, ttk
from typing import Any, Literal, TypedDict, Union, cast

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

TkVar = Union[tk.StringVar, tk.BooleanVar]

# Sentinel shown in the key picker when the keyring is the active source.
# When this value is selected we do NOT pass PYPI_PROFILE_KEY_PATH, which lets
# load_secret_key fall through to the keyring automatically.
_KEYRING_SENTINEL = "(keyring)"


def _get_string_var(var: TkVar | None, default: str = "") -> str:
    """Return a variable's value as text."""
    if var is None:
        return default
    return str(cast(Any, var).get())


def _get_bool_var(var: TkVar | None, default: bool = False) -> bool:
    """Return a variable's value as bool."""
    if var is None:
        return default
    return bool(cast(Any, var).get())


def _set_var(var: TkVar | None, value: str | bool) -> None:
    """Set a Tk variable when present."""
    if var is not None:
        cast(Any, var).set(value)


def _detect_keyring_status() -> str:
    """Return a short human-readable keyring status string."""
    try:
        import keyring
        import keyring.backends.fail
        from keyring.errors import KeyringError
    except ImportError:
        return "unavailable"

    try:
        backend = keyring.get_keyring()
        if isinstance(backend, keyring.backends.fail.Keyring):
            return "unavailable (disk only)"
        return f"active ({type(backend).__name__})"
    except (KeyringError, RuntimeError):
        return "unavailable"


def _load_toml_info(path_str: str) -> dict[str, str]:
    """Return a dict with keys: full_path, rel_path, pypi_username, public_key."""
    result = {"full_path": "", "rel_path": "", "pypi_username": "", "public_key": ""}
    if not path_str.strip():
        return result
    p = Path(path_str.strip()).expanduser()
    if not p.exists():
        return result

    resolved = p.resolve()
    result["full_path"] = str(resolved)
    try:
        result["rel_path"] = str(resolved.relative_to(Path.cwd()))
    except ValueError:
        result["rel_path"] = str(resolved)

    try:
        with open(p, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return result

    identity = data.get("identity", {})
    verification = data.get("verification", {})
    if isinstance(identity, dict):
        result["pypi_username"] = str(identity.get("pypi_username", ""))
    if isinstance(verification, dict):
        result["public_key"] = str(verification.get("public_key", ""))
    return result


def _has_signing_key() -> bool:
    """Return True if a signing key is available (keyring or default disk path)."""
    try:
        import keyring
        import keyring.backends.fail

        backend = keyring.get_keyring()
        if not isinstance(backend, keyring.backends.fail.Keyring):
            _encoded = keyring.get_password("pypi-profile", keyring.get_keyring().__class__.__name__)
            # Any non-fail backend counts — we can't easily check without knowing the username yet
            # so just confirm the backend is usable; load_secret_key will resolve the rest.
            return True
    except Exception:
        pass
    return Path("~/.pypi_profile/minisign.key").expanduser().exists()


def _profile_text(path_str: str) -> str:
    """Render a profile TOML as a human-readable markdown-style text summary."""
    if not path_str.strip():
        return "(No profile selected.)"
    p = Path(path_str.strip()).expanduser()
    if not p.exists():
        return f"(File not found: {p})"
    try:
        with open(p, "rb") as fh:
            data = tomllib.load(fh)
    except Exception as exc:
        return f"(Could not parse TOML: {exc})"

    lines: list[str] = []

    prof = data.get("profile", {})
    ident = data.get("identity", {})
    verif = data.get("verification", {})

    display_name = prof.get("display_name") or ident.get("display_name") or "Unknown"
    kind = prof.get("kind", "individual")
    summary = prof.get("summary", "")
    pypi_user = ident.get("pypi_username", "")
    location = ident.get("location", "")
    timezone = ident.get("timezone", "")
    pronouns = ident.get("pronouns", "")

    lines.append(f"# {display_name}  ({kind})")
    if summary:
        lines.append(f"\n{summary}")
    lines.append("")

    meta_parts = []
    if pypi_user:
        meta_parts.append(f"PyPI: {pypi_user}")
    if location:
        meta_parts.append(f"Location: {location}")
    if timezone:
        meta_parts.append(f"TZ: {timezone}")
    if pronouns:
        meta_parts.append(f"Pronouns: {pronouns}")
    if meta_parts:
        lines.append("  " + "  ·  ".join(meta_parts))
        lines.append("")

    pub_key = verif.get("public_key", "")
    if pub_key:
        lines.append(f"  Signing key: {pub_key[:20]}…  (public key present)")
    else:
        lines.append("  Signing key: (none — run Keygen)")
    lines.append("")

    packages = data.get("packages", [])
    if packages:
        lines.append(f"## Packages ({len(packages)})")
        for pkg in packages:
            state = pkg.get("state", "")
            role = pkg.get("role", "")
            tag = f"[{state}]" if state else ""
            summ = (pkg.get("summary") or "")[:72]
            lines.append(f"  - **{pkg.get('name', '?')}**  {role} {tag}")
            if summ:
                lines.append(f"      {summ}")
        lines.append("")

    profiles = data.get("profiles", [])
    if profiles:
        lines.append(f"## External Profiles ({len(profiles)})")
        for lnk in profiles:
            vstat = lnk.get("verification", "self_asserted")
            proof = "✓" if lnk.get("stored_proof") else "·"
            lines.append(f"  {proof} {lnk.get('label', lnk.get('kind', '?'))}: {lnk.get('url', '')}")
            if vstat not in ("self_asserted", ""):
                lines.append(f"      verification: {vstat}")
        lines.append("")

    contacts = data.get("contact_methods", [])
    if contacts:
        lines.append(f"## Contact ({len(contacts)})")
        for c in contacts:
            vis = c.get("visibility", "public")
            aud = ", ".join(c.get("audience", []))
            lines.append(f"  - {c.get('label', c.get('kind', '?'))}: {c.get('value', '')}  [{vis}] {aud}")
        lines.append("")

    hiring = data.get("hiring", {})
    if hiring.get("open_to_work_since"):
        lines.append("## Hiring")
        lines.append(f"  Open to work since: {hiring['open_to_work_since']}")
        if hiring.get("employment_types"):
            lines.append(f"  Employment types: {', '.join(hiring['employment_types'])}")
        if hiring.get("work_model"):
            lines.append(f"  Work model: {', '.join(hiring['work_model'])}")
        lines.append("")

    projects = data.get("projects", [])
    if projects:
        lines.append(f"## Projects ({len(projects)})")
        for proj in projects:
            lines.append(f"  - **{proj.get('name', '?')}**  {proj.get('role', '')}  [{proj.get('state', '')}]")
            if proj.get("url"):
                lines.append(f"      {proj['url']}")
        lines.append("")

    work = data.get("work_experience", [])
    if work:
        lines.append(f"## Work Experience ({len(work)})")
        for w in work:
            lines.append(
                f"  - {w.get('organization', '?')}  —  {w.get('title', '')}  ({w.get('start_date', '')} – {w.get('end_date', '')})"
            )
        lines.append("")

    succession = data.get("succession", {})
    if succession.get("policy"):
        lines.append("## Succession")
        lines.append(f"  Policy: {succession['policy']}")
        if succession.get("last_reviewed"):
            lines.append(f"  Last reviewed: {succession['last_reviewed']}")
        lines.append("")

    return "\n".join(lines)


ArgKind = Literal["file", "dir", "bool", "password", "choice", "str"]


class CommandArg(TypedDict, total=False):
    flag: str
    label: str
    default: str | bool
    kind: ArgKind
    choices: list[str]


class GuiCommand(TypedDict, total=False):
    name: str
    label: str
    help: str
    args: list[CommandArg]
    readonly: bool
    extra_argv: list[str]
    # "setup" commands don't use an active profile; "profile" commands do
    group: str


# Known identity platforms
IDENTITY_SITES: list[dict[str, str]] = [
    {
        "kind": "github",
        "label": "GitHub",
        "url_template": "https://github.com/{username}",
        "notes": "Add a pypi-profile proof string to your GitHub profile README or bio.",
    },
    {
        "kind": "gitlab",
        "label": "GitLab",
        "url_template": "https://gitlab.com/{username}",
        "notes": "Add a pypi-profile proof string to your GitLab profile bio.",
    },
    {
        "kind": "mastodon",
        "label": "Mastodon",
        "url_template": "https://{instance}/@{username}",
        "notes": "Add a proof string to a public Mastodon post or your profile bio. Uses compact token format.",
    },
    {
        "kind": "bluesky",
        "label": "Bluesky",
        "url_template": "https://bsky.app/profile/{username}",
        "notes": "Add a pypi-profile proof string to a pinned Bluesky post.",
    },
    {
        "kind": "linkedin",
        "label": "LinkedIn",
        "url_template": "https://www.linkedin.com/in/{username}",
        "notes": "Add the proof string to your LinkedIn About section or a featured post.",
    },
    {
        "kind": "twitter",
        "label": "Twitter / X",
        "url_template": "https://x.com/{username}",
        "notes": "Add the proof string to a pinned tweet or your bio.",
    },
    {
        "kind": "blogger",
        "label": "Blogger",
        "url_template": "https://{username}.blogspot.com",
        "notes": "Add a pypi-profile proof string to a post or your About page.",
    },
    {
        "kind": "wordpress",
        "label": "WordPress",
        "url_template": "https://{username}.wordpress.com",
        "notes": "Add the proof string to a dedicated page or your About widget.",
    },
    {
        "kind": "website",
        "label": "Personal Website",
        "url_template": "https://{domain}",
        "notes": "Add a pypi-profile proof string anywhere on the page (e.g. <meta> tag or footer).",
    },
    {
        "kind": "stackoverflow",
        "label": "Stack Overflow",
        "url_template": "https://stackoverflow.com/users/{user_id}",
        "notes": "Add the proof string to your Stack Overflow profile bio.",
    },
    {
        "kind": "keybase",
        "label": "Keybase",
        "url_template": "https://keybase.io/{username}",
        "notes": "Post the proof string as a Keybase proof or add it to your profile.",
    },
    {
        "kind": "orcid",
        "label": "ORCID",
        "url_template": "https://orcid.org/{orcid_id}",
        "notes": "Add the proof string to your ORCID biography field.",
    },
    {
        "kind": "other",
        "label": "Other (custom)",
        "url_template": "",
        "notes": "Enter any URL you control. Add the proof string somewhere visible on that page.",
    },
]

IDENTITY_SITE_LABELS = [s["label"] for s in IDENTITY_SITES]
IDENTITY_SITE_BY_LABEL = {s["label"]: s for s in IDENTITY_SITES}

# Flags that take a signing-key path — seeded from the global key picker
_KEY_FLAGS = {"--key"}


COMMANDS: list[GuiCommand] = [
    # ── Setup group (no active profile required) ──────────────────────────
    {
        "name": "init",
        "label": "Init",
        "group": "setup",
        "help": (
            "Create a skeleton pypi_profile.toml.\n\n"
            "Generates a minimal profile file you can fill in by hand.  "
            "Use --force to bulldoze an existing file and start fresh.\n\n"
            "To populate the profile from live data or a JSON Resume, use the "
            "Import command after Init.\n\n"
            "--username: your PyPI username\n"
            "--kind: individual / team / company / llc / foundation / collective / project / other\n"
            "--output: output path (default: pypi_profile.toml)\n"
            "--force: overwrite (bulldoze) an existing file"
        ),
        "args": [
            {"flag": "--username", "label": "PyPI username", "default": "", "kind": "str"},
            {
                "flag": "--kind",
                "label": "Kind",
                "default": "individual",
                "kind": "choice",
                "choices": [
                    "individual",
                    "team",
                    "company",
                    "llc",
                    "foundation",
                    "collective",
                    "project",
                    "other",
                ],
            },
            {"flag": "--output", "label": "Output path", "default": "pypi_profile.toml", "kind": "str"},
            {"flag": "--force", "label": "Force overwrite (bulldoze)", "default": False, "kind": "bool"},
        ],
        "extra_argv": ["--no-interactive"],
        "readonly": False,
    },
    {
        "name": "import",
        "label": "Import",
        "group": "setup",
        "help": (
            "Import data into an existing pypi_profile.toml.\n\n"
            "Merges live PyPI/GitHub package data and/or a JSON Resume file into "
            "the active profile.  Run Init first to create the skeleton.\n\n"
            "--fetch: pull live package and profile data from PyPI and GitHub\n"
            "--from-json-resume: path to a resume.json file to merge in\n"
            "--force: overwrite the output file even if it already exists\n\n"
            "Uses the profile selected in the top bar."
        ),
        "args": [
            {"flag": "--fetch", "label": "Fetch live data (PyPI / GitHub)", "default": True, "kind": "bool"},
            {"flag": "--from-json-resume", "label": "JSON Resume path", "default": "", "kind": "file"},
            {"flag": "--force", "label": "Force overwrite", "default": True, "kind": "bool"},
        ],
        "extra_argv": ["--no-interactive"],
        "readonly": False,
    },
    {
        "name": "keygen",
        "label": "Keygen",
        "group": "setup",
        "help": (
            "Generate a minisign keypair for signing profile claims.\n\n"
            "Creates a secret key and a public key.  The public key's base-64 value "
            "is written automatically into [verification] public_key in your profile.\n\n"
            "--key-dir: directory to write the key files (default: ~/.pypi_profile/)\n"
            "--keyring-identity: name for this key in the system keyring.\n"
            "  Defaults to your PyPI username so multiple accounts stay separate.\n"
            "--no-keyring: skip keyring storage and keep the key as a disk file only.\n"
            "--password: optional password to encrypt the on-disk secret key file.\n"
            "--force: overwrite existing key files"
        ),
        "args": [
            {"flag": "--key-dir", "label": "Key directory", "default": "~/.pypi_profile/", "kind": "dir"},
            {
                "flag": "--keyring-identity",
                "label": "Keyring identity (blank = PyPI username)",
                "default": "",
                "kind": "str",
            },
            {"flag": "--no-keyring", "label": "Disk only (skip keyring)", "default": False, "kind": "bool"},
            {"flag": "--password", "label": "Disk-key password (optional)", "default": "", "kind": "password"},
            {"flag": "--force", "label": "Force overwrite", "default": False, "kind": "bool"},
        ],
        "readonly": False,
    },
    # ── Profile group (active profile required) ───────────────────────────
    {
        "name": "display-text",
        "label": "Display Text",
        "group": "profile",
        "help": (
            "Display a human-readable summary of the active profile.\n\n"
            "Renders the profile as plain text with markdown-style formatting — "
            "a quick overview of who you are, your packages, external profiles, "
            "and signing/verification status.\n\n"
            "Uses the profile selected in the top bar.\n"
            "No network calls are made."
        ),
        "args": [],
        "readonly": True,
    },
    {
        "name": "inspect",
        "label": "Inspect",
        "group": "profile",
        "help": (
            "Inspect a profile package or TOML file without executing any plugin code.\n\n"
            "Prints a quick summary: principal name, PyPI username, number of packages, "
            "projects, humans, and whether a signing key is configured.\n\n"
            "Uses the profile selected in the top bar."
        ),
        "args": [],
        "readonly": True,
    },
    {
        "name": "validate",
        "label": "Validate",
        "group": "profile",
        "help": (
            "Validate a pypi_profile.toml file against the Pydantic schema.\n\n"
            "Reports OK with a brief summary on success, or prints detailed "
            "validation errors on failure.\n\n"
            "Uses the profile selected in the top bar."
        ),
        "args": [],
        "readonly": True,
    },
    {
        "name": "fetch",
        "label": "Fetch",
        "group": "profile",
        "help": (
            "Fetch live metadata from PyPI, GitHub, GitLab, and Mastodon.\n\n"
            "Compares the packages declared in the profile against what is actually "
            "published on PyPI and prints a reconciliation report.\n\n"
            "Uses the profile selected in the top bar.\n"
            "--json: also print the raw API responses as JSON."
        ),
        "args": [
            {"flag": "--json", "label": "Print raw JSON", "default": False, "kind": "bool"},
        ],
        "readonly": True,
    },
    {
        "name": "verify",
        "label": "Verify Claims",
        "group": "profile",
        "help": (
            "Verify proof-of-control claims for all [[profiles]] entries.\n\n"
            "Fetches each declared URL and looks for the signed proof string embedded "
            "in the page.  Requires a public_key in the [verification] section.\n\n"
            "Uses the profile selected in the top bar.\n"
            "--profile-package: override the profile package name used in the claim message."
        ),
        "args": [
            {"flag": "--profile-package", "label": "Profile package name override", "default": "", "kind": "str"},
        ],
        "readonly": True,
    },
    {
        "name": "sign",
        "label": "Sign Claim",
        "group": "profile",
        "help": (
            "Sign a controls-url claim and print the proof string.\n\n"
            "Use this to prove you control an external URL (GitHub profile, website, etc.).  "
            "Copy the printed proof string and place it at the target URL.\n\n"
            "Uses the profile selected in the top bar.\n"
            "--url: the URL you are asserting control over (required)\n"
            "--key: path to your secret key file (leave blank to use the keyring)\n"
            "--profile-package: override the profile package name\n\n"
            "Key password: leave blank — the signing key is loaded from your system "
            "keyring automatically.  Only enter a password if you are on a system "
            "without keyring support and your key file is password-protected."
        ),
        "args": [
            {"flag": "--url", "label": "URL to sign (required)", "default": "", "kind": "str"},
            {"flag": "--key", "label": "Secret key path (blank = keyring)", "default": "", "kind": "file"},
            {"flag": "--password", "label": "Key password (keyring fallback only)", "default": "", "kind": "password"},
            {"flag": "--profile-package", "label": "Profile package name override", "default": "", "kind": "str"},
        ],
        "readonly": False,
    },
    {
        "name": "update-proofs",
        "label": "Update Proofs",
        "group": "profile",
        "help": (
            "Sign all [[profiles]] URLs and write stored_proof values into the TOML.\n\n"
            "This is the batch equivalent of 'Sign Claim': it iterates every entry in "
            "[[profiles]] that uses controls-url verification, signs each URL with your "
            "minisign secret key, and patches the resulting proof strings directly into "
            "pypi_profile.toml under stored_proof.\n\n"
            "After running this command, commit the updated TOML so that the static "
            "build can embed the proofs without needing your private key.\n\n"
            "Uses the profile selected in the top bar.\n"
            "--key: path to your secret key file (leave blank to use the keyring)\n"
            "--profile-package: override the profile package name\n"
            "--force: re-sign URLs that already have a stored_proof\n\n"
            "Key password: leave blank — the signing key is loaded from your system "
            "keyring automatically."
        ),
        "args": [
            {"flag": "--key", "label": "Secret key path (blank = keyring)", "default": "", "kind": "file"},
            {"flag": "--password", "label": "Key password (keyring fallback only)", "default": "", "kind": "password"},
            {"flag": "--profile-package", "label": "Profile package name override", "default": "", "kind": "str"},
            {"flag": "--force", "label": "Re-sign existing proofs", "default": False, "kind": "bool"},
        ],
        "readonly": False,
    },
    {
        "name": "add-identity-site",
        "label": "Add Identity Site",
        "group": "profile",
        "help": (
            "Add a new [[profiles]] entry to your pypi_profile.toml.\n\n"
            "Choose a platform from the list — the URL template is pre-filled so you "
            "only need to substitute your username.  The entry is written into the TOML "
            "file immediately; run Update Proofs afterwards to generate and embed the "
            "signed proof.\n\n"
            "Uses the profile selected in the top bar.\n"
            "--site: the platform to add (pick from the list)\n"
            "--url: the full URL to your profile on that platform\n"
            "--label: display label (defaults to the platform name)\n"
            "--rel-me: set rel_me = true (for IndieWeb / webfinger verification)\n\n"  # nosec: B608
            "Supported platforms:\n" + "\n".join(f"  {s['label']}: {s['notes']}" for s in IDENTITY_SITES)
        ),
        "args": [
            {
                "flag": "--site",
                "label": "Platform",
                "default": IDENTITY_SITE_LABELS[0],
                "kind": "choice",
                "choices": IDENTITY_SITE_LABELS,
            },
            {"flag": "--url", "label": "Profile URL", "default": "", "kind": "str"},
            {"flag": "--label", "label": "Display label (optional)", "default": "", "kind": "str"},
            {"flag": "--rel-me", "label": "Set rel_me = true", "default": True, "kind": "bool"},
        ],
        "readonly": False,
    },
    # ── Website group ────────────────────────────────────────────────────
    {
        "name": "build",
        "label": "Build Static Site",
        "group": "website",
        "help": (
            "Generate a static HTML site from the active profile.\n\n"
            "Output goes to  ./site/<pypi_username>/  by default, matching the layout "
            "expected by GitHub Pages (one subdirectory per user).\n\n"
            "Uses the profile selected in the top bar.\n"
            "--output: override the output directory\n"
            "--base-url: URL prefix for asset paths, e.g. /myuser for GitHub Pages\n"
            "--resume-file: path to a JSON Resume file (auto-discovered if omitted)\n\n"
            "After building, press Open to view the site in your browser, or commit "
            "the ./site/ directory and push to GitHub Pages."
        ),
        "args": [
            {"flag": "--output", "label": "Output directory", "default": "", "kind": "dir"},
            {"flag": "--base-url", "label": "Base URL (e.g. /myuser)", "default": "", "kind": "str"},
            {"flag": "--resume-file", "label": "JSON Resume path (optional)", "default": "", "kind": "file"},
        ],
        "readonly": False,
    },
    {
        "name": "serve-static",
        "label": "Serve Static Site",
        "group": "website",
        "help": (
            "Serve the built static site with Python's built-in HTTP server.\n\n"
            "Run 'Build Static Site' first to generate the output.  "
            "This command then starts a lightweight file server so you can browse "
            "the result exactly as it will appear on GitHub Pages.\n\n"
            "The Open button (and auto-open on Run) will launch the site in your "
            "default browser.\n\n"
            "--port: port to listen on (default: 8001 to avoid clashing with Live Preview)\n"
            "--directory: override the directory to serve (default: site/<pypi_username>/)"
        ),
        "args": [
            {"flag": "--port", "label": "Port", "default": "8001", "kind": "str"},
            {"flag": "--directory", "label": "Directory (blank = auto)", "default": "", "kind": "dir"},
        ],
        "readonly": False,
    },
    {
        "name": "serve",
        "label": "Live Preview",
        "group": "website",
        "help": (
            "Start the FastAPI profile web server for live preview.\n\n"
            "Opens a local HTTP server so you can preview your profile in a browser.  "
            "The Open button launches your default browser automatically.\n"
            "Press Stop to shut down the server.\n\n"
            "Uses the profile selected in the top bar.\n"
            "--host: bind address (default: 127.0.0.1)\n"
            "--port: port number (default: 8000)\n"
            "--allow-code: enable plugin code execution (off by default for safety)"
        ),
        "args": [
            {"flag": "--host", "label": "Host", "default": "127.0.0.1", "kind": "str"},
            {"flag": "--port", "label": "Port", "default": "8000", "kind": "str"},
            {"flag": "--allow-code", "label": "Allow plugin code", "default": False, "kind": "bool"},
        ],
        "readonly": False,
    },
    # ── Key Management group ──────────────────────────────────────────────
    {
        "name": "key-info",
        "label": "Key Info",
        "group": "keys",
        "help": (
            "Inspect the active signing key without modifying anything.\n\n"
            "Shows the key source (keyring or disk), key ID, generation date, "
            "public key (truncated), and whether it matches the public key in your "
            "active pypi_profile.toml.\n\n"
            "No arguments required — runs automatically."
        ),
        "args": [],
        "readonly": True,
    },
    {
        "name": "key-list",
        "label": "List Keys",
        "group": "keys",
        "help": (
            "List all known signing keys across the system keyring and disk.\n\n"
            "Searches the keyring (if available) and all *.key files in "
            "~/.pypi_profile/ and the current directory.  Each entry shows "
            "its source, key ID, and whether it matches your profile TOML.\n\n"
            "--json: emit machine-readable JSON instead of a table."
        ),
        "args": [
            {"flag": "--json", "label": "JSON output", "default": False, "kind": "bool"},
        ],
        "readonly": True,
    },
    {
        "name": "key-rotate",
        "label": "Rotate Key",
        "group": "keys",
        "help": (
            "Replace the active signing key and re-sign all profile proofs.\n\n"
            "Generates a new keypair, updates [verification] public_key in the TOML, "
            "and re-signs every [[profiles]] entry.  The old key is archived to a .bak "
            "file unless --no-keep-old is set.\n\n"
            "NOTE: stored_proof values already published on external pages will appear "
            "invalid until those pages are updated with the new proof strings.\n\n"
            "Uses the profile selected in the top bar.\n"
            "--key-dir: directory for the new key files\n"
            "--keyring-identity: name for the new key in the keyring\n"
            "--no-keep-old: discard the old key instead of archiving it\n"
            "--force: skip the interactive confirmation prompt"
        ),
        "args": [
            {"flag": "--key-dir", "label": "Key directory", "default": "~/.pypi_profile/", "kind": "dir"},
            {
                "flag": "--keyring-identity",
                "label": "Keyring identity (blank = default)",
                "default": "",
                "kind": "str",
            },
            {"flag": "--no-keep-old", "label": "Discard old key (no archive)", "default": False, "kind": "bool"},
            {"flag": "--force", "label": "Skip confirmation prompt", "default": True, "kind": "bool"},
        ],
        "readonly": False,
    },
    {
        "name": "key-recover",
        "label": "Recover Key",
        "group": "keys",
        "help": (
            "Recover from a lost signing key.\n\n"
            "When your secret key is gone (disk deleted, keyring wiped, new machine), "
            "this command generates a replacement keypair, updates [verification] "
            "public_key in the TOML, and re-signs all [[profiles]] entries.\n\n"
            "If the key is still present, the command exits early and tells you to "
            "use Rotate Key instead.\n\n"
            "After recovery, commit the TOML and update any external pages that "
            "embedded the old proof strings.\n\n"
            "Uses the profile selected in the top bar."
        ),
        "args": [
            {"flag": "--key-dir", "label": "Key directory", "default": "~/.pypi_profile/", "kind": "dir"},
            {
                "flag": "--keyring-identity",
                "label": "Keyring identity (blank = default)",
                "default": "",
                "kind": "str",
            },
        ],
        "readonly": False,
    },
    {
        "name": "key-export",
        "label": "Export Key",
        "group": "keys",
        "help": (
            "Export the secret key to a file for secure transfer.\n\n"
            "Writes the raw secret key bytes to the specified output file.  "
            "Use this to move your key to a new machine or set up CI/CD signing.\n\n"
            "WARNING: The exported file is your secret key.  Treat it like a "
            "password.  Never commit it to version control.\n\n"
            "--output: destination file path (required)\n"
            "--key: source key file (blank = keyring or default disk path)"
        ),
        "args": [
            {"flag": "--output", "label": "Output file path", "default": "minisign.key.export", "kind": "file"},
            {"flag": "--key", "label": "Source key (blank = default)", "default": "", "kind": "file"},
        ],
        "readonly": False,
    },
    {
        "name": "key-import",
        "label": "Import Key",
        "group": "keys",
        "help": (
            "Install an exported key file into the keyring and/or disk.\n\n"
            "Reads a previously exported key file (from key-export) and installs it "
            "into the system keyring and the default disk path.\n\n"
            "Use this to set up a key from another machine or import a CI signing key.\n\n"
            "--file: path to the exported key file\n"
            "--keyring-identity: name for the key in the keyring (blank = default)\n"
            "--no-keyring: store only on disk, skip the keyring\n"
            "--force: overwrite an existing key on disk"
        ),
        "args": [
            {"flag": "file", "label": "Key file to import", "default": "", "kind": "file"},
            {
                "flag": "--keyring-identity",
                "label": "Keyring identity (blank = default)",
                "default": "",
                "kind": "str",
            },
            {"flag": "--no-keyring", "label": "Disk only (skip keyring)", "default": False, "kind": "bool"},
            {"flag": "--force", "label": "Overwrite existing key", "default": False, "kind": "bool"},
        ],
        "readonly": False,
    },
    # ── Diagnostics group ─────────────────────────────────────────────────
    {
        "name": "doctor",
        "label": "Doctor",
        "group": "diagnostics",
        "help": (
            "Diagnose local configuration and profile health.\n\n"
            "Checks the config file, signing key, public key in TOML, and bundled "
            "template/static resources.  No arguments required — runs automatically."
        ),
        "args": [],
        "readonly": True,
    },
    {
        "name": "display-toml",
        "label": "Display TOML",
        "group": "diagnostics",
        "help": (
            "Display the raw contents of the active pypi_profile.toml file.\n\n"
            "Shows the file exactly as stored on disk — useful for reviewing what "
            "is committed to source control or verifying that Update Proofs wrote "
            "the correct stored_proof values.\n\n"
            "Uses the profile selected in the top bar."
        ),
        "args": [],
        "readonly": True,
    },
    {
        "name": "dump",
        "label": "Display JSON",
        "group": "diagnostics",
        "help": (
            "Display the parsed profile as pretty-printed JSON.\n\n"
            "Useful for debugging the data model or piping into other tools.\n\n"
            "Uses the profile selected in the top bar."
        ),
        "args": [],
        "readonly": True,
    },
]

HELP_INTRO = (
    "pypi-profile GUI\n"
    "================\n\n"
    "Active profile:\n"
    "  Use the top bar to select which pypi_profile.toml you're working with.\n"
    "  All profile commands read the active profile automatically.\n\n"
    "Signing key:\n"
    "  Select your secret key in the top bar.  Commands that sign use it automatically.\n"
    "  Multiple identities / keys are supported — just switch the key before running.\n\n"
    "Setup commands (Doctor, Init, Keygen) run without a profile.\n\n"
    "Read-only commands run automatically when selected.\n"
    "Write commands require you to press Run.\n\n"
    "Key & password:\n"
    "  Your signing key is stored in the system keyring — you do NOT need "
    "to type a password for commands that use it.  The password field is "
    "only needed on systems without keyring support when the key file on "
    "disk is password-protected."
)


class PypiProfileGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("pypi-profile GUI")
        self.geometry("1100x760")
        self.minsize(900, 600)
        self.running_proc: subprocess.Popen[str] | None = None
        self.current_cmd: GuiCommand | None = None
        self.arg_widgets: dict[str, TkVar] = {}
        self._open_url: str = ""  # URL/path the Open button will launch
        self._auto_open: bool = False  # open automatically when command succeeds

        # Active profile — source of truth for all profile commands
        self.active_source = tk.StringVar(value="")
        self.active_source.trace_add("write", self._on_source_changed)

        # Global signing key — source of truth for all signing commands.
        # Default to keyring if available; fall back to disk path.
        keyring_available = _detect_keyring_status().startswith("active")
        default_key = _KEYRING_SENTINEL if keyring_available else str(Path("~/.pypi_profile/minisign.key").expanduser())
        self.global_key_path = tk.StringVar(value=default_key)
        self.global_key_path.trace_add("write", self._on_key_changed)
        self.global_key_password = tk.StringVar(value="")

        self.build_ui()
        self.select_command(COMMANDS[0])
        self.after(100, self._refresh_profile_list)
        self.after(200, self._select_startup_command)

    # ── UI construction ───────────────────────────────────────────────────

    def build_ui(self) -> None:
        mono = font.Font(family="Courier New", size=10)

        self.columnconfigure(0, weight=0, minsize=165)
        self.columnconfigure(1, weight=3)
        self.columnconfigure(2, weight=1, minsize=240)
        self.rowconfigure(0, weight=0)  # top bar
        self.rowconfigure(1, weight=1)  # panels

        self._build_top_bar()
        self._build_left_panel()
        self._build_center_panel(mono)
        self._build_right_panel()

    def _build_top_bar(self) -> None:
        font_label = ("Helvetica", 9, "bold")
        font_value = ("Courier New", 9)
        label_width = 11

        top_bar = tk.Frame(self, bd=1, relief=tk.GROOVE)
        top_bar.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 0))
        top_bar.columnconfigure(1, weight=2)
        top_bar.columnconfigure(4, weight=1)

        def lbl(parent: tk.Frame, text: str, row: int, col: int) -> None:
            tk.Label(
                parent,
                text=text,
                font=font_label,
                width=label_width,
                anchor="e",
                padx=4,
            ).grid(row=row, column=col, sticky="e", pady=2)

        def val_lbl(parent: tk.Frame, var: tk.StringVar, row: int, col: int, columnspan: int = 1) -> None:
            tk.Label(
                parent,
                textvariable=var,
                font=font_value,
                anchor="w",
            ).grid(row=row, column=col, columnspan=columnspan, sticky="ew", pady=2, padx=(0, 4))

        # ── Row 0: Active profile picker ──
        lbl(top_bar, "Profile:", 0, 0)

        self.profile_picker_var = tk.StringVar(value="")
        self.profile_picker = ttk.Combobox(
            top_bar,
            textvariable=self.profile_picker_var,
            state="normal",
            font=font_value,
        )
        self.profile_picker.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(4, 2), padx=(0, 4))
        self.profile_picker.bind("<<ComboboxSelected>>", self._on_profile_picker_selected)
        self.profile_picker.bind("<Return>", self._on_profile_picker_selected)

        tk.Button(top_bar, text="Browse…", font=("Helvetica", 8), padx=4, command=self._browse_profile).grid(
            row=0, column=3, pady=(4, 2), padx=(0, 4)
        )
        tk.Button(top_bar, text="Refresh", font=("Helvetica", 8), padx=4, command=self._refresh_profile_list).grid(
            row=0, column=4, pady=(4, 2), padx=(0, 8)
        )

        # ── Row 1: Resolved path + PyPI user ──
        lbl(top_bar, "Path:", 1, 0)
        self.bar_path_var = tk.StringVar(value="(none selected)")
        val_lbl(top_bar, self.bar_path_var, 1, 1, columnspan=2)

        tk.Label(top_bar, text="PyPI user:", font=font_label, anchor="e", padx=4).grid(
            row=1, column=3, sticky="e", pady=2
        )
        self.bar_user_var = tk.StringVar(value="—")
        val_lbl(top_bar, self.bar_user_var, 1, 4)

        # ── Row 2: Active signing key picker ──
        lbl(top_bar, "Signing key:", 2, 0)

        self.key_picker_var = tk.StringVar(value=self.global_key_path.get())
        self.key_picker = ttk.Combobox(
            top_bar,
            textvariable=self.key_picker_var,
            state="normal",
            font=font_value,
        )
        self.key_picker.grid(row=2, column=1, columnspan=2, sticky="ew", pady=2, padx=(0, 4))
        self.key_picker.bind("<<ComboboxSelected>>", self._on_key_picker_selected)
        self.key_picker.bind("<Return>", self._on_key_picker_selected)
        self.after(150, self._refresh_key_list)

        tk.Button(top_bar, text="Browse…", font=("Helvetica", 8), padx=4, command=self._browse_key).grid(
            row=2, column=3, pady=2, padx=(0, 4)
        )

        keyring_status = _detect_keyring_status()
        keyring_note = f"Keyring backend: {keyring_status}"
        self._keyring_label = tk.Label(
            top_bar,
            text=keyring_note,
            font=("Helvetica", 8),
            anchor="w",
        )
        self._keyring_label.grid(row=2, column=4, sticky="w", pady=2, padx=(0, 8))

        # ── Row 3: Public key from TOML + key password ──
        lbl(top_bar, "TOML key:", 3, 0)
        self.bar_key_var = tk.StringVar(value="—")
        val_lbl(top_bar, self.bar_key_var, 3, 1, columnspan=2)

        tk.Label(
            top_bar,
            text="Key password:",
            font=font_label,
            anchor="e",
            padx=4,
        ).grid(row=3, column=3, sticky="e", pady=(2, 4))
        tk.Entry(
            top_bar,
            textvariable=self.global_key_password,
            show="*",
            width=18,
            font=font_value,
        ).grid(row=3, column=4, sticky="ew", pady=(2, 4), padx=(0, 8))

    def _build_left_panel(self) -> None:
        left = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        left.grid(row=1, column=0, sticky="nsew", padx=(4, 0), pady=4)
        left.columnconfigure(0, weight=1)

        self.cmd_buttons: dict[str, tk.Button] = {}
        row_i = 0

        groups = [
            ("setup", "── Setup ──"),
            ("profile", "── Profile ──"),
            ("website", "── Website ──"),
            ("keys", "── Key Management ──"),
            ("diagnostics", "── Diagnostics ──"),
        ]
        for group, heading in groups:
            tk.Label(
                left,
                text=heading,
                font=("Helvetica", 8, "bold"),
                anchor="w",
                padx=8,
                pady=4,
            ).grid(row=row_i, column=0, sticky="ew")
            row_i += 1

            for cmd in COMMANDS:
                if cmd.get("group", "profile") != group:
                    continue
                btn = tk.Button(
                    left,
                    text=cmd["label"],
                    anchor="w",
                    padx=8,
                    relief=tk.FLAT,
                    command=self.make_select_command(cmd),
                )
                btn.grid(row=row_i, column=0, sticky="ew", padx=2, pady=1)
                self.cmd_buttons[cmd["name"]] = btn
                row_i += 1

    def _build_center_panel(self, mono: font.Font) -> None:
        center = tk.Frame(self)
        center.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)
        center.rowconfigure(3, weight=1)
        center.columnconfigure(0, weight=1)

        self.title_var = tk.StringVar(value="")
        tk.Label(
            center,
            textvariable=self.title_var,
            font=("Helvetica", 13, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        args_outer = tk.Frame(center, bd=1, relief=tk.GROOVE)
        args_outer.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        args_outer.columnconfigure(0, weight=1)
        self.args_frame = args_outer

        tk.Label(center, text="Output", anchor="w", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w")

        self.output = scrolledtext.ScrolledText(center, font=mono, wrap=tk.WORD)
        self.output.grid(row=3, column=0, sticky="nsew")

        btn_bar = tk.Frame(center)
        btn_bar.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        self.run_btn = tk.Button(btn_bar, text="Run", width=10, command=self.run_command, bg="#0e7c0e", fg="black")
        self.run_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.stop_btn = tk.Button(
            btn_bar, text="Stop", width=10, command=self.stop_command, bg="#7c0e0e", fg="black", state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.open_btn = tk.Button(btn_bar, text="Open", width=10, command=self._open_in_browser, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(btn_bar, textvariable=self.status_var, fg="#888888")
        self.status_label.pack(side=tk.LEFT, padx=8)

    def _build_right_panel(self) -> None:
        right = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        right.grid(row=1, column=2, sticky="nsew", padx=(0, 4), pady=4)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        tk.Label(right, text="Help", font=("Helvetica", 11, "bold"), anchor="w", pady=4).grid(
            row=0, column=0, sticky="ew", padx=6
        )
        self.help_text = scrolledtext.ScrolledText(right, font=("Helvetica", 10), wrap=tk.WORD, relief=tk.FLAT)
        self.help_text.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.help_text.insert(tk.END, HELP_INTRO)
        self.help_text.config(state=tk.DISABLED)

    # ── Top-bar helpers: profile ──────────────────────────────────────────

    def _on_source_changed(self, *_: object) -> None:
        self._refresh_status_bar()
        self._update_keyring_identity_hint()

    def _refresh_status_bar(self) -> None:
        source = self.active_source.get()
        info = _load_toml_info(source)
        if info["full_path"]:
            rel = info["rel_path"]
            full = info["full_path"]
            path_text = rel if rel == full else f"{rel}   ({full})"
        else:
            path_text = source if source.strip() else "(none selected)"
        self.bar_path_var.set(path_text)
        self.bar_user_var.set(info["pypi_username"] or "—")
        pub = info["public_key"]
        self.bar_key_var.set((pub[:44] + "…") if len(pub) > 44 else (pub or "—"))

    def _update_keyring_identity_hint(self) -> None:
        """Update the keyring status label to show which identity will be used."""
        pypi_user = self.bar_user_var.get().strip()
        base_status = _detect_keyring_status()
        if base_status.startswith("active") and pypi_user and pypi_user != "—":
            label_text = f"Keyring: {base_status} · identity: {pypi_user!r}"
        else:
            label_text = f"Keyring backend: {base_status}"
        if hasattr(self, "_keyring_label"):
            self._keyring_label.config(text=label_text)

    def _select_startup_command(self) -> None:
        """Choose the most useful command based on what's configured on disk."""
        has_profile = bool(self.active_source.get().strip())
        has_key = _has_signing_key()
        if not has_profile:
            target = "init"
        elif not has_key:
            target = "keygen"
        else:
            target = "display-text"
        cmd = next((c for c in COMMANDS if c["name"] == target), None)
        if cmd is not None:
            self.select_command(cmd)

    def _refresh_profile_list(self) -> None:
        from pypi_profile.finder import find_profile_files

        found = find_profile_files()
        paths = [str(p) for p in found]
        self.profile_picker["values"] = paths
        if paths and not self.profile_picker_var.get():
            self.profile_picker_var.set(paths[0])
            self._apply_profile_picker()

    def _apply_profile_picker(self) -> None:
        chosen = self.profile_picker_var.get().strip()
        if not chosen:
            return
        self.active_source.set(chosen)
        src_var = self.arg_widgets.get("source") or self.arg_widgets.get("path")
        _set_var(src_var, chosen)

    def _on_profile_picker_selected(self, _event: object = None) -> None:
        self._apply_profile_picker()

    def _browse_profile(self) -> None:
        path = filedialog.askopenfilename(
            title="Select profile file",
            filetypes=[("TOML files", "*.toml"), ("All files", "*.*")],
        )
        if path:
            self.profile_picker_var.set(path)
            vals = list(self.profile_picker["values"])
            if path not in vals:
                vals.insert(0, path)
                self.profile_picker["values"] = vals
            self._apply_profile_picker()

    # ── Top-bar helpers: signing key ──────────────────────────────────────

    def _on_key_changed(self, *_: object) -> None:
        self.key_picker_var.set(self.global_key_path.get())
        self._propagate_key_to_form()

    def _on_key_picker_selected(self, _event: object = None) -> None:
        chosen = self.key_picker_var.get().strip()
        if chosen:
            self.global_key_path.set(chosen)
            self._propagate_key_to_form()

    def _propagate_key_to_form(self) -> None:
        key_var = self.arg_widgets.get("--key")
        path = self.global_key_path.get()
        _set_var(key_var, "" if path == _KEYRING_SENTINEL else path)

    def _refresh_key_list(self) -> None:
        """Populate the key picker: keyring sentinel first (if available), then disk key files."""
        candidates: list[str] = []

        if _detect_keyring_status().startswith("active"):
            candidates.append(_KEYRING_SENTINEL)

        search_dirs = [
            Path("~/.pypi_profile/").expanduser(),
            Path.cwd(),
            Path.cwd() / ".pypi_profile",
        ]
        for d in search_dirs:
            if d.is_dir():
                for p in sorted(d.glob("*.key")):
                    s = str(p)
                    if s not in candidates:
                        candidates.append(s)

        current = self.key_picker_var.get().strip()
        if current and current not in candidates:
            candidates.insert(0, current)
        self.key_picker["values"] = candidates

    def _browse_key(self) -> None:
        path = filedialog.askopenfilename(
            title="Select secret key file",
            filetypes=[("Key files", "*.key"), ("All files", "*.*")],
        )
        if path:
            self.global_key_path.set(path)
            vals = list(self.key_picker["values"])
            if path not in vals:
                vals.insert(0, path)
                self.key_picker["values"] = vals
            self.key_picker_var.set(path)
            self._propagate_key_to_form()

    # ── Platform-picker for Add Identity Site ─────────────────────────────

    def _on_site_choice_changed(self, *_: object) -> None:
        site_var = self.arg_widgets.get("--site")
        url_var = self.arg_widgets.get("--url")
        label_var = self.arg_widgets.get("--label")
        if site_var is None:
            return
        chosen_label = _get_string_var(site_var)
        site = IDENTITY_SITE_BY_LABEL.get(chosen_label)
        if site is None:
            return
        _set_var(url_var, site["url_template"])
        _set_var(label_var, chosen_label)
        cmd = self.current_cmd
        if cmd and cmd["name"] == "add-identity-site":
            extra = (
                f"\nSelected platform: {chosen_label}"
                f"\nURL template: {site['url_template']}"
                f"\nNotes: {site['notes']}"
            )
            self.update_help(cmd["help"] + extra)

    # ── Command selection ─────────────────────────────────────────────────

    def make_select_command(self, cmd: GuiCommand) -> Callable[[], None]:
        def _select() -> None:
            self.select_command(cmd)

        return _select

    def select_command(self, cmd: GuiCommand) -> None:
        self.stop_command()
        self.current_cmd = cmd
        self._open_url = ""
        self._auto_open = False
        self.open_btn.config(state=tk.DISABLED)

        for name, btn in self.cmd_buttons.items():
            is_active = name == cmd["name"]
            btn.config(relief=tk.SUNKEN if is_active else tk.FLAT)

        self.title_var.set(cmd["label"])
        self.build_args_form(cmd)
        self.update_help(cmd["help"])
        self.output.delete("1.0", tk.END)

        if cmd["readonly"]:
            self.run_btn.config(state=tk.DISABLED)
            self.run_command()
        else:
            self.run_btn.config(state=tk.NORMAL)

    def build_args_form(self, cmd: GuiCommand) -> None:
        for w in self.args_frame.winfo_children():
            w.destroy()
        self.arg_widgets.clear()

        if not cmd["args"]:
            tk.Label(self.args_frame, text="No arguments needed.", fg="#888888", pady=4).grid(
                row=0, column=0, columnspan=3, padx=8
            )
            return

        self.args_frame.columnconfigure(1, weight=1)
        for row_i, arg in enumerate(cmd["args"]):
            flag = arg["flag"]
            kind = arg["kind"]
            label_text = arg["label"]

            # Determine live default for this field
            if flag in _KEY_FLAGS:
                default = self.global_key_path.get()
            else:
                default = arg["default"]

            tk.Label(self.args_frame, text=label_text + ":", anchor="e").grid(
                row=row_i, column=0, sticky="e", padx=(8, 4), pady=3
            )

            if kind == "bool":
                bool_var = tk.BooleanVar(value=bool(default))
                tk.Checkbutton(self.args_frame, variable=bool_var).grid(row=row_i, column=1, sticky="w", pady=3)
                self.arg_widgets[flag] = bool_var

            elif kind == "choice":
                choice_var = tk.StringVar(value=str(default))
                cb = ttk.Combobox(
                    self.args_frame, textvariable=choice_var, values=arg["choices"], state="readonly", width=24
                )
                cb.grid(row=row_i, column=1, sticky="ew", pady=3, padx=(0, 8))
                self.arg_widgets[flag] = choice_var
                if cmd["name"] == "add-identity-site" and flag == "--site":
                    choice_var.trace_add("write", self._on_site_choice_changed)

            elif kind == "password":
                password_var = tk.StringVar(value=str(default))
                pw_frame = tk.Frame(self.args_frame)
                pw_frame.grid(row=row_i, column=1, columnspan=2, sticky="ew", pady=3, padx=(0, 8))
                pw_frame.columnconfigure(0, weight=1)
                tk.Entry(pw_frame, textvariable=password_var, show="*", width=36).grid(row=0, column=0, sticky="ew")
                tk.Label(
                    pw_frame,
                    text="Leave blank — keyring handles this automatically.",
                    fg="#888888",
                    font=("Helvetica", 8),
                    anchor="w",
                ).grid(row=1, column=0, sticky="w")
                self.arg_widgets[flag] = password_var

            elif kind in ("file", "dir"):
                path_var = tk.StringVar(value=str(default))
                entry = tk.Entry(self.args_frame, textvariable=path_var, width=36)
                entry.grid(row=row_i, column=1, sticky="ew", pady=3)

                if kind == "file":

                    def _browse(v: tk.StringVar = path_var) -> None:
                        if p := filedialog.askopenfilename():
                            v.set(p)

                else:

                    def _browse(v: tk.StringVar = path_var) -> None:
                        if p := filedialog.askdirectory():
                            v.set(p)

                tk.Button(self.args_frame, text="Browse", command=_browse).grid(
                    row=row_i, column=2, padx=(4, 8), pady=3
                )
                self.arg_widgets[flag] = path_var

            else:
                text_var = tk.StringVar(value=str(default))
                tk.Entry(self.args_frame, textvariable=text_var, width=36).grid(
                    row=row_i, column=1, sticky="ew", pady=3, padx=(0, 8)
                )
                self.arg_widgets[flag] = text_var

    # ── Help ──────────────────────────────────────────────────────────────

    def update_help(self, text: str) -> None:
        self.help_text.config(state=tk.NORMAL)
        self.help_text.delete("1.0", tk.END)
        self.help_text.insert(tk.END, text)
        self.help_text.config(state=tk.DISABLED)

    # ── Command execution ─────────────────────────────────────────────────

    def build_argv_and_env(self, cmd: GuiCommand) -> tuple[list[str], dict[str, str]]:
        import os

        extra_env: dict[str, str] = {}

        argv = [sys.executable, "-m", "pypi_profile.cli", cmd["name"]]

        if cmd["name"] == "sign":
            argv.append("controls-url")

        argv.extend(cmd.get("extra_argv", []))

        # For profile-group commands inject the active source as a positional arg.
        # The source field no longer appears in the args form; it comes from the top bar.
        _NEEDS_SOURCE = {
            "inspect",
            "validate",
            "dump",
            "fetch",
            "verify",
            "serve",
            "build",
            "sign",
            "update-proofs",
            "add-identity-site",
            "key-rotate",
            "key-recover",
        }
        if cmd["name"] in _NEEDS_SOURCE:
            source = self.active_source.get().strip()
            if source:
                argv.append(source)

        for arg in cmd["args"]:
            flag = arg["flag"]
            kind = arg["kind"]
            var = self.arg_widgets.get(flag)
            if var is None:
                continue

            if kind == "bool":
                if _get_bool_var(var):
                    argv.append(flag)
            elif kind == "password":
                value = _get_string_var(var).strip()
                if value:
                    extra_env["PYPI_PROFILE_KEY_PASSWORD"] = value
            elif flag.startswith("--"):
                value = _get_string_var(var).strip()
                # For build --output, derive the default from the profile username when blank.
                if not value and cmd["name"] == "build" and flag == "--output":
                    info = _load_toml_info(self.active_source.get())
                    username = info.get("pypi_username", "")
                    value = str(Path("site") / username) if username else "site"
                if value:
                    argv += [flag, value]
            else:
                value = _get_string_var(var).strip()
                if value:
                    argv.append(value)

        # Global key: only set PYPI_PROFILE_KEY_PATH if a disk key was explicitly chosen
        # (i.e. not the keyring sentinel). Leaving it unset lets load_secret_key use the keyring.
        key_path = self.global_key_path.get().strip()
        key_password = self.global_key_password.get().strip()
        if key_path and key_path != _KEYRING_SENTINEL:
            extra_env.setdefault("PYPI_PROFILE_KEY_PATH", key_path)
        if key_password:
            extra_env.setdefault("PYPI_PROFILE_KEY_PASSWORD", key_password)

        return argv, {**os.environ, **extra_env}

    def run_command(self) -> None:
        cmd = self.current_cmd
        if cmd is None:
            return

        self.output.delete("1.0", tk.END)

        if cmd["name"] == "display-text":
            self._run_display_text()
            return

        if cmd["name"] == "display-toml":
            self._run_display_toml()
            return

        if cmd["name"] == "import":
            self._run_import()
            return

        if cmd["name"] == "add-identity-site":
            self._run_add_identity_site()
            return

        if cmd["name"] == "serve-static":
            self._run_serve_static()
            return

        # Configure Open button before launching so it's ready when the process finishes.
        self._open_url = ""
        self._auto_open = False
        if cmd["name"] == "serve":
            host_var = self.arg_widgets.get("--host")
            port_var = self.arg_widgets.get("--port")
            host = _get_string_var(host_var, "127.0.0.1") or "127.0.0.1"
            port = _get_string_var(port_var, "8000") or "8000"
            self._open_url = f"http://{host}:{port}/"
            self._auto_open = True
        elif cmd["name"] == "build":
            self._open_url = self._resolve_build_output_url()

        argv, env = self.build_argv_and_env(cmd)
        self.append_output(f"$ {' '.join(argv)}\n\n")
        self.status_var.set("Running…")
        self.status_label.config(fg="#888888")
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        # For serve: enable Open immediately and auto-open after the server has had time to start.
        if cmd["name"] == "serve" and self._open_url:
            self.open_btn.config(state=tk.NORMAL)
            self.after(1500, self._open_in_browser)

        def worker() -> None:
            try:
                with subprocess.Popen(  # nosec B603
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(Path.cwd()),
                    env=env,
                ) as proc:
                    self.running_proc = proc
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        self.append_output(line)
                    rc = proc.wait()
                self.running_proc = None
                self.after(0, lambda: self.on_done(rc, cmd))
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                self.append_output(f"\nERROR: {exc}\n")
                self.running_proc = None
                self.after(0, lambda: self.on_done(1, cmd))

        threading.Thread(target=worker, daemon=True).start()

    def _run_serve_static(self) -> None:
        """Serve the static build output with Python's http.server in a daemon thread."""
        import http.server
        import socketserver

        port_var = self.arg_widgets.get("--port")
        dir_var = self.arg_widgets.get("--directory")
        port_str = _get_string_var(port_var, "8001").strip() or "8001"
        dir_str = _get_string_var(dir_var).strip()

        try:
            port = int(port_str)
        except ValueError:
            self.append_output(f"ERROR: invalid port {port_str!r}\n")
            self.after(0, lambda: self._finish_current_command(1))
            return

        if not dir_str:
            info = _load_toml_info(self.active_source.get())
            username = info.get("pypi_username", "")
            dir_str = str(Path("site") / username) if username else "site"

        serve_dir = Path(dir_str).expanduser().resolve()
        if not serve_dir.is_dir():
            self.append_output(
                f"ERROR: directory not found: {serve_dir}\n" f"Run 'Build Static Site' first to generate the output.\n"
            )
            self.after(0, lambda: self._finish_current_command(1))
            return

        url = f"http://127.0.0.1:{port}/"
        self._open_url = url
        self._auto_open = True

        self.append_output(f"Serving {serve_dir}\n  at {url}\n  Press Stop to shut down.\n\n")
        self.status_var.set("Serving…")
        self.status_label.config(fg="#888888")
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.open_btn.config(state=tk.NORMAL)

        serve_dir_str = str(serve_dir)

        class _QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args: object, **kwargs: object) -> None:
                super().__init__(*args, directory=serve_dir_str, **kwargs)  # type: ignore[call-arg]

            def log_message(self, fmt: str, *args: object) -> None:
                pass  # suppress per-request stdout noise

        try:
            httpd = socketserver.TCPServer(("127.0.0.1", port), _QuietHandler)
        except OSError as exc:
            self.append_output(f"ERROR: could not bind port {port}: {exc}\n")
            self.run_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.after(0, lambda: self._finish_current_command(1))
            return

        self._static_httpd = httpd

        cmd_ref = self.current_cmd

        def worker() -> None:
            httpd.serve_forever()
            self.after(0, lambda: self.on_done(0, cmd_ref))  # type: ignore[arg-type]

        self._static_thread = threading.Thread(target=worker, daemon=True)
        self._static_thread.start()

        self.after(800, self._open_in_browser)

    def _run_display_text(self) -> None:
        source = self.active_source.get().strip()
        text = _profile_text(source)
        self.append_output(text)
        self.after(0, lambda: self._finish_current_command(0))

    def _run_import(self) -> None:
        """Run init with --force plus any import flags against the active profile path."""
        fetch_var = self.arg_widgets.get("--fetch")
        resume_var = self.arg_widgets.get("--from-json-resume")
        source = self.active_source.get().strip()

        argv = [sys.executable, "-m", "pypi_profile.cli", "init", "--no-interactive", "--force"]
        if source:
            argv += ["--output", source]
        if _get_bool_var(fetch_var):
            argv.append("--fetch")
        resume = _get_string_var(resume_var).strip()
        if resume:
            argv += ["--from-json-resume", resume]

        import os

        env = {**os.environ}
        self.append_output(f"$ {' '.join(argv)}\n\n")
        self.status_var.set("Running…")
        self.status_label.config(fg="#888888")
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        def worker() -> None:
            try:
                with subprocess.Popen(  # nosec B603
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(Path.cwd()),
                    env=env,
                ) as proc:
                    self.running_proc = proc
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        self.append_output(line)
                    rc = proc.wait()
                self.running_proc = None
                cmd = self.current_cmd
                self.after(0, lambda: self.on_done(rc, cmd))  # type: ignore[arg-type]
                if rc == 0:
                    self.after(200, self._refresh_profile_list)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                self.append_output(f"\nERROR: {exc}\n")
                self.running_proc = None
                cmd = self.current_cmd
                self.after(0, lambda: self.on_done(1, cmd))  # type: ignore[arg-type]

        threading.Thread(target=worker, daemon=True).start()

    def _run_display_toml(self) -> None:
        source = self.active_source.get().strip()
        self.append_output(f"# {source}\n\n")
        try:
            p = Path(source).expanduser()
            if not p.exists():
                self.append_output(f"ERROR: File not found: {p}\n")
                self.after(0, lambda: self._finish_current_command(1))
                return
            self.append_output(p.read_text(encoding="utf-8"))
            self.after(0, lambda: self._finish_current_command(0))
        except OSError as exc:
            self.append_output(f"ERROR: {exc}\n")
            self.after(0, lambda: self._finish_current_command(1))

    def _run_add_identity_site(self) -> None:
        site_var = self.arg_widgets.get("--site")
        url_var = self.arg_widgets.get("--url")
        label_var = self.arg_widgets.get("--label")
        rel_me_var = self.arg_widgets.get("--rel-me")

        source = self.active_source.get().strip()
        chosen_label = _get_string_var(site_var).strip()
        url = _get_string_var(url_var).strip()
        display_label = _get_string_var(label_var).strip()
        rel_me = _get_bool_var(rel_me_var, True)

        site = IDENTITY_SITE_BY_LABEL.get(chosen_label)
        kind = site["kind"] if site else "other"
        if not display_label:
            display_label = chosen_label or kind

        template = site["url_template"] if site else ""
        if not url or (template and url == template):
            self.append_output(
                "ERROR: Please fill in the Profile URL field with your actual profile URL.\n"
                f"Template was: {template}\n"
            )
            self.after(0, lambda: self._finish_current_command(1))
            return

        try:
            p = Path(source).expanduser()
            if not p.exists():
                self.append_output(f"ERROR: File not found: {p}\n")
                self.after(0, lambda: self._finish_current_command(1))
                return

            rel_me_toml = "true" if rel_me else "false"
            new_block = (
                f"\n[[profiles]]\n"
                f'kind = "{kind}"\n'
                f'label = "{display_label}"\n'
                f'url = "{url}"\n'
                f'verification = "self_asserted"\n'
                f"rel_me = {rel_me_toml}\n"
                f'stored_proof = ""\n'
            )
            updated = p.read_text(encoding="utf-8").rstrip() + "\n" + new_block
            p.write_text(updated, encoding="utf-8")

            self.append_output(f"Added [[profiles]] entry to {p}\n\n")
            self.append_output(new_block)
            self.append_output("\nNext step: run 'Update Proofs' to sign this URL and embed the proof.\n")
            self.after(0, lambda: self._finish_current_command(0))
            self.active_source.set(source)
        except OSError as exc:
            self.append_output(f"ERROR: {exc}\n")
            self.after(0, lambda: self._finish_current_command(1))

    def _finish_current_command(self, rc: int) -> None:
        """Complete the active command when one is selected."""
        if self.current_cmd is not None:
            self.on_done(rc, self.current_cmd)

    def on_done(self, rc: int, cmd: GuiCommand) -> None:
        self.stop_btn.config(state=tk.DISABLED)
        if not cmd["readonly"]:
            self.run_btn.config(state=tk.NORMAL)
        msg = f"Exited {rc}"
        self.status_var.set(msg)
        self.status_label.config(fg="#0e7c0e" if rc == 0 else "#7c0e0e")
        self.append_output(f"\n[{msg}]\n")
        self.after(5000, lambda: self.status_var.set(""))
        if rc == 0 and cmd.get("name") in ("init", "import"):
            self.after(200, self._refresh_profile_list)
        if rc == 0 and cmd.get("name") in ("key-rotate", "key-recover", "key-import", "keygen"):
            self.after(200, self._refresh_key_list)
        # Enable Open button for build on success; serve already enables it at launch.
        if self._open_url and cmd.get("name") == "build":
            self.open_btn.config(state=tk.NORMAL)
            if rc == 0:
                self.after(0, self._open_in_browser)

    def _open_in_browser(self) -> None:
        """Open self._open_url in the system default browser."""
        import webbrowser

        if self._open_url:
            webbrowser.open(self._open_url)

    def _resolve_build_output_url(self) -> str:
        """Return a file:// URL for the build output index.html."""
        output_var = self.arg_widgets.get("--output")
        output_str = _get_string_var(output_var).strip()
        if not output_str:
            # Default: ./site/<pypi_username>/
            info = _load_toml_info(self.active_source.get())
            username = info.get("pypi_username", "")
            if username:
                output_str = str(Path("site") / username)
            else:
                output_str = "site"
        index = Path(output_str).expanduser().resolve() / "index.html"
        return index.as_uri()

    def stop_command(self) -> None:
        if self.running_proc is not None:
            with suppress(OSError):
                self.running_proc.terminate()
            self.running_proc = None
        httpd = getattr(self, "_static_httpd", None)
        if httpd is not None:
            with suppress(Exception):
                httpd.shutdown()
            self._static_httpd = None
        self.stop_btn.config(state=tk.DISABLED)
        if self.current_cmd and not self.current_cmd["readonly"]:
            self.run_btn.config(state=tk.NORMAL)
        self.status_var.set("")
        self.status_label.config(fg="#888888")

    def append_output(self, text: str) -> None:
        def do() -> None:
            self.output.insert(tk.END, text)
            self.output.see(tk.END)

        self.after(0, do)


def main() -> None:
    app = PypiProfileGui()
    with contextlib.suppress(KeyboardInterrupt):
        app.mainloop()


if __name__ == "__main__":
    main()
