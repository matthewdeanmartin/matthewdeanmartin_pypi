# Key Management — pypi-profile

This document specifies the key management features needed to make signing
practical for real users: multiple accounts, key rotation, lost-key recovery,
and inspecting what key is associated with what profile.

______________________________________________________________________

## Background

pypi-profile uses minisign Ed25519 keypairs to sign profile claims. The
secret key is stored in the system keyring (preferred) or as a file on disk
(`~/.pypi_profile/minisign.key`). The public key is embedded in the profile
TOML under `[verification] public_key`.

The current implementation generates a key and moves on. Missing pieces:

- No way to rotate a key without losing all stored proofs.
- No way to recover gracefully from a lost key.
- No way to list all keys in the keyring or on disk.
- No way to inspect which profile a given key belongs to.
- No audit trail of when a key was generated or last used.

______________________________________________________________________

## Feature: `key-info` — inspect a key

**CLI**: `pypi-profile key-info [--key PATH]`

Print information about the active signing key without modifying anything.

Output:

```
Signing key info
  source:      keyring (username="matthewdeanmartin", service="pypi-profile")
  key ID:      A3F92E8B1CD04501
  generated:   2025-11-14  (from key file metadata if available, else "unknown")
  public key:  RWS...  (base64, truncated to 20 chars + "…")

Profile binding
  pypi_profile.toml found: yes  (C:\Users\matth\pypi_profile.toml)
  public_key in TOML:       matches this key ✓    |  mismatch ✗  |  absent
```

If no key is found, print a clear message and exit 0 (not an error — the user
may not have run keygen yet).

**GUI**: Surface as a read-only command in the **Diagnostics** group. Runs
automatically when selected.

______________________________________________________________________

## Feature: `key-list` — list all known keys

**CLI**: `pypi-profile key-list`

Enumerate every key pypi-profile can find, across:

1. All identities in the system keyring under service `"pypi-profile"`.
1. All `*.key` files in `~/.pypi_profile/` and the current directory.

Output (table):

```
Identity / path                              Key ID           Source
matthewdeanmartin                            A3F92E8B1CD04501 keyring
work-account                                 9B12C4D7E3A00812 keyring
~/.pypi_profile/minisign.key                 A3F92E8B1CD04501 disk (matches keyring)
./old-keys/minisign.key                      7F00112233445566 disk
```

Flags:

- `--json` — emit JSON for scripting.

**Implementation note**: reading identities from a keyring requires iterating
credentials, which not all backends support. When enumeration is unavailable,
only the known default identities (`"default"`, the active PyPI username) are
checked and the table notes `(enumeration not supported by keyring backend)`.

______________________________________________________________________

## Feature: `key-rotate` — replace the active key

**CLI**: `pypi-profile key-rotate [SOURCE] [--key-dir PATH] [--keyring-identity NAME] [--force]`

Generates a new keypair, re-signs all `[[profiles]]` entries with the new key,
updates `[verification] public_key` in the TOML, and optionally archives the
old key.

Steps (in order, each atomic or roll-back-safe):

1. Generate new keypair (new files + keyring entry).
1. Update `[verification] public_key` in the TOML.
1. Re-sign all `[[profiles]]` entries (calls `patch_proofs_in_toml` with new key).
1. Archive old secret key to `~/.pypi_profile/minisign.key.YYYYMMDD-HHMMSS.bak`
   and remove the old keyring entry (only if `--no-keep-old` is not set).
1. Print a summary of what changed.

The operation rolls back to the original TOML if step 3 fails, so the old key
remains valid.

**Key rotation does NOT invalidate stored proofs that have already been
published on external sites** — those sites still hold the old proof string.
The new `stored_proof` values in the TOML supersede them for anyone who fetches
the latest TOML, but anyone who cached the page before rotation will see a
mismatch. The command prints a reminder of this.

