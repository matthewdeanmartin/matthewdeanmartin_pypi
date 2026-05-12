"""Build and encode signed claims for pypi-profile proof-of-control."""

from __future__ import annotations

import base64
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, cast

logger = logging.getLogger(__name__)

PROOF_PREFIX = "pypi-profile-proof:"


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
    """Return an unsigned claim dict ready for signing."""
    if issued_at is None:
        issued_at = datetime.now(tz=timezone.utc)
    if expires_at is None:
        # Default: 1 year
        expires_at = issued_at.replace(year=issued_at.year + 1)
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


def encode_claim(claim: dict[str, Any]) -> str:
    """Base64url-encode a claim dict (with signature) to a proof token string."""
    raw = json.dumps(claim, separators=(",", ":")).encode()
    token = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    return f"{PROOF_PREFIX} {token}"


def decode_claim(token: str) -> dict[str, Any]:
    """Decode a pypi-profile-proof token back to a dict."""
    token = token.strip()
    if token.startswith(PROOF_PREFIX):
        token = token[len(PROOF_PREFIX) :].strip()
    # Re-add padding
    padding = (4 - len(token) % 4) % 4
    raw = base64.urlsafe_b64decode(token + "=" * padding)
    return cast(dict[str, Any], json.loads(raw))


def is_expired(claim: dict[str, Any]) -> bool:
    """Return True if the claim's expires_at is in the past."""
    expires_str = claim.get("expires_at", "")
    if not expires_str:
        return False
    try:
        expires = datetime.strptime(expires_str, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        return datetime.now(tz=timezone.utc) > expires
    except ValueError:
        logger.debug("Could not parse expires_at %r in claim", expires_str, exc_info=True)
        return False
