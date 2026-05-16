"""Key management helpers for pypi-profile: info, list, rotate, recover, export, import."""

from __future__ import annotations

import contextlib
import datetime
import os
import sys
from pathlib import Path
from typing import Any

from pypi_profile.signing import (
    DEFAULT_KEY_DIR,
    DEFAULT_SK_NAME,
    KEYRING_SERVICE,
    generate_keypair,
    keyring_is_usable,
    keyring_username,
    load_key_bytes_from_keyring,
    patch_proofs_in_toml,
    patch_public_key_in_toml,
)


def derive_key_id(sk_bytes: bytes) -> str:
    """Return the 16-char upper-hex key ID embedded in a minisign secret key."""
    import minisign  # type: ignore[import-untyped]

    sk = minisign.SecretKey.from_bytes(sk_bytes.rstrip(b"\n"))
    return bytes(sk._keynum_sk.key_id).hex().upper()


def derive_public_key_b64(sk_bytes: bytes) -> str:
    """Return the base64-encoded public key derived from secret key bytes."""
    import minisign  # type: ignore[import-untyped]

    sk = minisign.SecretKey.from_bytes(sk_bytes.rstrip(b"\n"))
    return sk.get_public_key().to_base64().decode()


def load_all_toml_public_keys(start_dir: Path | None = None) -> list[tuple[Path, str]]:
    """Return [(toml_path, public_key_b64), ...] for every profile TOML found."""
    from pypi_profile.finder import find_profile_files

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

    result: list[tuple[Path, str]] = []
    for toml_path in find_profile_files(root=start_dir):
        try:
            with open(toml_path, "rb") as fh:
                data = tomllib.load(fh)
            pk = data.get("verification", {}).get("public_key", "")
            result.append((toml_path, pk))
        except Exception:
            result.append((toml_path, ""))
    return result


def key_match_status(pub_b64: str, toml_entries: list[tuple[Path, str]]) -> str:
    """Return a human-readable match verdict between a public key and TOML entries."""
    if not toml_entries:
        return "no profile TOML found"
    for toml_path, toml_pk in toml_entries:
        if not toml_pk:
            continue
        if toml_pk == pub_b64:
            return f"matches ({toml_path})"
    for toml_path, toml_pk in toml_entries:
        if toml_pk:
            return f"mismatch ({toml_path})"
    return "absent (no public_key in TOML)"


