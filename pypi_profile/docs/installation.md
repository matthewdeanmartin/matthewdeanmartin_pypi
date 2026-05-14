# Installation

## Recommended: `pipx`

For most users, `pipx` is the cleanest way to install the CLI:

```bash
pipx install pypi-profile
```

## Alternative: `pip`

If you prefer a regular environment:

```bash
pip install pypi-profile
```

## Optional extras

The standard install already includes the FastAPI server, Jinja templates, `keyring`, and `py-minisign`.

Optional extras add:

- `fetch` for `httpx`-powered live metadata fetches
- `validate` for JSON Resume schema validation
- `all` for both

```bash
pip install "pypi-profile[all]"
```

Or with `pipx`:

```bash
pipx install "pypi-profile[all]"
```

## From source

This repository is a `uv` workspace. Clone the repo and run from the workspace root:

```bash
git clone https://github.com/matthewdeanmartin/matthewdeanmartin_pypi.git
cd matthewdeanmartin_pypi
uv sync --all-extras
uv run pypi-profile --help
```

If you only want to work on the package locally, package-level checks can still be run from the repo root:

```bash
uv run make -C pypi_profile test
uv run make -C pypi_profile check
```

## Important command note

Use the CLI entry point:

```bash
uv run pypi-profile --help
```

Do **not** use `python -m pypi_profile`; the workspace directory and importable package share the same name, and
the CLI entry point is the reliable path.

## After install

Once installed, continue with [Quick start](usage/quickstart.md) and then read [Security](security.md) before you
publish signed proofs.
