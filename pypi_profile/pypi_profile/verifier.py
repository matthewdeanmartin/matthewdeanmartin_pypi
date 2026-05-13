"""Fetch external URLs and verify pypi-profile-proof claims."""

from __future__ import annotations

import base64
import binascii
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, cast

from pypi_profile.claims import decode_claim, is_compact_claim, is_expired
from pypi_profile.models import ClaimStatus, ProfileData, ProfileLink

logger = logging.getLogger(__name__)

PROOF_RE = re.compile(
    r"pypi-profile-proof:\s*([A-Za-z0-9_\-]+={0,3})",
    re.IGNORECASE,
)

# Domains that actively block scrapers — we skip fetch-based verification and log at DEBUG.
SCRAPER_HOSTILE_DOMAINS = frozenset(
    [
        "linkedin.com",
        "www.linkedin.com",
        "twitter.com",
        "x.com",
        "www.twitter.com",
        "www.x.com",
        "instagram.com",
        "www.instagram.com",
        "facebook.com",
        "www.facebook.com",
    ]
)


def import_minisign() -> Any:
    try:
        import minisign  # type: ignore[import-untyped]

        return minisign
    except ImportError as exc:
        logger.debug("py-minisign not installed; verification unavailable")
        raise ImportError("py-minisign is required for verification. Install it with: uv add py-minisign") from exc


def fetch_page(url: str) -> str:
    """Return the text content of a URL."""
    parsed_url = urllib.parse.urlsplit(url)
    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}")

    try:
        import httpx

        resp = httpx.get(url, follow_redirects=True, timeout=15)
        resp.raise_for_status()
        return str(resp.text)
    except ImportError:
        try:
            # Only HTTP(S) URLs are allowed above.
            with urllib.request.urlopen(url, timeout=15) as r:  # nosec B310
                return cast(bytes, r.read()).decode(errors="replace")
        except urllib.error.URLError as exc:
            raise OSError(str(exc)) from exc
    except httpx.HTTPError as exc:
        raise OSError(str(exc)) from exc


def find_proof_tokens(text: str) -> list[str]:
    """Extract all pypi-profile-proof tokens from a page."""
    return [m.group(0) for m in PROOF_RE.finditer(text)]


def verify_claim_signature(claim: dict[str, Any], public_key_b64: str) -> bool:
    """Verify the Ed25519 signature on a decoded claim dict.

    Handles both claim formats:
    - Full: ``signature`` field holds standard-base64 of 74-byte minisign binary
      (2-byte algo + 8-byte key_id + 64-byte Ed25519 sig).
    - Compact: ``g`` field holds base64url of the raw 64-byte Ed25519 sig only.

    Returns True if the signature is valid.
    """
    import hashlib

    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        pk_full = base64.standard_b64decode(public_key_b64)
        if len(pk_full) != 42:
            logger.debug("Unexpected public key length: %d", len(pk_full))
            return False
        raw_pk = pk_full[10:]
    except (TypeError, ValueError, binascii.Error):
        logger.debug("Failed to parse public key", exc_info=True)
        return False

    if is_compact_claim(claim):
        sig_b64url = claim.get("g", "")
        if not sig_b64url:
            return False
        try:
            padding = (4 - len(sig_b64url) % 4) % 4
            raw_sig = base64.urlsafe_b64decode(sig_b64url + "=" * padding)
            if len(raw_sig) != 64:
                logger.debug("Unexpected compact sig length: %d", len(raw_sig))
                return False
        except (TypeError, ValueError, binascii.Error):
            logger.debug("Failed to decode compact signature", exc_info=True)
            return False
    else:
        sig_b64 = claim.get("signature", "")
        if not sig_b64:
            return False
        try:
            sig_full = base64.standard_b64decode(sig_b64)
            if len(sig_full) != 74:
                logger.debug("Unexpected full sig length: %d", len(sig_full))
                return False
            raw_sig = sig_full[10:]
        except (TypeError, ValueError, binascii.Error):
            logger.debug("Failed to decode full signature", exc_info=True)
            return False

    from pypi_profile.signing import claim_to_bytes

    claim_bytes = claim_to_bytes(claim)
    msg_hash = hashlib.blake2b(claim_bytes, digest_size=64).digest()
    try:
        ed_pk = Ed25519PublicKey.from_public_bytes(raw_pk)
        ed_pk.verify(raw_sig, msg_hash)
        return True
    except (InvalidSignature, ValueError):
        logger.debug("Claim signature verification failed", exc_info=True)
        return False


