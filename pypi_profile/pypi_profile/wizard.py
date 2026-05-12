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
def session() -> PromptSession[str]:
    return PromptSession()


def print_styled(msg: str) -> None:
    print_formatted_text(HTML(msg), style=STYLE)


def ask(prompt: str, default: str = "", hint: str = "", validator: Validator | None = None) -> str:
    """Prompt for a single line of text. Returns default if user presses enter."""
    display = prompt
    if default:
        display += f" <hint>[{default}]</hint>"
    if hint:
        display += f" <hint>({hint})</hint>"
    display += ": "
    result = session().prompt(
        HTML(display),
        style=STYLE,
        default=default,
        validator=validator,
        validate_while_typing=False,
    )
    return result.strip()


def ask_with_completer(prompt: str, choices: list[str], default: str = "", hint: str = "") -> str:
    completer = WordCompleter(choices, ignore_case=True)
    display = prompt
    if default:
        display += f" <hint>[{default}]</hint>"
    if hint:
        display += f" <hint>({hint})</hint>"
    display += ": "
    result = session().prompt(HTML(display), style=STYLE, default=default, completer=completer)
    return result.strip()


def ask_bool(prompt: str, default: bool = False) -> bool:
    default_hint = "Y/n" if default else "y/N"
    display = f"{prompt} <hint>[{default_hint}]</hint>: "
    while True:
        result = session().prompt(HTML(display), style=STYLE).strip().lower()
        if not result:
            return default
        if result in ("y", "yes"):
            return True
        if result in ("n", "no"):
            return False
        print_styled("<warn>Please enter y or n.</warn>")


def checkboxlist(title: str, choices: list[tuple[str, str]], defaults: list[str] | None = None) -> list[str]:
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


class NonEmptyValidator(Validator):
    def validate(self, document: Any) -> None:
        if not document.text.strip():
            raise ValidationError(message="This field cannot be empty.")


REQUIRED = NonEmptyValidator()


# ---------------------------------------------------------------------------
# Pre-flight: detect existing data sources
# ---------------------------------------------------------------------------


def find_json_resume() -> Path | None:
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


def load_existing_toml(dest: Path) -> dict[str, Any]:
    """Load an existing pypi_profile.toml if it exists, returning raw dict."""
    if not dest.exists():
        return {}
    with open(dest, "rb") as fh:
        return tomllib.load(fh)


def fetch_pypi_data_silent(username: str) -> list[dict[str, Any]]:
    """Fetch PyPI packages for username with a spinner-style status line."""
    from pypi_profile.importers import fetch_pypi_user_packages

    print_styled(f"<fetched>  Fetching PyPI packages for {username!r} …</fetched>")
    pkgs = fetch_pypi_user_packages(username)
    print_styled(f"<ok>  Found {len(pkgs)} packages on PyPI.</ok>")
    return pkgs


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------