def key_info(
    sk_path: Path | None = None,
    keyring_identity: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    """Collect information about the active signing key without modifying anything.

    Returns a dict with keys: source, key_id, generated, public_key, profile_binding.
    Returns {'not_found': True} when no key is present.
    """
    sk_bytes: bytes | None = None
    source: str = "not found"

    env_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
    if sk_path is not None:
        if sk_path.exists():
            sk_bytes = sk_path.read_bytes()
            source = f"disk ({sk_path})"
        else:
            return {"not_found": True, "source": f"disk path given but not found ({sk_path})"}

    elif env_path:
        disk_path = Path(env_path).expanduser()
        if disk_path.exists():
            sk_bytes = disk_path.read_bytes()
            source = f"env var PYPI_PROFILE_KEY_PATH ({disk_path})"
        else:
            return {"not_found": True, "source": f"PYPI_PROFILE_KEY_PATH set but key not found ({disk_path})"}

    elif keyring_is_usable():
        raw = load_key_bytes_from_keyring(keyring_identity)
        if raw is not None:
            sk_bytes = raw
            uname = keyring_username(keyring_identity)
            source = f"keyring (username={uname!r}, service={KEYRING_SERVICE!r})"
        else:
            disk_path = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
            if disk_path.exists():
                sk_bytes = disk_path.read_bytes()
                source = f"disk ({disk_path})"

    else:
        disk_path = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
        if disk_path.exists():
            sk_bytes = disk_path.read_bytes()
            source = f"disk ({disk_path})"

    if sk_bytes is None:
        return {"not_found": True, "source": source}

    try:
        key_id = derive_key_id(sk_bytes)
        pub_b64 = derive_public_key_b64(sk_bytes)
    except Exception as exc:
        return {"not_found": False, "source": source, "error": str(exc)}

    disk_key_path = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
    generated = "unknown"
    if disk_key_path.exists():
        mtime = disk_key_path.stat().st_mtime
        generated = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%d")

    toml_entries = load_all_toml_public_keys()
    binding = key_match_status(pub_b64, toml_entries)

    return {
        "not_found": False,
        "source": source,
        "key_id": key_id,
        "generated": generated,
        "public_key": pub_b64,
        "profile_binding": binding,
    }


def key_list(extra_dirs: list[Path] | None = None) -> list[dict[str, Any]]:
    """Enumerate all known keys across keyring and disk locations.

    Returns a list of dicts, each with: identity_or_path, key_id, source, public_key.
    """
    results: list[dict[str, Any]] = []
    seen_key_ids: set[str] = set()

    toml_entries = load_all_toml_public_keys()

    def add_from_bytes(raw: bytes, source: str, label: str) -> dict[str, Any] | None:
        try:
            kid = derive_key_id(raw)
            pub = derive_public_key_b64(raw)
        except Exception:
            return None
        binding = key_match_status(pub, toml_entries)
        return {"identity_or_path": label, "key_id": kid, "source": source, "public_key": pub, "binding": binding}

    if keyring_is_usable():
        for identity in ["default", keyring_username()]:
            raw = load_key_bytes_from_keyring(identity if identity != "default" else None)
            if raw is None:
                continue
            label = f"{KEYRING_SERVICE}/{identity}"
            entry = add_from_bytes(raw, "keyring", label)
            if entry and entry["key_id"] not in seen_key_ids:
                seen_key_ids.add(entry["key_id"])
                results.append(entry)
    else:
        results.append(
            {
                "identity_or_path": "(enumeration not supported by keyring backend)",
                "key_id": "—",
                "source": "keyring unavailable",
                "public_key": "",
                "binding": "",
            }
        )

    search_dirs = [DEFAULT_KEY_DIR, Path.cwd(), Path.cwd() / ".pypi_profile"]
    if extra_dirs:
        search_dirs.extend(extra_dirs)

    for d in search_dirs:
        if not d.is_dir():
            continue
        for kfile in sorted(d.glob("minisign*.key")):
            if not kfile.exists():
                continue
            try:
                raw = kfile.read_bytes()
            except OSError:
                continue
            entry = add_from_bytes(raw, "disk", str(kfile))
            if entry is None:
                continue
            label = str(kfile)
            if entry["key_id"] in seen_key_ids:
                entry["source"] = "disk (matches keyring)"
            seen_key_ids.add(entry["key_id"])
            results.append(entry)

    return results


def key_rotate(
    toml_path: Path,
    profile_package: str,
    pypi_username: str,
    key_dir: Path | None = None,
    keyring_identity: str | None = None,
    password: str | None = None,
    no_keep_old: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Replace the active signing key and re-sign all profile proofs.

    Returns a summary dict with keys: old_key_id, new_key_id, archived_path, updated_urls.
    Rolls back TOML to the original content if re-signing fails.
    """
    old_sk_bytes: bytes | None = None
    old_key_id: str = "unknown"

    if keyring_is_usable():
        old_sk_bytes = load_key_bytes_from_keyring(keyring_identity)
    if old_sk_bytes is None:
        effective_dir = key_dir or DEFAULT_KEY_DIR
        old_disk_path = effective_dir / DEFAULT_SK_NAME
        if old_disk_path.exists():
            old_sk_bytes = old_disk_path.read_bytes()

    if old_sk_bytes is not None:
        with contextlib.suppress(Exception):
            old_key_id = derive_key_id(old_sk_bytes)

    original_toml = toml_path.read_text(encoding="utf-8") if toml_path.exists() else ""

    if dry_run:
        return {
            "dry_run": True,
            "old_key_id": old_key_id,
            "new_key_id": "(would generate)",
            "archived_path": None,
            "updated_urls": [],
        }

    sk_path, _pk_path, new_pub_b64 = generate_keypair(
        key_dir=key_dir,
        password=password,
        force=True,
        keyring_identity=keyring_identity,
        store_in_keyring=True,
    )

    import minisign  # type: ignore[import-untyped]

    new_sk = minisign.SecretKey.from_file(sk_path)
    new_key_id = bytes(new_sk._keynum_sk.key_id).hex().upper()

    import re

    text = toml_path.read_text(encoding="utf-8")
    patched, _ = re.subn(
        r'(?m)^(public_key\s*=\s*)"[^"]*"',
        f'public_key = "{new_pub_b64}"',
        text,
    )
    toml_path.write_text(patched, encoding="utf-8")

    try:
        updated_urls = patch_proofs_in_toml(
            toml_path=toml_path,
            profile_package=profile_package,
            pypi_username=pypi_username,
            sk_path=sk_path,
            password=password,
            force=True,
        )
    except Exception:
        toml_path.write_text(original_toml, encoding="utf-8")
        raise

    archived_path: Path | None = None
    if old_sk_bytes is not None and not no_keep_old:
        ts = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
        effective_dir = key_dir or DEFAULT_KEY_DIR
        archived_path = effective_dir / f"{DEFAULT_SK_NAME}.{ts}.bak"
        archived_path.write_bytes(old_sk_bytes)

    return {
        "dry_run": False,
        "old_key_id": old_key_id,
        "new_key_id": new_key_id,
        "new_public_key": new_pub_b64,
        "archived_path": archived_path,
        "updated_urls": updated_urls,
    }


def key_recover(
    toml_path: Path,
    profile_package: str,
    pypi_username: str,
    key_dir: Path | None = None,
    keyring_identity: str | None = None,
    password: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Guide the user through recovery when the secret key is lost.

    Returns a summary dict with keys: key_was_present, urls_needing_update, new_key_id.
    """
    key_present = False
    if keyring_is_usable():
        raw = load_key_bytes_from_keyring(keyring_identity)
        if raw is not None:
            key_present = True
    if not key_present:
        effective_dir = key_dir or DEFAULT_KEY_DIR
        if (effective_dir / DEFAULT_SK_NAME).exists():
            key_present = True

    if key_present:
        return {"key_was_present": True, "message": "Key found — use key-rotate instead of key-recover."}

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

    urls_with_proofs: list[str] = []
    if toml_path.exists():
        try:
            with open(toml_path, "rb") as fh:
                raw_toml = tomllib.load(fh)
            for entry in raw_toml.get("profiles", []):
                if entry.get("stored_proof"):
                    urls_with_proofs.append(entry.get("url", ""))
        except Exception:
            pass

    if dry_run:
        return {
            "key_was_present": False,
            "dry_run": True,
            "urls_needing_update": urls_with_proofs,
            "message": "DRY RUN: would generate new keypair, update TOML, and re-sign all proofs.",
        }

    sk_path, pk_path, new_pub_b64 = generate_keypair(
        key_dir=key_dir,
        password=password,
        force=True,
        keyring_identity=keyring_identity,
        store_in_keyring=True,
    )

    import minisign  # type: ignore[import-untyped]

    new_sk = minisign.SecretKey.from_file(sk_path)
    new_key_id = bytes(new_sk._keynum_sk.key_id).hex().upper()

    patch_public_key_in_toml(toml_path, pk_path)

    updated_urls = patch_proofs_in_toml(
        toml_path=toml_path,
        profile_package=profile_package,
        pypi_username=pypi_username,
        sk_path=sk_path,
        password=password,
        force=True,
    )

    return {
        "key_was_present": False,
        "dry_run": False,
        "new_key_id": new_key_id,
        "new_public_key": new_pub_b64,
        "sk_path": sk_path,
        "updated_urls": updated_urls,
        "urls_needing_update": urls_with_proofs,
    }


def key_export(
    output_path: Path | None = None,
    sk_path: Path | None = None,
    keyring_identity: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Export the raw secret key bytes to a file (or return them for stdout).

    Never prints key material to stdout — callers must write to a file.
    Returns dict with keys: written_to, key_id, warning.
    """
    sk_bytes: bytes | None = None
    source: str

    env_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
    if sk_path is not None:
        if not sk_path.exists():
            raise FileNotFoundError(f"Secret key not found at {sk_path}")
        sk_bytes = sk_path.read_bytes()
        source = str(sk_path)
    elif env_path:
        disk_path = Path(env_path).expanduser()
        if not disk_path.exists():
            raise FileNotFoundError(f"Secret key not found at {disk_path} (from PYPI_PROFILE_KEY_PATH)")
        sk_bytes = disk_path.read_bytes()
        source = str(disk_path)
    elif keyring_is_usable():
        raw = load_key_bytes_from_keyring(keyring_identity)
        if raw is not None:
            sk_bytes = raw
            uname = keyring_username(keyring_identity)
            source = f"keyring (username={uname!r})"
        else:
            disk_path = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
            if disk_path.exists():
                sk_bytes = disk_path.read_bytes()
                source = str(disk_path)
            else:
                raise FileNotFoundError("No secret key found. Run: pypi-profile keygen")
    else:
        disk_path = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
        if disk_path.exists():
            sk_bytes = disk_path.read_bytes()
            source = str(disk_path)
        else:
            raise FileNotFoundError("No secret key found. Run: pypi-profile keygen")

    key_id = derive_key_id(sk_bytes)

    if dry_run:
        return {
            "dry_run": True,
            "source": source,
            "key_id": key_id,
            "output": str(output_path) if output_path else "(stdout)",
            "warning": "The exported file contains your secret key. Treat it as a password.",
        }

    if output_path is None:
        raise ValueError("output_path is required for key-export (never write key material to stdout)")

    output_path.write_bytes(sk_bytes)
    return {
        "dry_run": False,
        "written_to": str(output_path),
        "source": source,
        "key_id": key_id,
        "warning": "The exported file contains your secret key. Treat it as a password. Never commit it.",
    }


def key_import(
    import_path: Path,
    keyring_identity: str | None = None,
    key_dir: Path | None = None,
    no_keyring: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Install a previously exported key file into the keyring and/or disk.

    Returns dict with keys: key_id, stored_in_keyring, stored_on_disk, disk_path.
    """
    effective_dir = key_dir or DEFAULT_KEY_DIR
    disk_path = effective_dir / DEFAULT_SK_NAME

    if dry_run:
        return {
            "dry_run": True,
            "key_id": "(not read in dry-run)",
            "would_store_in_keyring": keyring_is_usable() and not no_keyring,
            "would_store_on_disk": True,
            "disk_path": str(disk_path),
        }

    if not import_path.exists():
        raise FileNotFoundError(f"Import file not found: {import_path}")

    sk_bytes = import_path.read_bytes()
    key_id = derive_key_id(sk_bytes)

    if disk_path.exists() and not force:
        raise FileExistsError(f"Key already exists at {disk_path}. Use --force to overwrite.")

    stored_keyring = False
    if not no_keyring and keyring_is_usable():
        from pypi_profile.signing import store_key_in_keyring

        stored_keyring = store_key_in_keyring(sk_bytes, keyring_identity)

    effective_dir.mkdir(parents=True, exist_ok=True)
    disk_path.write_bytes(sk_bytes)

    return {
        "dry_run": False,
        "key_id": key_id,
        "stored_in_keyring": stored_keyring,
        "stored_on_disk": True,
        "disk_path": str(disk_path),
    }