def status_from_tokens(
    tokens: list[str],
    *,
    subject_url: str,
    pypi_username: str,
    profile_package: str,
    public_key_b64: str,
) -> ClaimStatus:
    """Return the best verification status from a page's proof tokens.

    Handles both full and compact claim formats.
    """
    for token_str in tokens:
        try:
            claim = decode_claim(token_str)
        except (TypeError, ValueError):
            logger.debug("Could not decode proof token; skipping", exc_info=True)
            continue

        if is_compact_claim(claim):
            if claim.get("s") != subject_url:
                continue
            if claim.get("u") != pypi_username:
                continue
            if claim.get("p") != profile_package:
                continue
        else:
            if claim.get("subject") != subject_url:
                continue
            if claim.get("pypi_username") != pypi_username:
                continue
            if claim.get("profile_package") != profile_package:
                continue

        if is_expired(claim):
            return "expired"
        if verify_claim_signature(claim, public_key_b64):
            return "verified"
        return "invalid"

    return "unverified"


def diagnose_tokens(
    tokens: list[str],
    *,
    subject_url: str,
    pypi_username: str,
    profile_package: str,
    public_key_b64: str,
) -> tuple[ClaimStatus, list[str]]:
    """Like status_from_tokens but also returns a list of diagnostic strings.

    Returns (status, [step1, step2, ...]) where the steps describe what was
    found and why verification succeeded or failed.
    """
    steps: list[str] = []

    if not tokens:
        steps.append("No pypi-profile-proof tokens found on page.")
        steps.append("Paste the proof string from 'Add proof-of-control' into the target page.")
        return "unverified", steps

    steps.append(f"Found {len(tokens)} proof token(s) on page.")

    for i, token_str in enumerate(tokens, 1):
        try:
            claim = decode_claim(token_str)
        except (TypeError, ValueError) as exc:
            steps.append(f"Token {i}: could not decode — {exc}")
            continue

        compact = is_compact_claim(claim)
        fmt = "compact" if compact else "full"
        claim_subject = claim.get("s") if compact else claim.get("subject")
        claim_username = claim.get("u") if compact else claim.get("pypi_username")
        claim_package = claim.get("p") if compact else claim.get("profile_package")

        steps.append(f"Token {i} ({fmt} format): subject={claim_subject!r}")

        if claim_subject != subject_url:
            steps.append(f"  ↳ Subject mismatch: expected {subject_url!r}")
            continue
        if claim_username != pypi_username:
            steps.append(f"  ↳ Username mismatch: token has {claim_username!r}, expected {pypi_username!r}")
            continue
        if claim_package != profile_package:
            steps.append(f"  ↳ Package mismatch: token has {claim_package!r}, expected {profile_package!r}")
            continue

        steps.append("  ↳ Subject, username, and package match.")

        if is_expired(claim):
            exp = claim.get("expires_at") or claim.get("e")
            steps.append(f"  ↳ Claim expired (expires_at: {exp}). Re-run: pypi-profile update-proofs <source>")
            return "expired", steps

        if not public_key_b64:
            steps.append("  ↳ No public_key in [verification] — cannot verify signature.")
            steps.append("    Run: pypi-profile keygen  and add the public key to your TOML.")
            return "unverified", steps

        # Check signature format
        if compact:
            sig_raw = claim.get("g", "")
            if not sig_raw:
                steps.append("  ↳ Compact claim has no 'g' signature field.")
                return "invalid", steps
            try:
                padding = (4 - len(sig_raw) % 4) % 4
                sig_bytes = base64.urlsafe_b64decode(sig_raw + "=" * padding)
                steps.append(f"  ↳ Compact signature: {len(sig_bytes)} bytes (expected 64).")
                if len(sig_bytes) != 64:
                    steps.append(
                        f"  ↳ Wrong length ({len(sig_bytes)}). Token was probably signed with an old format."
                        " Re-run: pypi-profile update-proofs <source>"
                    )
                    return "invalid", steps
            except Exception as exc:
                steps.append(f"  ↳ Could not decode compact signature: {exc}")
                return "invalid", steps
        else:
            sig_raw = claim.get("signature", "")
            if not sig_raw:
                steps.append("  ↳ Full claim has no 'signature' field.")
                return "invalid", steps
            try:
                sig_bytes = base64.standard_b64decode(sig_raw)
                steps.append(f"  ↳ Full signature: {len(sig_bytes)} bytes (expected 74).")
                if len(sig_bytes) != 74:
                    steps.append(
                        f"  ↳ Wrong length ({len(sig_bytes)} bytes). "
                        "Token was probably signed with an old armored format."
                        " Re-run: pypi-profile update-proofs <source>"
                    )
                    return "invalid", steps
            except Exception as exc:
                steps.append(f"  ↳ Could not decode signature: {exc}")
                return "invalid", steps

        # Check public key length (informational only — verify_claim_signature does the real check)
        try:
            pk_bytes = base64.standard_b64decode(public_key_b64)
            steps.append(f"  ↳ Public key: {len(pk_bytes)} bytes (expected 42).")
            if len(pk_bytes) != 42:
                steps.append(
                    f"  ↳ Public key wrong length ({len(pk_bytes)}). "
                    "Check public_key in [verification] is a minisign .pub value."
                )
                return "invalid", steps
        except Exception as exc:
            steps.append(f"  ↳ Could not decode public key: {exc}")
            return "invalid", steps

        # Delegate to verify_claim_signature so mocks work in tests and logic stays in one place.
        steps.append("  ↳ Verifying Ed25519 signature...")
        if verify_claim_signature(claim, public_key_b64):
            steps.append("  ↳ Signature valid. ✓")
            return "verified", steps
        else:
            steps.append("  ↳ Signature INVALID — does not verify against public key.")
            steps.append("    Check that public_key in [verification] matches the key used to sign.")
            steps.append("    If you regenerated your keypair, re-run: pypi-profile update-proofs <source>")
            return "invalid", steps

    steps.append(f"No token matched subject={subject_url!r} / username={pypi_username!r} / package={profile_package!r}.")
    return "unverified", steps