def section_identity(existing: dict[str, Any], prefilled: dict[str, Any]) -> dict[str, Any]:
    print_styled("\n<section>── Identity ──────────────────────────────────────────────────</section>")

    ex_id = existing.get("identity", {})
    pf_id = prefilled.get("identity", {})

    display_name = ask(
        "Your display name",
        default=ex_id.get("display_name") or pf_id.get("display_name") or "",
        validator=REQUIRED,
    )
    legal_name = (
        ask(
            "Legal name",
            default=ex_id.get("legal_name") or pf_id.get("legal_name") or display_name,
            hint="full legal name, optional",
        )
        or display_name
    )
    pypi_username = ask(
        "PyPI username",
        default=ex_id.get("pypi_username") or pf_id.get("pypi_username") or "",
        validator=REQUIRED,
    )
    location = ask(
        "Location",
        default=ex_id.get("location") or pf_id.get("location") or "",
        hint="City, Country",
    )
    timezone = ask(
        "Timezone",
        default=ex_id.get("timezone") or pf_id.get("timezone") or "UTC",
        hint="e.g. America/New_York",
    )
    pronouns = ask(
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


def section_profile_summary(
    existing: dict[str, Any], prefilled: dict[str, Any], identity: dict[str, Any]
) -> dict[str, Any]:
    print_styled("\n<section>── Profile ──────────────────────────────────────────────────</section>")

    ex_prof = existing.get("profile", {})
    pf_prof = prefilled.get("profile", {})

    kind = (
        ask_with_completer(
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
    summary = ask(
        "Short bio / summary",
        default=ex_prof.get("summary") or pf_prof.get("summary") or "",
        hint="one or two sentences",
    )

    return {
        "kind": kind,
        "display_name": identity["display_name"],
        "summary": summary,
    }


def section_social_profiles(
    existing: dict[str, Any], prefilled: dict[str, Any], pypi_username: str
) -> list[dict[str, Any]]:
    print_styled("\n<section>── External Profiles / Links ──────────────────────────────────</section>")

    ex_profiles: list[dict[str, Any]] = existing.get("profiles", [])
    pf_profiles: list[dict[str, Any]] = prefilled.get("profiles", [])

    # Build index keyed by kind
    merged: dict[str, dict[str, Any]] = {}
    for p in ex_profiles + pf_profiles:
        merged[p["kind"]] = p

    # GitHub
    gh_default = merged.get("github", {}).get("url", f"https://github.com/{pypi_username}" if pypi_username else "")
    gh_url = ask("GitHub URL", default=gh_default, hint="leave blank to skip")
    if gh_url:
        merged["github"] = {
            "kind": "github",
            "label": "GitHub",
            "url": gh_url,
            "verification": "self_asserted",
        }

    # GitLab
    gl_default = merged.get("gitlab", {}).get("url", "")
    gl_url = ask("GitLab URL", default=gl_default, hint="optional")
    if gl_url:
        merged["gitlab"] = {
            "kind": "gitlab",
            "label": "GitLab",
            "url": gl_url,
            "verification": "self_asserted",
        }

    # Mastodon
    masto_default = merged.get("mastodon", {}).get("url", "")
    masto_url = ask(
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
    li_url = ask("LinkedIn URL", default=li_default, hint="optional")
    if li_url:
        merged["linkedin"] = {
            "kind": "linkedin",
            "label": "LinkedIn",
            "url": li_url,
            "verification": "self_asserted",
        }

    # Website
    web_default = merged.get("website", {}).get("url", "")
    web_url = ask("Personal website", default=web_default, hint="optional")
    if web_url:
        merged["website"] = {
            "kind": "website",
            "label": "Website",
            "url": web_url,
            "verification": "self_asserted",
        }

    return list(merged.values())


def section_contact(existing: dict[str, Any], prefilled: dict[str, Any]) -> list[dict[str, Any]]:
    print_styled("\n<section>── Contact Methods ──────────────────────────────────────────</section>")

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

    email = ask("Professional email", default=email_default, hint="optional")
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


def section_packages(
    existing: dict[str, Any],
    prefilled: dict[str, Any],
    pypi_username: str,
) -> list[dict[str, Any]]:
    print_styled("\n<section>── PyPI Packages ──────────────────────────────────────────────</section>")

    ex_pkgs: list[dict[str, Any]] = existing.get("packages", [])
    pf_pkgs: list[dict[str, Any]] = prefilled.get("packages", [])

    # Packages from existing TOML take precedence
    known_names = {p["name"] for p in ex_pkgs}

    # Live fetch — only if we don't already have data and user is happy to wait
    live_pkgs: list[dict[str, Any]] = []
    if pypi_username and not ex_pkgs:
        do_fetch = ask_bool(
            f"Fetch your PyPI packages for {pypi_username!r} from PyPI now?",
            default=True,
        )
        if do_fetch:
            live_pkgs = fetch_pypi_data_silent(pypi_username)

    # Merge: existing > live > prefilled (from json-resume, usually empty for packages)
    all_pkgs: list[dict[str, Any]] = ex_pkgs[:]
    for p in live_pkgs + pf_pkgs:
        if p["name"] not in known_names:
            all_pkgs.append(p)
            known_names.add(p["name"])

    if all_pkgs:
        print_styled(f"<ok>  {len(all_pkgs)} package(s) will be included.</ok>")
        for pkg in all_pkgs[:5]:
            print_styled(
                f"    • {pkg['name']}  <hint>({pkg.get('role', 'maintainer')}, {pkg.get('state', 'active')})</hint>"
            )
        if len(all_pkgs) > 5:
            print_styled(f"    … and {len(all_pkgs) - 5} more")
    else:
        print_styled("<hint>  No packages found. You can edit the TOML to add them later.</hint>")
        add_one = ask_bool("Add a placeholder package entry?", default=False)
        if add_one:
            pkg_name = ask("Package name", default="")
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


def section_hiring(existing: dict[str, Any]) -> dict[str, Any]:
    print_styled("\n<section>── Availability / Hiring ─────────────────────────────────────</section>")
    print_styled("<hint>  (These fields appear on your profile page and help employers/clients find you.)</hint>")

    ex_h = existing.get("hiring", {})

    open_since = ask(
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
    selected_et = checkboxlist(
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
    selected_wm = checkboxlist(
        "Work model preferences:",
        model_choices,
        defaults=current_wm,
    )

    jurisdiction_raw = ask(
        "Jurisdiction(s) (comma-separated country codes, e.g. US,CA):",
        default=",".join(ex_h.get("jurisdiction", [])),
    )
    jurisdiction = [j.strip() for j in jurisdiction_raw.split(",") if j.strip()]

    speaking = ask_bool("Open to speaking engagements?", default=ex_h.get("speaking", False))
    sponsorship = ask_bool("Open to sponsorship / donations?", default=ex_h.get("sponsorship", False))

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
    print_styled("")
    print_styled("<header>╔══════════════════════════════════════════════════════════════╗</header>")
    print_styled("<header>║         pypi-profile  —  interactive setup wizard           ║</header>")
    print_styled("<header>╚══════════════════════════════════════════════════════════════╝</header>")
    print_styled("")

    # ── Step 0: load existing data (safe to re-run) ──────────────────────────
    existing: dict[str, Any] = {}
    if dest.exists():
        existing = load_existing_toml(dest)
        print_styled(f"<ok>  Found existing {dest} — pre-filling answers from it.</ok>")
        print_styled("<hint>  Just press Enter to keep existing values.</hint>\n")
    else:
        print_styled(f"<hint>  Will create {dest}</hint>\n")

    # ── Step 1: JSON Resume auto-detect ──────────────────────────────────────
    prefilled: dict[str, Any] = {}

    jr_path_str = from_json_resume
    if not jr_path_str:
        found = find_json_resume()
        if found:
            print_styled(f"<ok>  Found JSON Resume at {found}</ok>")
            use_jr = ask_bool("Import data from it?", default=True)
            if use_jr:
                jr_path_str = str(found)

    if jr_path_str:
        jr_path = Path(jr_path_str)
        if jr_path.exists():
            from pypi_profile.importers import from_json_resume as from_jr

            print_styled(f"<fetched>  Importing {jr_path} …</fetched>")
            prefilled = from_jr(jr_path)
            print_styled("<ok>  JSON Resume imported.</ok>")
        else:
            print_styled(f"<warn>  JSON Resume not found: {jr_path}</warn>")

    # ── Step 2: Ask questions (shortest path) ────────────────────────────────
    identity = section_identity(existing, prefilled)
    profile_sec = section_profile_summary(existing, prefilled, identity)
    social_profiles = section_social_profiles(existing, prefilled, identity["pypi_username"])
    contact_methods = section_contact(existing, prefilled)
    packages = section_packages(existing, prefilled, identity["pypi_username"])
    hiring = section_hiring(existing)

    # ── Step 3: Carry over sections we didn't ask about ──────────────────────
    work_experience = existing.get("work_experience") or prefilled.get("work_experience") or []
    projects = existing.get("projects") or prefilled.get("projects") or []
    contracting = existing.get("contracting") or prefilled.get("contracting") or {}
    succession = existing.get("succession") or {}
    verification = existing.get("verification") or {}
    contact_preferences = existing.get("contact_preferences") or {}
    funding = existing.get("funding") or prefilled.get("funding") or {}

    humans = existing.get("humans") or [
        {
            "id": identity["pypi_username"],
            "display_name": identity["display_name"],
            "role": "Owner",
        }
    ]

    print_styled("")
    print_styled("<ok>✔  All questions answered.</ok>")

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
        "funding": funding,
    }
