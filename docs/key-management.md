# Key management

This page is for the operational key commands: inspect, list, rotate, recover, export, and import.

## First-time setup

Generate the keypair with:

```bash
pypi-profile keygen
```

What the current code does:

- writes the secret and public key files under `~/.pypi_profile/` unless you override `--key-dir`
- stores the secret key in the system keyring when a usable backend exists, unless you pass `--no-keyring`
- keeps a disk copy as a fallback
- patches `pypi_profile.toml` with the public key when a local file is present in the current directory

## Multi-identity setups

Use `--keyring-identity` when you keep more than one signing key.

```bash
pypi-profile keygen --keyring-identity work
pypi-profile keygen --keyring-identity personal
```

In the CLI, `keygen` tries to default the keyring identity from `identity.pypi_username` in a local `pypi_profile.toml` when one is present. In the GUI, switch keys from the top bar before running signing commands.

## Read-only commands

Inspect the active key:

```bash
pypi-profile key-info
```

List all visible keys:

```bash
pypi-profile key-list
pypi-profile key-list --json
```

## Rotate a key

Rotate when you still have the old key and want to replace it:

```bash
pypi-profile key-rotate pypi_profile.toml
```

This command currently:

1. generates a new keypair
1. updates `[verification].public_key`
1. re-signs all stored proofs
1. archives the old key unless you pass `--no-keep-old`

After rotation:

1. update the proof tokens on the external pages
1. commit the updated TOML
1. rebuild and republish the static site
1. republish the package

## Recover a lost key

Recover when the secret key is gone:

```bash
pypi-profile key-recover pypi_profile.toml
```

This generates a replacement keypair, updates the TOML, and re-signs stored proofs. It also reports which external URLs need their published proof strings replaced.

## Export and import

Export for secure transfer:

```bash
pypi-profile key-export --output backup-minisign.key
```

Import on another machine:

```bash
pypi-profile key-import backup-minisign.key --force
```

Useful flags:

- `--keyring-identity`
- `--key-dir`
- `--no-keyring`
- `--force`

## When to use which command

| Situation | Command |
|---|---|
| Inspect the active key | `key-info` |
| See all available keys | `key-list` |
| Replace a key you still have | `key-rotate` |
| Replace a key you lost | `key-recover` |
| Move a key to another machine | `key-export` then `key-import` |

## Related pages

- [Signing and verification](signing.md) explains what the signatures prove.
- [Usage](basic-usage.md) covers the normal re-sign, rebuild, and republish loop.
