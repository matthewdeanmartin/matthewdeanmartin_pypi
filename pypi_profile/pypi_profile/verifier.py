"""Fetch external URLs and verify pypi-profile-proof claims."""

from __future__ import annotations

import base64
import re
from typing import Any

from pypi_profile.claims import PROOF_PREFIX, decode_claim, is_expired
from pypi_profile.models import ClaimStatus, ProfileData, ProfileLink

PROOF_RE = re.compile(
    r"pypi-profile-proof:\s*([A-Za-z0-9_\-]+={0,3})",
    re.IGNORECASE,
)


def _import_minisign() -> Any:
    try:
        import minisign

        return minisign
    except ImportError as exc:
        raise ImportError(
            "py-minisign is required for verification. Install it with: uv add py-minisign"
        ) from exc


def fetch_page(url: str) -> str:
    """Return the text content of a URL."""
    try:
        import httpx

        resp = httpx.get(url, follow_redirects=True, timeout=15)
        resp.raise_for_status()
        return resp.text
    except ImportError:
        import urllib.request

        with urllib.request.urlopen(url, timeout=15) as r:  # noqa: S310
            return r.read().decode(errors="replace")


def find_proof_tokens(text: str) -> list[str]:
    """Extract all pypi-profile-proof tokens from a page."""
    return [m.group(0) for m in PROOF_RE.finditer(text)]


def verify_claim_signature(claim: dict[str, Any], public_key_b64: str) -> bool:
    """Verify the minisign signature on a decoded claim dict.

    Returns True if valid, False otherwise.
    """
    ms = _import_minisign()

    sig_b64 = claim.get("signature", "")
    if not sig_b64:
        return False

    try:
        pk = ms.PublicKey.from_base64(public_key_b64)
        sig = ms.Signature.from_bytes(base64.standard_b64decode(sig_b64))
    except Exception:
        return False

    from pypi_profile.signing import _claim_to_bytes

    claim_bytes = _claim_to_bytes(claim)
    try:
        pk.verify(claim_bytes, sig)
        return True
    except Exception:
        return False


def verify_profile_link(
    link: ProfileLink,
    public_key_b64: str,
    profile_package: str,
    pypi_username: str,
) -> ClaimStatus:
    """Fetch a profile URL and attempt to verify a proof-of-control claim.

    Returns a ClaimStatus string.
    """
    if not public_key_b64:
        return "unverified"

    try:
        text = fetch_page(link.url)
    except Exception:
        return "unverified"

    tokens = find_proof_tokens(text)
    if not tokens:
        return "unverified"

    for token_str in tokens:
        try:
            claim = decode_claim(token_str)
        except Exception:
            continue

        if claim.get("subject") != link.url:
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


def verify_all_profiles(
    profile: ProfileData,
    profile_package: str,
) -> list[dict[str, Any]]:
    """Check all [[profiles]] entries and return verification results.

    Each result dict has keys: kind, label, url, status.
    """
    public_key_b64 = profile.verification.public_key
    pypi_username = profile.identity.pypi_username

    results = []
    for link in profile.profiles:
        status: ClaimStatus = verify_profile_link(
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
            }
        )
    return results
