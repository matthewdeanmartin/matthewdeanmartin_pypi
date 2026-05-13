"""Minisign keypair generation and claim signing for pypi-profile."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import keyring
import keyring.backends.fail
import minisign  # type: ignore[import-untyped]

from pypi_profile.claims import build_claim, build_compact_claim, encode_claim

logger = logging.getLogger(__name__)

DEFAULT_KEY_DIR = Path("~/.pypi_profile").expanduser()
DEFAULT_SK_NAME = "minisign.key"
DEFAULT_PK_NAME = "minisign.pub"

KEYRING_SERVICE = "pypi-profile"


def keyring_username() -> str:
    """Return the keyring username for the secret key entry."""
    return os.environ.get("PYPI_PROFILE_KEYRING_USERNAME", "default")


def keyring_is_usable() -> bool:
    """Return True when a non-fail keyring backend is active."""
    backend = keyring.get_keyring()
    if isinstance(backend, keyring.backends.fail.Keyring):
        logger.debug("keyring fail backend active; falling back to disk")
        return False
    return True


def store_key_in_keyring(sk_bytes: bytes) -> bool:
    """Store raw secret key bytes in keyring. Returns True on success."""
    try:
        encoded = base64.b64encode(sk_bytes).decode()
        keyring.set_password(KEYRING_SERVICE, keyring_username(), encoded)
        logger.info(
            "Secret key stored in keyring (service=%r, username=%r)",
            KEYRING_SERVICE,
            keyring_username(),
        )
        return True
    except Exception:
        logger.warning("Could not store key in keyring", exc_info=True)
        return False


def load_key_bytes_from_keyring() -> bytes | None:
    """Retrieve raw secret key bytes from keyring, or None if unavailable."""
    try:
        encoded = keyring.get_password(KEYRING_SERVICE, keyring_username())
        if encoded is None:
            logger.debug(
                "No key found in keyring for service=%r username=%r",
                KEYRING_SERVICE,
                keyring_username(),
            )
            return None
        return base64.b64decode(encoded)
    except Exception:
        logger.warning("Could not load key from keyring", exc_info=True)
        return None


def generate_keypair(
    key_dir: Path | None = None,
    password: str | None = None,
    force: bool = False,
) -> tuple[Path, Path, str]:
    """Generate a minisign keypair.

    The secret key is stored in the system keyring when a usable backend is
    available, and always written to disk as a fallback.  Returns
    (sk_path, pk_path, public_key_b64).
    """
    if key_dir is None:
        key_dir = DEFAULT_KEY_DIR
    key_dir.mkdir(parents=True, exist_ok=True)

    sk_path = key_dir / DEFAULT_SK_NAME
    pk_path = key_dir / DEFAULT_PK_NAME

    if sk_path.exists() and not force:
        raise FileExistsError(f"Secret key already exists at {sk_path}. Use force=True to overwrite.")

    logger.debug("Generating minisign keypair in %s", key_dir)
    kp = minisign.KeyPair.generate()

    if password:
        kp.secret_key.encrypt(password)

    sk_bytes = bytes(kp.secret_key) + b"\n"
    sk_path.write_bytes(sk_bytes)
    pk_path.write_bytes(bytes(kp.public_key) + b"\n")
    logger.info("Keypair written: sk=%s pk=%s", sk_path, pk_path)

    if keyring_is_usable() and store_key_in_keyring(sk_bytes):
        logger.info("Secret key also stored in system keyring")

    public_key_b64 = kp.public_key.to_base64().decode()
    return sk_path, pk_path, public_key_b64


def load_secret_key(sk_path: Path | None = None, password: str | None = None) -> Any:
    """Load a minisign SecretKey, preferring the system keyring over disk.

    Resolution order:
    1. Explicit sk_path argument (bypasses keyring).
    2. PYPI_PROFILE_KEY_PATH environment variable (bypasses keyring).
    3. System keyring (if a usable backend is active).
    4. Default disk path (~/.pypi_profile/minisign.key).
    """
    if not password:
        password = os.environ.get("PYPI_PROFILE_KEY_PASSWORD", "")

    # Explicit path — load directly from disk, no keyring.
    if sk_path is not None:
        if not sk_path.exists():
            raise FileNotFoundError(f"Secret key not found at {sk_path}. Run: pypi-profile keygen")
        logger.debug("Loading secret key from explicit path %s", sk_path)
        sk = minisign.SecretKey.from_file(sk_path)
        if password:
            sk.decrypt(password)
        return sk

    env_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
    if env_path:
        disk_path = Path(env_path).expanduser()
        if not disk_path.exists():
            raise FileNotFoundError(f"Secret key not found at {disk_path} (from PYPI_PROFILE_KEY_PATH).")
        logger.debug("Loading secret key from PYPI_PROFILE_KEY_PATH=%s", disk_path)
        sk = minisign.SecretKey.from_file(disk_path)
        if password:
            sk.decrypt(password)
        return sk

    # Try keyring first.
    if keyring_is_usable():
        sk_bytes = load_key_bytes_from_keyring()
        if sk_bytes is not None:
            logger.debug("Loading secret key from system keyring")
            sk = minisign.SecretKey.from_bytes(sk_bytes.rstrip(b"\n"))
            if password:
                sk.decrypt(password)
            return sk

    # Fall back to default disk path.
    disk_path = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
    if not disk_path.exists():
        logger.error("Secret key not found at %s", disk_path)
        raise FileNotFoundError(f"Secret key not found at {disk_path}. Run: pypi-profile keygen")
    logger.debug("Loading secret key from disk fallback %s", disk_path)
    sk = minisign.SecretKey.from_file(disk_path)
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
    compact: bool = False,
) -> str:
    """Sign a controls-url claim and return the encoded proof string.

    ``compact=True`` produces a shorter token (~360 chars) suitable for
    character-limited platforms like Mastodon.  It omits redundant fields and
    uses single-letter keys + Unix timestamps.  The default (False) produces
    the full human-readable token.
    """
    logger.debug(
        "Signing controls-url claim for %s -> %s (compact=%s)",
        pypi_username,
        subject_url,
        compact,
    )
    sk = load_secret_key(sk_path, password)

    if compact:
        claim = build_compact_claim(
            profile_package=profile_package,
            pypi_username=pypi_username,
            subject_url=subject_url,
        )
        claim_json_bytes = claim_to_bytes(claim)
        sig = sk.sign(claim_json_bytes, prehash=True)
        # Compact: store only the raw 64-byte Ed25519 sig as base64url (no header).
        claim["g"] = base64.urlsafe_b64encode(sig._signature).rstrip(b"=").decode()
    else:
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
        claim_json_bytes = claim_to_bytes(claim)
        sig = sk.sign(claim_json_bytes, prehash=True)
        # Store only the 74-byte binary (algo + key_id + ed25519_sig), not the armored text format.
        sig_b64 = base64.standard_b64encode(sig._signature_algorithm.value + sig._key_id + sig._signature).decode()
        claim["signature"] = sig_b64

    return encode_claim(claim)


def read_public_key_b64(pk_path: Path | None = None) -> str | None:
    """Return the base64-encoded public key from disk, or None if unavailable."""
    if pk_path is None:
        env_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
        pk_path = Path(env_path).expanduser().with_suffix(".pub") if env_path else DEFAULT_KEY_DIR / DEFAULT_PK_NAME
    if not pk_path.exists():
        logger.debug("Public key not found at %s", pk_path)
        return None
    try:
        pk = minisign.PublicKey.from_file(pk_path)
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


def _make_proof_replacer(proof: str, escaped_url: str) -> Any:
    """Return a re.sub replacement function with proof and escaped_url bound at definition time."""

    def replace_or_insert(m: re.Match[str]) -> str:
        block = m.group(0)
        proof_line = f'stored_proof = "{proof}"'
        if re.search(r"(?m)^stored_proof\s*=", block):
            block = re.sub(r"(?m)^stored_proof\s*=.*$", proof_line, block)
        else:
            block = re.sub(
                rf'(?m)^(url\s*=\s*"{escaped_url}"\s*)$',
                r"\1\n" + proof_line,
                block,
            )
        return block

    return replace_or_insert


def patch_proofs_in_toml(
    toml_path: Path,
    profile_package: str,
    pypi_username: str,
    sk_path: Path | None = None,
    password: str | None = None,
    force: bool = False,
) -> list[str]:
    """Sign every [[profiles]] entry that lacks a stored_proof and write them in-place.

    Returns a list of URLs that were updated.
    Only updates entries missing stored_proof unless force=True.
    Preserves all comments and formatting in the TOML file.
    """
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-reuse-def]

    try:
        text = toml_path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Cannot read %s", toml_path, exc_info=True)
        return []

    original_text = text

    with open(toml_path, "rb") as fh:
        raw = tomllib.load(fh)

    profiles = raw.get("profiles", [])
    updated: list[str] = []

    for entry in profiles:
        url = entry.get("url", "")
        if not url:
            continue
        if entry.get("stored_proof") and not force:
            logger.debug("Skipping %s — stored_proof already present", url)
            continue

        compact = entry.get("kind", "") == "mastodon"
        try:
            proof = sign_controls_url(
                profile_package=profile_package,
                pypi_username=pypi_username,
                subject_url=url,
                sk_path=sk_path,
                password=password,
                compact=compact,
            )
        except (FileNotFoundError, OSError, ValueError) as exc:
            logger.warning("Could not sign %s: %s", url, exc)
            continue

        escaped_url = re.escape(url)
        replacer = _make_proof_replacer(proof, escaped_url)
        # (?:(?!\[\[profiles\]\])[\s\S])*? — lazy match that cannot cross into the next [[profiles]] block
        pattern = (
            rf'(\[\[profiles\]\](?:(?!\[\[profiles\]\])[\s\S])*?url\s*=\s*"{escaped_url}"[\s\S]*?)(?=\[\[|\[(?!\[)|\Z)'
        )
        new_text, n = re.subn(pattern, replacer, text, flags=re.DOTALL)
        if n:
            text = new_text
            updated.append(url)
            logger.info("Wrote stored_proof for %s into %s", url, toml_path)
        else:
            logger.warning("Could not locate [[profiles]] block for url=%s in %s", url, toml_path)

    if updated:
        try:
            toml_path.write_text(text, encoding="utf-8")
        except OSError:
            logger.warning("Cannot write patched proofs to %s", toml_path, exc_info=True)
            return []

        # Validate the written file parses as valid TOML; roll back if not.
        try:
            with open(toml_path, "rb") as fh:
                written = tomllib.load(fh)
        except Exception as exc:
            logger.error("Patched TOML is invalid (%s); rolling back to original content", exc)
            try:
                toml_path.write_text(original_text, encoding="utf-8")
            except OSError:
                logger.error(
                    "Rollback also failed for %s — file may be corrupt; original content: %r",
                    toml_path,
                    original_text,
                )
            raise ValueError(
                f"patch_proofs_in_toml produced invalid TOML for {toml_path}; "
                f"file rolled back to original. Parser error: {exc}"
            ) from exc

        # Validate that no two [[profiles]] entries share the same stored_proof.
        written_profiles = written.get("profiles", [])
        seen_proofs: dict[str, str] = {}
        for entry in written_profiles:
            proof = entry.get("stored_proof", "")
            entry_url = entry.get("url", "")
            if not proof:
                continue
            if proof in seen_proofs:
                logger.error(
                    "Duplicate stored_proof detected: url=%r shares proof with url=%r — rolling back",
                    entry_url,
                    seen_proofs[proof],
                )
                try:
                    toml_path.write_text(original_text, encoding="utf-8")
                except OSError:
                    logger.error("Rollback failed for %s", toml_path)
                raise ValueError(
                    f"patch_proofs_in_toml wrote duplicate stored_proof for {entry_url!r} and "
                    f"{seen_proofs[proof]!r} in {toml_path}; file rolled back."
                )
            seen_proofs[proof] = entry_url

    return updated


def claim_to_bytes(claim: dict[str, Any]) -> bytes:
    """Deterministic JSON bytes for a claim (without the signature field).

    Works for both full claims (``signature`` key) and compact claims (``g`` key).
    """
    canonical = {k: v for k, v in claim.items() if k not in ("signature", "g")}
    return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