_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def _extract_urls_from_field(value: str) -> list[str]:
    """Extract all href URLs from a Mastodon field value (which may be HTML)."""
    hrefs = _HREF_RE.findall(value)
    return hrefs if hrefs else [value]


def verify_mastodon_link(
    link: ProfileLink,
    profile_package: str,
    public_key_b64: str = "",
    pypi_username: str = "",
) -> ClaimStatus:
    """Verify a Mastodon profile using the Mastodon API rel-me link check."""
    status, _ = diagnose_mastodon_link(link, profile_package, public_key_b64, pypi_username)
    return status


def diagnose_mastodon_link(
    link: ProfileLink,
    profile_package: str,
    public_key_b64: str = "",
    pypi_username: str = "",
) -> tuple[ClaimStatus, list[str]]:
    """Verify a Mastodon profile via the API and return (status, diagnostic steps).

    Two verification paths, tried in order:
    1. Mastodon-verified rel-me link: a profile field whose href contains
       ``pypi.org/project/<profile_package>`` or ``pypi.org/user/<pypi_username>``
       and has a non-null ``verified_at``.
    2. Proof-token fallback: fetch the profile page and look for a
       pypi-profile-proof token signed with the account's key.
    """
    import json as _json

    steps: list[str] = []

    m = re.match(r"https?://([^/]+)/@([^/]+)", link.url)
    if not m:
        steps.append(f"URL {link.url!r} does not look like a Mastodon profile URL (expected https://instance/@user).")
        return "unverified", steps

    instance, username = m.group(1), m.group(2)
    api_url = f"https://{instance}/api/v1/accounts/lookup?acct={username}"
    steps.append(f"Fetching Mastodon account via API: {api_url}")

    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "pypi-profile/0.1"})
        with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
            data = _json.loads(r.read().decode())
    except (OSError, ValueError, urllib.error.URLError) as exc:
        steps.append(f"Could not reach Mastodon API: {exc}")
        return "unverified", steps

    fields = data.get("fields", [])
    steps.append(f"Account has {len(fields)} profile field(s).")

    # Patterns that count as a verified PyPI identity link.
    # pypi.org/project/<package> is canonical; pypi.org/user/<username> also accepted.
    identity_patterns: list[str] = [f"pypi.org/project/{profile_package}"]
    if pypi_username:
        identity_patterns.append(f"pypi.org/user/{pypi_username}")

    for field in fields:
        name = field.get("name", "")
        raw_value = field.get("value", "")
        verified_at = field.get("verified_at")
        # Mastodon wraps values in HTML; extract href URLs for matching.
        field_urls = _extract_urls_from_field(raw_value)
        field_urls_str = ", ".join(field_urls)
        steps.append(f"  Field {name!r}: urls={field_urls_str}  verified_at={verified_at!r}")

        for pattern in identity_patterns:
            if any(pattern in u for u in field_urls):
                if verified_at:
                    steps.append(f"  -> Contains {pattern!r} and is Mastodon-verified. ✓")
                    return "verified", steps
                else:
                    steps.append(f"  -> Contains {pattern!r} but NOT yet verified by Mastodon.")
                    steps.append("     Mastodon verifies links by checking for a rel='me' backlink.")
                    steps.append("     pypi.org/user/<name> pages don't carry rel='me', so this won't auto-verify.")
                    steps.append("     Use proof-token verification instead (see 'Add proof-of-control' below).")

    steps.append(f"No Mastodon-verified field matching any of {identity_patterns} found.")
    steps.append("Falling back to proof-token check on the profile page...")

    try:
        text = fetch_page(link.url)
    except (OSError, ValueError) as exc:
        steps.append(f"Could not fetch {link.url}: {exc}")
        return "unverified", steps

    tokens = find_proof_tokens(text)
    steps.append(f"Found {len(tokens)} proof token(s) on Mastodon profile page.")

    if not tokens:
        steps.append("Paste your compact proof string into the Mastodon post bio or a pinned post.")
        return "unverified", steps

    if not public_key_b64:
        steps.append("No public_key in [verification] — cannot verify proof token signature.")
        return "unverified", steps

    status, token_steps = diagnose_tokens(
        tokens,
        subject_url=link.url,
        pypi_username=pypi_username,
        profile_package=profile_package,
        public_key_b64=public_key_b64,
    )
    steps.extend(token_steps)
    return status, steps


