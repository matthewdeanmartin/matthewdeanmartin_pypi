"""Build and encode signed claims for pypi-profile proof-of-control."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from pypi_profile.serialization import json_dumps_bytes, json_loads

logger = logging.getLogger(__name__)

PROOF_PREFIX = "pypi-profile-proof:"
TINY_PREFIX = "t:"
FINGERPRINT_PREFIX = "f:"

# Compact claim field names (to minimise token length for character-limited platforms).
# Full name -> short key
COMPACT_FIELDS = {
    "profile_package": "p",
    "pypi_username": "u",
    "subject": "s",
    "issued_at": "i",
    "expires_at": "e",
    "nonce": "n",
    "signature": "g",
}
COMPACT_FIELDS_INV = {v: k for k, v in COMPACT_FIELDS.items()}


def build_claim(
    *,
    profile_package: str,
    pypi_username: str,
    claim_type: str,
    subject_url: str,
    key_id: str,
    signature_backend: str = "minisign",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    nonce: str | None = None,
) -> dict[str, Any]:
    """Return an unsigned full claim dict ready for signing."""
    if issued_at is None:
        issued_at = datetime.now(tz=timezone.utc)
    if expires_at is None:
        try:
            expires_at = issued_at.replace(year=issued_at.year + 1)
        except ValueError:
            expires_at = issued_at + timedelta(days=365)
    if nonce is None:
        nonce = str(uuid.UUID(bytes=secrets.token_bytes(16), version=4))

    return {
        "profile_package": profile_package,
        "pypi_username": pypi_username,
        "claim": claim_type,
        "subject": subject_url,
        "issued_at": issued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nonce": nonce,
        "key_id": key_id,
        "signature_backend": signature_backend,
    }


def build_compact_claim(
    *,
    profile_package: str,
    pypi_username: str,
    subject_url: str,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    nonce: str | None = None,
) -> dict[str, Any]:
    """Return an unsigned compact claim dict ready for signing.

    Compact claims use short single-letter keys and Unix timestamps instead of
    ISO strings, and omit redundant fields (claim type, key_id, backend).
    The signature field is ``g`` and stores only the raw 64-byte Ed25519
    signature as base64url (no minisign header prefix), saving another 14 chars
    vs the full format.

    Typical encoded length: ~360 chars — well under Mastodon's 500-char limit.
    """
    if issued_at is None:
        issued_at = datetime.now(tz=timezone.utc)
    if expires_at is None:
        try:
            expires_at = issued_at.replace(year=issued_at.year + 1)
        except ValueError:
            expires_at = issued_at + timedelta(days=365)
    if nonce is None:
        # 16 random bytes → 22 base64url chars (vs 36 for a UUID string)
        nonce = base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b"=").decode()

    return {
        "p": profile_package,
        "u": pypi_username,
        "s": subject_url,
        "i": int(issued_at.timestamp()),
        "e": int(expires_at.timestamp()),
        "n": nonce,
    }


def build_tiny_claim(
    *,
    profile_package: str,
    pypi_username: str,
    subject_url: str,
    year: int | None = None,
) -> dict[str, Any]:
    """Return an unsigned tiny claim dict ready for signing.

    The tiny claim carries NO nonce and NO sub-year expiry. Its message body is
    reconstructed at verify time from (profile_package, pypi_username,
    subject_url, year). The on-wire token contains only the 64-byte Ed25519
    signature, base64url-encoded.

    Trade-off: a tiny token is a long-lived self-assertion. Verifiers should
    accept signatures issued in the current year or one of the two prior
    years. Replay within that window is intentional and acceptable for slots
    like a PyPI display-name signature.

    Typical encoded length: ~88 chars (2-char prefix + 86-char base64url sig).
    """
    if year is None:
        year = datetime.now(tz=timezone.utc).year
    return {
        "p": profile_package,
        "u": pypi_username,
        "s": subject_url,
        "y": int(year),
    }


def tiny_message_bytes(
    *,
    profile_package: str,
    pypi_username: str,
    subject_url: str,
    year: int,
) -> bytes:
    """Deterministic message bytes for a tiny claim — the thing actually signed.

    Same canonical JSON shape as build_tiny_claim so the verifier can
    reconstruct the message from out-of-band context.
    """
    canonical = {
        "p": profile_package,
        "s": subject_url,
        "u": pypi_username,
        "y": int(year),
    }
    return json_dumps_bytes(canonical, sort_keys=True, separators=(",", ":"))


def encode_tiny_token(sig_64: bytes) -> str:
    """Encode a raw 64-byte Ed25519 signature as a tiny token string."""
    if len(sig_64) != 64:
        raise ValueError(f"tiny token requires a 64-byte signature, got {len(sig_64)}")
    sig_b64url = base64.urlsafe_b64encode(sig_64).rstrip(b"=").decode()
    return f"{TINY_PREFIX}{sig_b64url}"


def decode_tiny_token(token: str) -> bytes:
    """Decode a tiny token to its raw 64-byte signature."""
    token = token.strip()
    if not token.startswith(TINY_PREFIX):
        raise ValueError(f"not a tiny token (missing {TINY_PREFIX!r} prefix)")
    sig_b64url = token[len(TINY_PREFIX) :]
    padding = (4 - len(sig_b64url) % 4) % 4
    raw = base64.urlsafe_b64decode(sig_b64url + "=" * padding)
    if len(raw) != 64:
        raise ValueError(f"tiny token decoded to {len(raw)} bytes, expected 64")
    return raw


def fingerprint_of_full_proof(full_token: str, key_id_hex: str) -> str:
    """Return a fingerprint pointer token for a full proof token.

    The fingerprint is ``f:<keyid16hex>:<hash16hex>`` where:
      - keyid16hex is the lowercase first 8 bytes of the minisign key id
      - hash16hex is the lowercase first 8 bytes of blake2b(full_token)

    Total length: 35 chars. The full token is expected to be discoverable
    elsewhere (e.g. via the profile package on PyPI's JSON API).
    """
    if not full_token:
        raise ValueError("full_token must be non-empty")
    keyid = key_id_hex.lower().lstrip("0x")[:16]
    if len(keyid) != 16:
        raise ValueError(f"key_id must be at least 8 bytes (16 hex chars), got {key_id_hex!r}")
    digest = hashlib.blake2b(full_token.encode(), digest_size=8).hexdigest()
    return f"{FINGERPRINT_PREFIX}{keyid}:{digest}"


def parse_fingerprint(token: str) -> tuple[str, str]:
    """Return (key_id_hex, hash_hex) parsed from a fingerprint token."""
    token = token.strip()
    if not token.startswith(FINGERPRINT_PREFIX):
        raise ValueError(f"not a fingerprint token (missing {FINGERPRINT_PREFIX!r} prefix)")
    body = token[len(FINGERPRINT_PREFIX) :]
    parts = body.split(":")
    if len(parts) != 2 or len(parts[0]) != 16 or len(parts[1]) != 16:
        raise ValueError(f"malformed fingerprint token: {token!r}")
    return parts[0].lower(), parts[1].lower()


def is_tiny_token(s: str) -> bool:
    """Return True if s looks like a tiny token."""
    return s.strip().startswith(TINY_PREFIX) and not s.strip().startswith(FINGERPRINT_PREFIX)


def is_fingerprint_token(s: str) -> bool:
    """Return True if s looks like a fingerprint token."""
    return s.strip().startswith(FINGERPRINT_PREFIX)


def is_compact_claim(claim: dict[str, Any]) -> bool:
    """Return True if this is a compact claim (uses short single-letter keys)."""
    return "p" in claim and "s" in claim


def encode_claim(claim: dict[str, Any]) -> str:
    """Base64url-encode a claim dict (with signature) to a proof token string."""
    raw = json_dumps_bytes(claim, separators=(",", ":"))
    token = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    return f"{PROOF_PREFIX} {token}"


def decode_claim(token: str) -> dict[str, Any]:
    """Decode a pypi-profile-proof token back to a dict.

    Handles both full and compact claim formats transparently.
    """
    token = token.strip()
    if token.startswith(PROOF_PREFIX):
        token = token[len(PROOF_PREFIX) :].strip()
    padding = (4 - len(token) % 4) % 4
    raw = base64.urlsafe_b64decode(token + "=" * padding)
    return cast(dict[str, Any], json_loads(raw))


def is_expired(claim: dict[str, Any]) -> bool:
    """Return True if the claim's expiry is in the past.

    Handles both ISO-string (full) and Unix-timestamp (compact) formats.
    """
    if is_compact_claim(claim):
        exp = claim.get("e")
        if not exp:
            return False
        try:
            return datetime.now(tz=timezone.utc).timestamp() > int(exp)
        except (TypeError, ValueError):
            return False

    expires_str = claim.get("expires_at", "")
    if not expires_str:
        return False
    try:
        expires = datetime.strptime(expires_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return datetime.now(tz=timezone.utc) > expires
    except ValueError:
        logger.debug("Could not parse expires_at %r in claim", expires_str, exc_info=True)
        return False
