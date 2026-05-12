"""Fetch external URLs and verify pypi-profile-proof claims."""

from __future__ import annotations

import base64
import binascii
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, cast

from pypi_profile.claims import decode_claim, is_expired
from pypi_profile.models import ClaimStatus, ProfileData, ProfileLink

PROOF_RE = re.compile(
    r"pypi-profile-proof:\s*([A-Za-z0-9_\-]+={0,3})",
    re.IGNORECASE,
)


def _import_minisign() -> Any:
    try:
        import minisign  # type: ignore[import-untyped]

        return minisign
    except ImportError as exc:
        raise ImportError(
            "py-minisign is required for verification. Install it with: uv add py-minisign"
        ) from exc


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
    except (TypeError, ValueError, OSError, binascii.Error):
        return False

    from pypi_profile.signing import _claim_to_bytes

    claim_bytes = _claim_to_bytes(claim)
    try:
        pk.verify(claim_bytes, sig)
        return True
    except (TypeError, ValueError, OSError):
        return False


def _status_from_tokens(
    tokens: list[str],
    *,
    subject_url: str,
    pypi_username: str,
    profile_package: str,
    public_key_b64: str,
) -> ClaimStatus:
    """Return the best verification status from a page's proof tokens."""
    for token_str in tokens:
        try:
            claim = decode_claim(token_str)
        except (TypeError, ValueError):
            continue

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
    except (OSError, ValueError):
        return "unverified"

    return _status_from_tokens(
        find_proof_tokens(text),
        subject_url=link.url,
        pypi_username=pypi_username,
        profile_package=profile_package,
        public_key_b64=public_key_b64,
    )


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
