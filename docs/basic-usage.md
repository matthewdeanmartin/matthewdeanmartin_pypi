# Usage

This page is for the ongoing work after the first quick start: editing the profile, adding claims, re-signing proofs, rebuilding output, and republishing.

## Accepted profile sources

Commands that take a `source` can currently resolve:

- a direct `pypi_profile.toml` path
- a directory containing `pypi_profile.toml`
- a `pyproject.toml` with `[tool.pypi-profile]`
- an installed package name when its distribution exposes `pypi_profile.toml`

## Common maintenance tasks

| Task | GUI | CLI |
|---|---|---|
| Review current data | **Inspect**, **Display TOML**, **Display JSON**, **Validate Config** | `inspect`, `dump`, `validate` |
| Refresh imported data | **Import** | `init --fetch ... --force` or `init --from-json-resume ... --force` |
| Add a new identity site | **Add Identity Site** | edit `[[profiles]]` in `pypi_profile.toml` |
| Generate proof tokens again | **Update Proofs** | `update-proofs` |
| Check published proofs | **Verify Claims** | `verify` |
| Preview live site | **Live Preview** | `serve` |
| Build static site | **Build & Preview** | `build` |

## Add a new identity site

When you add a new `[[profiles]]` entry:

1. add the URL
1. sign it
1. publish the proof token on that page
1. verify it
1. rebuild the static site
1. republish the package if the TOML changed

CLI example:

```bash
pypi-profile update-proofs pypi_profile.toml
pypi-profile verify pypi_profile.toml
pypi-profile build pypi_profile.toml --output dist
```

## Add or edit claims

For normal profile edits:

1. edit `pypi_profile.toml`
1. run `inspect` or `validate`
1. if you changed `[[profiles]]`, run `update-proofs`
1. if you changed public profile content, rebuild the static site
1. republish the package so the updated TOML is in the release

## Sign again

Run `update-proofs --force` when you need to replace existing `stored_proof` values:

```bash
pypi-profile update-proofs pypi_profile.toml --force
```

After that:

1. replace the old tokens on the external pages
1. run `verify`
1. rebuild the static site
1. republish the package

## Rebuild and republish

Any time the committed profile data changes, there are two separate publication surfaces to think about:

1. **Static site**: rebuild with `build` and republish the generated output directory.
1. **Package**: rebuild and republish the Python distribution that ships `pypi_profile.toml`.

## Import fresh data

`fetch-claims` is the read-only comparison command:

```bash
pypi-profile fetch-claims pypi_profile.toml
```

If you want to regenerate the profile from imported sources, use the init-based import flow described in [Quick Start - CLI](quickstart.md) or the **Import** command in [Quick Start - GUI](gui.md).

## Diagnostics and discovery

Useful commands for routine checks:

```bash
pypi-profile doctor
pypi-profile find-profiles
pypi-profile inspect pypi_profile.toml --no-validate
```

## When the key changes

Use [Key management](key-management.md) for:

- `key-info`
- `key-list`
- `key-rotate`
- `key-recover`
- `key-export`
- `key-import`
