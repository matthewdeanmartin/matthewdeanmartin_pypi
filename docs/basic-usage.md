# Basic usage

## Core workflow

The day-to-day flow is:

1. create or edit `pypi_profile.toml`
1. run `pypi-profile validate`
1. run `pypi-profile serve`
1. optionally use `inspect`, `dump`, `fetch`, `build`, or `gui`

For signed proof-of-control:

1. run `pypi-profile keygen` once to create a keypair
1. paste the printed public key into `[verification]` in your TOML
1. run `pypi-profile sign controls-url` for each external profile URL
1. paste the proof token onto the external page
1. run `pypi-profile update-proofs` to store proofs in the TOML for static builds
1. run `pypi-profile verify` to confirm the round-trip

## Accepted profile sources

Several commands accept a `source`, not just a file path. As implemented today, `pypi-profile` can resolve:

- a direct `pypi_profile.toml` path
- a directory that contains `pypi_profile.toml`
- an installed package name if its distribution exposes `pypi_profile.toml`

## Commands

### `init`

Creates a starter TOML file. The current implementation can also:

- import from JSON Resume with `--from-json-resume`
- merge local `FUNDING.yml` data when present
- fetch live data with `--fetch`

### `validate`

Loads the TOML through the Pydantic schema and reports the principal plus record counts.

### `inspect`

Shows a quick summary without serving the site or dumping all JSON.

### `serve`

Starts the FastAPI app and renders:

- `/`
- `/packages`
- `/projects`
- `/resume`
- `/hiring`
- `/contact`
- `/verification`
- `/succession`

### `dump`

Prints the full validated profile model as JSON.

### `keygen`

Generates a minisign keypair. When `keyring` is installed and a usable backend
is active, the secret key is stored in the system keyring (macOS Keychain,
Windows Credential Manager, libsecret). A disk copy is always written to
`~/.pypi_profile/minisign.key` as a fallback. Prints the public key to paste
into `[verification]` in your TOML. Run this once.

```bash
pypi-profile keygen
pypi-profile keygen --password "passphrase"   # encrypt the disk copy
```

Both `py-minisign` and `keyring` are included in a standard `pypi-profile` install.

### `sign`

Signs a proof-of-control claim for an external URL and prints the
`pypi-profile-proof:` token to paste onto that page. Loads the secret key from
the system keyring if available, otherwise from disk.

```bash
pypi-profile sign controls-url pypi_profile.toml \
    --url https://github.com/yourname
```

Requires `py-minisign`.

### `update-proofs`

Signs every `[[profiles]]` URL that lacks a `stored_proof` and writes the proof
strings into the TOML in-place. Run this locally after signing so that static
builds (which do not have access to the private key) can still include proof
strings in the rendered `/verification` page.

```bash
pypi-profile update-proofs pypi_profile.toml
pypi-profile update-proofs pypi_profile.toml --force   # re-sign everything
```

### `verify`

Fetches each declared `[[profiles]]` URL and checks for a valid proof token.

```bash
pypi-profile verify pypi_profile.toml
```

Reports each claim as `verified`, `unverified`, `invalid`, or `expired`.

### `doctor`

Checks required and optional runtime dependencies such as `fastapi`, `uvicorn`,
`pydantic`, `httpx`, `pyyaml`, and `py-minisign`. Also reports whether a secret
key file is present in `~/.pypi_profile/`.

### `fetch`

Fetches live metadata for the declared profile:

- PyPI packages for the profile owner
- per-package PyPI metadata
- GitHub profile, repos, and `FUNDING.yml`
- GitLab profile
- Mastodon profile

Fetch results are cached in `.pypi_profile_cache/`.

### `build`

Generates a static site from the profile so it can be published without running a
live FastAPI server.

```bash
pypi-profile build pypi_profile.toml --output dist
```

Use `--base-url` when publishing below a subpath such as a GitHub Pages project
site.

### `find-profiles`

Scans a directory tree for profile files.

It currently finds:

- files named `pypi_profile.toml`
- `pyproject.toml` files that contain `[tool.pypi-profile]`

```bash
pypi-profile find-profiles
pypi-profile find-profiles path\to\workspace
```

### `gui`

Launches the Tkinter desktop GUI for the most common local workflows:

- creating a starter profile
- validating and inspecting a profile
- serving the site locally
- generating keys
- signing claims and updating stored proofs

See [GUI](gui.md) for the layout and usage model.

## Data model sections

The current schema covers:

- `[profile]`
- `[identity]`
- `[[humans]]`
- `[[profiles]]`
- `[[contact_methods]]`
- `[[packages]]`
- `[[projects]]`
- `[[work_experience]]`
- `[hiring]`
- `[contracting]`
- `[contact_preferences]`
- `[succession]`
- `[verification]`

That is enough to publish a useful maintainer or team profile today, even though some of the richer verification and export features are still roadmap items.

### `[[profiles]]` fields

Each profile link supports these fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `kind` | string | required | Platform identifier, e.g. `"github"`, `"mastodon"` |
| `label` | string | required | Display label |
| `url` | string | required | Full URL of the external profile or post |
| `verification` | string | `"self_asserted"` | Claim status: `"self_asserted"`, `"verified"`, etc. |
| `rel_me` | bool | `false` | Render `rel="me"` on the anchor; enables Mastodon-style link verification |
| `stored_proof` | string | `""` | Pre-signed proof token written by `update-proofs`; used by static builds |

Set `rel_me = true` on any link that should carry `rel="me"` — typically Mastodon
and personal website links. Set `stored_proof` by running
`pypi-profile update-proofs` rather than editing it by hand.
