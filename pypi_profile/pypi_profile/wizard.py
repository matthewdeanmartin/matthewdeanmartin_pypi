"""Interactive onboarding wizard for pypi-profile using prompt-toolkit."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import checkboxlist_dialog
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import ValidationError, Validator

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

STYLE = Style.from_dict(
    {
        "header": "#ansiblue bold",
        "section": "#ansicyan bold",
        "hint": "#ansigray italic",
        "fetched": "#ansigreen",
        "skip": "#ansiyellow",
        "warn": "#ansiyellow bold",
        "ok": "#ansigreen bold",
    }
)


@lru_cache(maxsize=1)
def _session() -> PromptSession[str]:
    return PromptSession()


def _print(msg: str) -> None:
    print_formatted_text(HTML(msg), style=STYLE)


def _ask(
    prompt: str, default: str = "", hint: str = "", validator: Validator | None = None
) -> str:
    """Prompt for a single line of text. Returns default if user presses enter."""
    display = prompt
    if default:
        display += f" <hint>[{default}]</hint>"
    if hint:
        display += f" <hint>({hint})</hint>"
    display += ": "
    result = _session().prompt(
        HTML(display),
        style=STYLE,
        default=default,
        validator=validator,
        validate_while_typing=False,
    )
    return result.strip()


def _ask_with_completer(
    prompt: str, choices: list[str], default: str = "", hint: str = ""
) -> str:
    completer = WordCompleter(choices, ignore_case=True)
    display = prompt
    if default:
        display += f" <hint>[{default}]</hint>"
    if hint:
        display += f" <hint>({hint})</hint>"
    display += ": "
    result = _session().prompt(
        HTML(display), style=STYLE, default=default, completer=completer
    )
    return result.strip()


def _ask_bool(prompt: str, default: bool = False) -> bool:
    default_hint = "Y/n" if default else "y/N"
    display = f"{prompt} <hint>[{default_hint}]</hint>: "
    while True:
        result = _session().prompt(HTML(display), style=STYLE).strip().lower()
        if not result:
            return default
        if result in ("y", "yes"):
            return True
        if result in ("n", "no"):
            return False
        _print("<warn>Please enter y or n.</warn>")


def _checkboxlist(
    title: str, choices: list[tuple[str, str]], defaults: list[str] | None = None
) -> list[str]:
    """Show a checkbox list dialog."""
    if not sys.stdout.isatty():
        return defaults or []
    defaults_set = set(defaults or [])
    values = [(v, HTML(f"  {label}")) for v, label in choices]
    result = checkboxlist_dialog(
        title=title,
        values=values,
        default_values=[v for v, _ in values if v in defaults_set],
        style=STYLE,
    ).run()
    return result or []


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


class _NonEmptyValidator(Validator):
    def validate(self, document: Any) -> None:
        if not document.text.strip():
            raise ValidationError(message="This field cannot be empty.")


_REQUIRED = _NonEmptyValidator()


# ---------------------------------------------------------------------------
# Pre-flight: detect existing data sources
# ---------------------------------------------------------------------------


def _find_json_resume() -> Path | None:
    """Search common locations for a JSON Resume file."""
    candidates = [
        Path.cwd() / "resume.json",
        Path.home() / "resume.json",
        Path.cwd() / "cv.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _load_existing_toml(dest: Path) -> dict[str, Any]:
    """Load an existing pypi_profile.toml if it exists, returning raw dict."""
    if not dest.exists():
        return {}
    with open(dest, "rb") as fh:
        return tomllib.load(fh)


def _fetch_pypi_data_silent(username: str) -> list[dict[str, Any]]:
    """Fetch PyPI packages for username with a spinner-style status line."""
    from pypi_profile.importers import _fetch_pypi_user_packages

    _print(f"<fetched>  Fetching PyPI packages for {username!r} …</fetched>")
    pkgs = _fetch_pypi_user_packages(username)
    _print(f"<ok>  Found {len(pkgs)} packages on PyPI.</ok>")
    return pkgs


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------


def _section_identity(
    existing: dict[str, Any], prefilled: dict[str, Any]
) -> dict[str, Any]:
    _print(
        "\n<section>── Identity ──────────────────────────────────────────────────</section>"
    )

    ex_id = existing.get("identity", {})
    pf_id = prefilled.get("identity", {})

    display_name = _ask(
        "Your display name",
        default=ex_id.get("display_name") or pf_id.get("display_name") or "",
        validator=_REQUIRED,
    )
    legal_name = (
        _ask(
            "Legal name",
            default=ex_id.get("legal_name") or pf_id.get("legal_name") or display_name,
            hint="full legal name, optional",
        )
        or display_name
    )
    pypi_username = _ask(
        "PyPI username",
        default=ex_id.get("pypi_username") or pf_id.get("pypi_username") or "",
        validator=_REQUIRED,
    )
    location = _ask(
        "Location",
        default=ex_id.get("location") or pf_id.get("location") or "",
        hint="City, Country",
    )
    timezone = _ask(
        "Timezone",
        default=ex_id.get("timezone") or pf_id.get("timezone") or "UTC",
        hint="e.g. America/New_York",
    )
    pronouns = _ask(
        "Pronouns",
        default=ex_id.get("pronouns") or pf_id.get("pronouns") or "",
        hint="optional, e.g. he/him",
    )

    return {
        "display_name": display_name,
        "legal_name": legal_name,
        "pypi_username": pypi_username,
        "location": location,
        "timezone": timezone or "UTC",
        "pronouns": pronouns,
    }


def _section_profile_summary(
    existing: dict[str, Any], prefilled: dict[str, Any], identity: dict[str, Any]
) -> dict[str, Any]:
    _print(
        "\n<section>── Profile ──────────────────────────────────────────────────</section>"
    )

    ex_prof = existing.get("profile", {})
    pf_prof = prefilled.get("profile", {})

    kind = (
        _ask_with_completer(
            "Profile kind",
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
            default=ex_prof.get("kind") or pf_prof.get("kind") or "individual",
            hint="tab to see choices",
        )
        or "individual"
    )
    summary = _ask(
        "Short bio / summary",
        default=ex_prof.get("summary") or pf_prof.get("summary") or "",
        hint="one or two sentences",
    )

    return {
        "kind": kind,
        "display_name": identity["display_name"],
        "summary": summary,
    }


def _section_social_profiles(
    existing: dict[str, Any], prefilled: dict[str, Any], pypi_username: str
) -> list[dict[str, Any]]:
    _print(
        "\n<section>── External Profiles / Links ──────────────────────────────────</section>"
    )

    ex_profiles: list[dict[str, Any]] = existing.get("profiles", [])
    pf_profiles: list[dict[str, Any]] = prefilled.get("profiles", [])

    # Build index keyed by kind
    merged: dict[str, dict[str, Any]] = {}
    for p in ex_profiles + pf_profiles:
        merged[p["kind"]] = p

    # GitHub
    gh_default = merged.get("github", {}).get(
        "url", f"https://github.com/{pypi_username}" if pypi_username else ""
    )
    gh_url = _ask("GitHub URL", default=gh_default, hint="leave blank to skip")
    if gh_url:
        merged["github"] = {
            "kind": "github",
            "label": "GitHub",
            "url": gh_url,
            "verification": "self_asserted",
        }

    # GitLab
    gl_default = merged.get("gitlab", {}).get("url", "")
    gl_url = _ask("GitLab URL", default=gl_default, hint="optional")
    if gl_url:
        merged["gitlab"] = {
            "kind": "gitlab",
            "label": "GitLab",
            "url": gl_url,
            "verification": "self_asserted",
        }

    # Mastodon
    masto_default = merged.get("mastodon", {}).get("url", "")
    masto_url = _ask(
        "Mastodon URL",
        default=masto_default,
        hint="e.g. https://fosstodon.org/@you, optional",
    )
    if masto_url:
        merged["mastodon"] = {
            "kind": "mastodon",
            "label": "Mastodon",
            "url": masto_url,
            "verification": "self_asserted",
        }

    # LinkedIn
    li_default = merged.get("linkedin", {}).get("url", "")
    li_url = _ask("LinkedIn URL", default=li_default, hint="optional")
    if li_url:
        merged["linkedin"] = {
            "kind": "linkedin",
            "label": "LinkedIn",
            "url": li_url,
            "verification": "self_asserted",
        }

    # Website
    web_default = merged.get("website", {}).get("url", "")
    web_url = _ask("Personal website", default=web_default, hint="optional")
    if web_url:
        merged["website"] = {
            "kind": "website",
            "label": "Website",
            "url": web_url,
            "verification": "self_asserted",
        }

    return list(merged.values())


def _section_contact(
    existing: dict[str, Any], prefilled: dict[str, Any]
) -> list[dict[str, Any]]:
    _print(
        "\n<section>── Contact Methods ──────────────────────────────────────────</section>"
    )

    ex_cm: list[dict[str, Any]] = existing.get("contact_methods", [])
    pf_cm: list[dict[str, Any]] = prefilled.get("contact_methods", [])

    # merge by kind+value
    merged: dict[str, dict[str, Any]] = {}
    for c in ex_cm + pf_cm:
        merged[c.get("kind", "") + ":" + c.get("value", "")] = c

    email_default = ""
    for c in merged.values():
        if c.get("kind") == "email":
            email_default = c.get("value", "")
            break

    email = _ask("Professional email", default=email_default, hint="optional")
    if email:
        key = "email:" + email
        merged[key] = {
            "kind": "email",
            "label": "Professional email",
            "value": email,
            "audience": ["hiring", "consulting", "security"],
            "visibility": "public",
        }

    return list(merged.values())


def _section_packages(
    existing: dict[str, Any],
    prefilled: dict[str, Any],
    pypi_username: str,
) -> list[dict[str, Any]]:
    _print(
        "\n<section>── PyPI Packages ──────────────────────────────────────────────</section>"
    )

    ex_pkgs: list[dict[str, Any]] = existing.get("packages", [])
    pf_pkgs: list[dict[str, Any]] = prefilled.get("packages", [])

    # Packages from existing TOML take precedence
    known_names = {p["name"] for p in ex_pkgs}

    # Live fetch — only if we don't already have data and user is happy to wait
    live_pkgs: list[dict[str, Any]] = []
    if pypi_username and not ex_pkgs:
        do_fetch = _ask_bool(
            f"Fetch your PyPI packages for {pypi_username!r} from PyPI now?",
            default=True,
        )
        if do_fetch:
            live_pkgs = _fetch_pypi_data_silent(pypi_username)

    # Merge: existing > live > prefilled (from json-resume, usually empty for packages)
    all_pkgs: list[dict[str, Any]] = ex_pkgs[:]
    for p in live_pkgs + pf_pkgs:
        if p["name"] not in known_names:
            all_pkgs.append(p)
            known_names.add(p["name"])

    if all_pkgs:
        _print(f"<ok>  {len(all_pkgs)} package(s) will be included.</ok>")
        for pkg in all_pkgs[:5]:
            _print(
                f"    • {pkg['name']}  <hint>({pkg.get('role', 'maintainer')}, {pkg.get('state', 'active')})</hint>"
            )
        if len(all_pkgs) > 5:
            _print(f"    … and {len(all_pkgs) - 5} more")
    else:
        _print(
            "<hint>  No packages found. You can edit the TOML to add them later.</hint>"
        )
        add_one = _ask_bool("Add a placeholder package entry?", default=False)
        if add_one:
            pkg_name = _ask("Package name", default="")
            if pkg_name:
                all_pkgs = [
                    {
                        "name": pkg_name,
                        "role": "maintainer",
                        "state": "active",
                        "summary": "",
                        "url": f"https://pypi.org/project/{pkg_name}/",
                    }
                ]

    return all_pkgs


def _section_hiring(existing: dict[str, Any]) -> dict[str, Any]:
    _print(
        "\n<section>── Availability / Hiring ─────────────────────────────────────</section>"
    )
    _print(
        "<hint>  (These fields appear on your profile page and help employers/clients find you.)</hint>"
    )

    ex_h = existing.get("hiring", {})

    open_since = _ask(
        "Open to work since (YYYY-MM-DD, leave blank if not looking):",
        default=ex_h.get("open_to_work_since", ""),
    )

    employment_choices = [
        ("employment", "Full-time employment"),
        ("contracting", "Contracting"),
        ("consulting", "Consulting"),
        ("freelance", "Freelance"),
    ]
    current_et = ex_h.get("employment_types", [])
    selected_et = _checkboxlist(
        "Employment types (space to toggle, enter to confirm):",
        employment_choices,
        defaults=current_et,
    )

    model_choices = [
        ("remote", "Remote"),
        ("hybrid", "Hybrid"),
        ("onsite", "On-site"),
    ]
    current_wm = ex_h.get("work_model", [])
    selected_wm = _checkboxlist(
        "Work model preferences:",
        model_choices,
        defaults=current_wm,
    )

    jurisdiction_raw = _ask(
        "Jurisdiction(s) (comma-separated country codes, e.g. US,CA):",
        default=",".join(ex_h.get("jurisdiction", [])),
    )
    jurisdiction = [j.strip() for j in jurisdiction_raw.split(",") if j.strip()]

    speaking = _ask_bool(
        "Open to speaking engagements?", default=ex_h.get("speaking", False)
    )
    sponsorship = _ask_bool(
        "Open to sponsorship / donations?", default=ex_h.get("sponsorship", False)
    )

    return {
        "open_to_work_since": open_since,
        "employment_types": selected_et,
        "work_model": selected_wm,
        "jurisdiction": jurisdiction,
        "speaking": speaking,
        "sponsorship": sponsorship,
    }


# ---------------------------------------------------------------------------
# Main wizard entry point
# ---------------------------------------------------------------------------


def run_wizard(dest: Path, from_json_resume: str = "") -> dict[str, Any]:
    """Run the interactive init wizard and return the merged data dict."""
    _print("")
    _print(
        "<header>╔══════════════════════════════════════════════════════════════╗</header>"
    )
    _print(
        "<header>║         pypi-profile  —  interactive setup wizard           ║</header>"
    )
    _print(
        "<header>╚══════════════════════════════════════════════════════════════╝</header>"
    )
    _print("")

    # ── Step 0: load existing data (safe to re-run) ──────────────────────────
    existing: dict[str, Any] = {}
    if dest.exists():
        existing = _load_existing_toml(dest)
        _print(f"<ok>  Found existing {dest} — pre-filling answers from it.</ok>")
        _print("<hint>  Just press Enter to keep existing values.</hint>\n")
    else:
        _print(f"<hint>  Will create {dest}</hint>\n")

    # ── Step 1: JSON Resume auto-detect ──────────────────────────────────────
    prefilled: dict[str, Any] = {}

    jr_path_str = from_json_resume
    if not jr_path_str:
        found = _find_json_resume()
        if found:
            _print(f"<ok>  Found JSON Resume at {found}</ok>")
            use_jr = _ask_bool("Import data from it?", default=True)
            if use_jr:
                jr_path_str = str(found)

    if jr_path_str:
        jr_path = Path(jr_path_str)
        if jr_path.exists():
            from pypi_profile.importers import from_json_resume as _from_jr

            _print(f"<fetched>  Importing {jr_path} …</fetched>")
            prefilled = _from_jr(jr_path)
            _print("<ok>  JSON Resume imported.</ok>")
        else:
            _print(f"<warn>  JSON Resume not found: {jr_path}</warn>")

    # ── Step 2: Ask questions (shortest path) ────────────────────────────────
    identity = _section_identity(existing, prefilled)
    profile_sec = _section_profile_summary(existing, prefilled, identity)
    social_profiles = _section_social_profiles(
        existing, prefilled, identity["pypi_username"]
    )
    contact_methods = _section_contact(existing, prefilled)
    packages = _section_packages(existing, prefilled, identity["pypi_username"])
    hiring = _section_hiring(existing)

    # ── Step 3: Carry over sections we didn't ask about ──────────────────────
    work_experience = (
        existing.get("work_experience") or prefilled.get("work_experience") or []
    )
    projects = existing.get("projects") or prefilled.get("projects") or []
    contracting = existing.get("contracting") or prefilled.get("contracting") or {}
    succession = existing.get("succession") or {}
    verification = existing.get("verification") or {}
    contact_preferences = existing.get("contact_preferences") or {}
    funding = existing.get("_funding") or prefilled.get("_funding") or {}

    humans = existing.get("humans") or [
        {
            "id": identity["pypi_username"],
            "display_name": identity["display_name"],
            "role": "Owner",
        }
    ]

    _print("")
    _print("<ok>✔  All questions answered.</ok>")

    return {
        "profile": profile_sec,
        "identity": identity,
        "humans": humans,
        "profiles": social_profiles,
        "contact_methods": contact_methods,
        "packages": packages,
        "projects": projects,
        "work_experience": work_experience,
        "hiring": hiring,
        "contracting": contracting,
        "succession": succession,
        "verification": verification,
        "contact_preferences": contact_preferences,
        "_funding": funding,
    }