**GUI**: Surface in a new **Key Management** section within the **Setup** group.
Not read-only; shows a confirmation prompt before executing.

______________________________________________________________________

## Feature: `key-recover` — handle a lost secret key

**CLI**: `pypi-profile key-recover [SOURCE] [--key-dir PATH] [--keyring-identity NAME]`

When the secret key is lost (disk deleted, keyring wiped, machine replaced),
the public key in the TOML is still valid — but new proofs cannot be signed.

This command guides the user through the recovery workflow:

1. **Diagnose**: detect whether the key is truly absent from both disk and keyring.
1. **Generate replacement**: run `keygen` to create a new keypair.
1. **Update TOML**: write the new public key into `[verification]`.
1. **Re-sign proofs**: re-sign all `[[profiles]]` entries with the new key
   (`update-proofs --force`).
1. **Commit reminder**: print a message explaining that the user must commit and
   push the updated TOML, and update any external pages that embedded the old
   proof string.

If the key is found (not actually lost), the command exits early with a message
pointing to `key-rotate` instead.

**Note on external pages**: any `stored_proof` values published before the
loss will appear `invalid` until the external page is updated with the new
proof. `key-recover` lists all affected URLs so the user knows what to update.

______________________________________________________________________

## Feature: `key-export` / `key-import` — move keys between machines

**CLI**:

```
pypi-profile key-export [--key PATH] [--output FILE]
pypi-profile key-import FILE [--keyring-identity NAME] [--force]
```

`key-export` writes the raw secret key bytes to a file (or stdout) for secure
transfer. The output is the same binary format used on disk. A warning is
printed that the exported file must be treated as a secret.

`key-import` reads a previously exported key file and installs it:

- Into the keyring under the given identity.
- To the default disk path (if `--no-keyring` is also passed).

Intended use: set up a CI/CD signing key, or move from one machine to another
without rotating.

______________________________________________________________________

## Feature: profile ↔ key association

`pypi-profile key-info` and `pypi-profile key-list` both report whether each
discovered key matches the public key in any `pypi_profile.toml` found in the
current directory tree (via `find_profile_files()`).

Match logic:

1. Load the secret key.
1. Derive its public key.
1. Compare to `[verification] public_key` in each TOML found.
1. Report `matches`, `mismatch`, or `not checked` (if the TOML has no public
   key).

This answers the question: *"which profile uses this key?"* without requiring
the user to cross-reference manually.

______________________________________________________________________

## GUI: Key Management panel

Add a **Key Management** section to the **Setup** group in the left panel,
with the following commands (in order):

| Label | Command | Read-only |
|------------------|-----------------|-----------|
| Key Info | `key-info` | yes |
| List Keys | `key-list` | yes |
| Rotate Key | `key-rotate` | no |
| Recover Key | `key-recover` | no |
| Export Key | `key-export` | no |
| Import Key | `key-import` | no |

The **Signing key** picker in the top bar is updated after any key management
operation to reflect the new key list.

______________________________________________________________________

## Error messages and UX requirements

All key management commands must:

- Never print raw secret key material to stdout (only to a file on `export`).
- Never exit with a traceback — all expected error conditions (missing key, bad
  password, keyring unavailable) produce a short plain-English message and a
  non-zero exit code.
- Distinguish `key not found` (exit 1, normal state before `keygen`) from
  `key found but unreadable` (exit 2, likely a permissions or encryption issue).
- Include a `--dry-run` flag on all write operations.

______________________________________________________________________

## Implementation order

1. `key-info` — lowest risk, pure read; unblocks diagnosis.
1. `key-list` — read-only enumeration; catches the "which machine has my key?" problem.
1. `key-export` / `key-import` — enables CI and multi-machine setups.
1. `key-rotate` — depends on `key-export` for archiving and `update-proofs` for re-signing.
1. `key-recover` — thin wrapper over `keygen` + `update-proofs`; add after `key-rotate` is stable.