def verify_profile_link(
    link: ProfileLink,
    public_key_b64: str,
    profile_package: str,
    pypi_username: str,
) -> ClaimStatus:
    """Fetch a profile URL and attempt to verify a proof-of-control claim."""
    status, _ = diagnose_profile_link(link, public_key_b64, profile_package, pypi_username)
    return status


def diagnose_profile_link(
    link: ProfileLink,
    public_key_b64: str,
    profile_package: str,
    pypi_username: str,
) -> tuple[ClaimStatus, list[str]]:
    """Like verify_profile_link but also returns a list of diagnostic step strings."""
    steps: list[str] = []
    hostname = urllib.parse.urlsplit(link.url).hostname or ""

    if hostname in SCRAPER_HOSTILE_DOMAINS:
        steps.append(f"{hostname} actively blocks automated requests — live verification is not possible.")
        steps.append("Self-assertion is the only available option for this platform.")
        return "unverified", steps

    if link.kind == "mastodon":
        return diagnose_mastodon_link(link, profile_package, public_key_b64, pypi_username)

    if not public_key_b64:
        steps.append("No public_key in [verification] — cannot verify any signatures.")
        steps.append("Run: pypi-profile keygen  then add the public key to your TOML.")
        return "unverified", steps

    steps.append(f"Fetching {link.url} ...")
    try:
        text = fetch_page(link.url)
    except (OSError, ValueError) as exc:
        steps.append(f"Failed to fetch page: {exc}")
        return "unverified", steps

    tokens = find_proof_tokens(text)
    status, token_steps = diagnose_tokens(
        tokens,
        subject_url=link.url,
        pypi_username=pypi_username,
        profile_package=profile_package,
        public_key_b64=public_key_b64,
    )
    steps.extend(token_steps)
    return status, steps


def verify_all_profiles(
    profile: ProfileData,
    profile_package: str,
) -> list[dict[str, Any]]:
    """Check all [[profiles]] entries and return verification results.

    Each result dict has keys: kind, label, url, status.
    """
    public_key_b64 = profile.verification.public_key
    pypi_username = profile.identity.pypi_username

    logger.debug("Verifying %d profile link(s) for %r", len(profile.profiles), pypi_username)
    results = []
    for link in profile.profiles:
        status: ClaimStatus = verify_profile_link(
            link,
            public_key_b64=public_key_b64,
            profile_package=profile_package,
            pypi_username=pypi_username,
        )
        logger.debug("Link %s -> status=%s", link.url, status)
        results.append(
            {
                "kind": link.kind,
                "label": link.label,
                "url": link.url,
                "status": status,
            }
        )
    return results


def diagnose_all_profiles(
    profile: ProfileData,
    profile_package: str,
) -> list[dict[str, Any]]:
    """Like verify_all_profiles but each result also includes a ``detail`` list of diagnostic strings."""
    public_key_b64 = profile.verification.public_key
    pypi_username = profile.identity.pypi_username

    results = []
    for link in profile.profiles:
        status, steps = diagnose_profile_link(
            link,
            public_key_b64=public_key_b64,
            profile_package=profile_package,
            pypi_username=pypi_username,
        )
        results.append(
            {
                "kind": link.kind,
                "label": link.label,
                "url": link.url,
                "status": status,
                "detail": steps,
            }
        )
    return results
