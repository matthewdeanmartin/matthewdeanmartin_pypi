"""Minisign keypair generation and claim signing for pypi-profile."""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from pypi_profile.claims import build_claim, encode_claim

logger = logging.getLogger(__name__)

DEFAULT_KEY_DIR = Path("~/.pypi_profile").expanduser()
DEFAULT_SK_NAME = "minisign.key"
DEFAULT_PK_NAME = "minisign.pub"


def _import_minisign() -> Any:
    try:
        import minisign  # type: ignore[import-untyped]

        return minisign
    except ImportError as exc:
        logger.debug("py-minisign not installed; signing unavailable")
        raise ImportError(
            "py-minisign is required for signing. Install it with: uv add py-minisign"
        ) from exc


def generate_keypair(
    key_dir: Path | None = None,
    password: str | None = None,
    force: bool = False,
) -> tuple[Path, Path, str]:
    """Generate a minisign keypair.

    Returns (sk_path, pk_path, public_key_b64).
    """
    ms = _import_minisign()

    if key_dir is None:
        key_dir = DEFAULT_KEY_DIR
    key_dir.mkdir(parents=True, exist_ok=True)

    sk_path = key_dir / DEFAULT_SK_NAME
    pk_path = key_dir / DEFAULT_PK_NAME

    if sk_path.exists() and not force:
        raise FileExistsError(
            f"Secret key already exists at {sk_path}. Use force=True to overwrite."
        )

    logger.debug("Generating minisign keypair in %s", key_dir)
    kp = ms.KeyPair.generate()

    if password:
        kp.secret_key.encrypt(password)

    sk_path.write_bytes(bytes(kp.secret_key) + b"\n")
    pk_path.write_bytes(bytes(kp.public_key) + b"\n")
    logger.info("Keypair written: sk=%s pk=%s", sk_path, pk_path)

    public_key_b64 = kp.public_key.to_base64().decode()
    return sk_path, pk_path, public_key_b64


def load_secret_key(sk_path: Path | None = None, password: str | None = None) -> Any:
    """Load a minisign SecretKey from disk, decrypting if a password is provided."""
    import os

    ms = _import_minisign()

    if sk_path is None:
        env_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
        sk_path = (
            Path(env_path).expanduser()
            if env_path
            else DEFAULT_KEY_DIR / DEFAULT_SK_NAME
        )
    if not sk_path.exists():
        logger.error("Secret key not found at %s", sk_path)
        raise FileNotFoundError(
            f"Secret key not found at {sk_path}. Run: pypi-profile keygen"
        )

    if not password:
        password = os.environ.get("PYPI_PROFILE_KEY_PASSWORD", "")

    logger.debug("Loading secret key from %s", sk_path)
    sk = ms.SecretKey.from_file(sk_path)
    if password:
        sk.decrypt(password)
    return sk


def sign_controls_url(
    *,
    profile_package: str,
    pypi_username: str,
    subject_url: str,
    sk_path: Path | None = None,
    password: str | None = None,
) -> str:
    """Sign a controls-url claim and return the encoded proof string."""
    logger.debug("Signing controls-url claim for %s -> %s", pypi_username, subject_url)
    sk = load_secret_key(sk_path, password)

    key_id_bytes = bytes(sk._keynum_sk.key_id)
    key_id_hex = key_id_bytes.hex().upper()

    claim = build_claim(
        profile_package=profile_package,
        pypi_username=pypi_username,
        claim_type="controls-url",
        subject_url=subject_url,
        key_id=key_id_hex,
        signature_backend="minisign",
    )

    claim_json_bytes = _claim_to_bytes(claim)
    sig = sk.sign(claim_json_bytes, prehash=True)
    sig_b64 = base64.standard_b64encode(bytes(sig)).decode()

    claim["signature"] = sig_b64
    return encode_claim(claim)


def read_public_key_b64(pk_path: Path | None = None) -> str | None:
    """Return the base64-encoded public key from disk, or None if unavailable."""
    import os

    if pk_path is None:
        env_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
        pk_path = (
            Path(env_path).expanduser().with_suffix(".pub")
            if env_path
            else DEFAULT_KEY_DIR / DEFAULT_PK_NAME
        )
    if not pk_path.exists():
        logger.debug("Public key not found at %s", pk_path)
        return None
    try:
        ms = _import_minisign()
        pk = ms.PublicKey.from_file(pk_path)
        logger.debug("Loaded public key from %s", pk_path)
        return pk.to_base64().decode()
    except Exception:
        logger.warning("Failed to read public key from %s", pk_path, exc_info=True)
        return None


def patch_public_key_in_toml(toml_path: Path, pk_path: Path | None = None) -> str | None:
    """If toml_path has an empty public_key and a key exists on disk, write it in-place.

    Returns the base64 public key string if patched, None otherwise.
    Only touches lines matching ``public_key = ""``.  All other content,
    including comments, is preserved exactly.
    """
    import re

    pub_b64 = read_public_key_b64(pk_path)
    if not pub_b64:
        return None

    try:
        text = toml_path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Cannot read %s to patch public key", toml_path, exc_info=True)
        return None

    patched, n = re.subn(
        r'(?m)^(public_key\s*=\s*)""',
        f'public_key = "{pub_b64}"',
        text,
    )
    if n == 0:
        logger.debug("No empty public_key field found in %s; skipping patch", toml_path)
        return None

    try:
        toml_path.write_text(patched, encoding="utf-8")
        logger.info("Patched public key into %s", toml_path)
    except OSError:
        logger.warning("Cannot write patched public key to %s", toml_path, exc_info=True)
        return None

    return pub_b64


def _claim_to_bytes(claim: dict[str, Any]) -> bytes:
    """Deterministic JSON bytes for a claim (without the signature field)."""
    import json

    canonical = {k: v for k, v in claim.items() if k != "signature"}
    return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
