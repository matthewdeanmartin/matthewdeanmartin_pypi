# Basic usage

## Core workflow

The current day-to-day flow is:

1. create or edit `pypi_profile.toml`
2. run `pypi-profile validate`
3. run `pypi-profile serve`
4. optionally use `inspect`, `dump`, or `fetch`

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

### `doctor`

Checks required and optional runtime dependencies such as `fastapi`, `uvicorn`, `pydantic`, `httpx`, `pyyaml`, and `py-minisign`.

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
