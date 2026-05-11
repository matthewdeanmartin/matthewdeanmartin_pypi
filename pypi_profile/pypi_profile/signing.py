"""Minisign keypair generation and claim signing for pypi-profile."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from pypi_profile.claims import build_claim, encode_claim

DEFAULT_KEY_DIR = Path("~/.pypi_profile").expanduser()
DEFAULT_SK_NAME = "minisign.key"
DEFAULT_PK_NAME = "minisign.pub"


def _import_minisign() -> Any:
    try:
        import minisign  # type: ignore[import-untyped]

        return minisign
    except ImportError as exc:
        raise ImportError("py-minisign is required for signing. Install it with: uv add py-minisign") from exc


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
        raise FileExistsError(f"Secret key already exists at {sk_path}. Use force=True to overwrite.")

    kp = ms.KeyPair.generate()

    if password:
        kp.secret_key.encrypt(password)

    sk_path.write_bytes(bytes(kp.secret_key) + b"\n")
    pk_path.write_bytes(bytes(kp.public_key) + b"\n")

    public_key_b64 = kp.public_key.to_base64().decode()
    return sk_path, pk_path, public_key_b64


def load_secret_key(sk_path: Path | None = None, password: str | None = None) -> Any:
    """Load a minisign SecretKey from disk, decrypting if a password is provided."""
    import os

    ms = _import_minisign()

    if sk_path is None:
        env_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
        sk_path = Path(env_path).expanduser() if env_path else DEFAULT_KEY_DIR / DEFAULT_SK_NAME
    if not sk_path.exists():
        raise FileNotFoundError(f"Secret key not found at {sk_path}. Run: pypi-profile keygen")

    if not password:
        password = os.environ.get("PYPI_PROFILE_KEY_PASSWORD", "")

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


def _claim_to_bytes(claim: dict[str, Any]) -> bytes:
    """Deterministic JSON bytes for a claim (without the signature field)."""
    import json

    canonical = {k: v for k, v in claim.items() if k != "signature"}
    return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
