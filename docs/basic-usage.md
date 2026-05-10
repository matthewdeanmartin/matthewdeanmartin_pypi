# Basic usage

## Core workflow

The day-to-day flow is:

1. create or edit `pypi_profile.toml`
2. run `pypi-profile validate`
3. run `pypi-profile serve`
4. optionally use `inspect`, `dump`, or `fetch`

For signed proof-of-control:

1. run `pypi-profile keygen` once to create a keypair
2. paste the printed public key into `[verification]` in your TOML
3. run `pypi-profile sign controls-url` for each external profile URL
4. paste the proof token onto the external page
5. run `pypi-profile verify` to confirm the round-trip

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

Generates a minisign keypair and writes it to `~/.pypi_profile/`. Prints the
public key to paste into `[verification]` in your TOML. Run this once; protect
the secret key file.

```bash
pypi-profile keygen
pypi-profile keygen --password "passphrase"   # encrypt the secret key
```

Requires `py-minisign`. Install with `pipx install "pypi-profile[sign]"`.

### `sign`

Signs a proof-of-control claim for an external URL and prints the
`pypi-profile-proof:` token to paste onto that page.

```bash
pypi-profile sign controls-url pypi_profile.toml \
    --url https://github.com/yourname
```

Requires `py-minisign`.

### `verify`

Fetches each declared `[[profiles]]` URL and checks for a valid proof token.

```bash
pypi-profile verify pypi_profile.toml
```

Reports each claim as `verified`, `unverified`, `invalid`, or `expired`.
Requires `py-minisign`.

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
