# pypi-profile

`pypi-profile` is a CLI and small FastAPI app for publishing a maintainer profile from a `pypi_profile.toml`
file.

It is aimed at package publishers who want one place to describe who maintains a project, what packages and
projects they work on, how to contact them, and how to prove control over related external accounts.

## What the package does

`pypi-profile` currently ships:

- a CLI for `init`, `validate`, `inspect`, `serve`, `dump`, `doctor`, `fetch`, `keygen`, `sign`, `verify`,
  `update-proofs`, `build`, `find-profiles`, and `gui`
- a TOML-first profile format for identity, packages, projects, hiring, contact, succession, and verification
  data
- a FastAPI + Jinja2 site renderer with matching JSON endpoints
- a minisign-based proof-of-control flow for external profile URLs

This README documents the **usable core that ships today**. It is intentionally not a roadmap for unfinished
extension work.

## Install

### Recommended: `pipx`

```bash
pipx install pypi-profile
```

### Alternative: `pip`

```bash
pip install pypi-profile
```

### Optional extras

The standard install already includes the web server and signing support.

Install extras if you also want:

- `fetch` for `httpx`-powered live metadata fetches
- `validate` for JSON Resume schema validation
- `all` for both

```bash
pipx install "pypi-profile[all]"
```

Or with `pip`:

```bash
pip install "pypi-profile[all]"
```

### From source

This repository is a `uv` workspace. Run commands from the repo root:

```bash
git clone https://github.com/matthewdeanmartin/matthewdeanmartin_pypi.git
cd matthewdeanmartin_pypi
uv sync --all-extras
uv run pypi-profile --help
```

Use the CLI entry point `pypi-profile`, not `python -m pypi_profile`.

## Usage

The shortest path from zero to a local profile site is:

```bash
pypi-profile init --username your-pypi-name
pypi-profile validate pypi_profile.toml
pypi-profile serve pypi_profile.toml
```

That gives you a starter TOML file and serves the profile locally at `http://127.0.0.1:8000`.

Useful follow-up commands:

```bash
pypi-profile inspect pypi_profile.toml
pypi-profile dump pypi_profile.toml
pypi-profile doctor
```

If you already have source data, you can bootstrap from it:

```bash
pypi-profile init --from-json-resume resume.json --output pypi_profile.toml
pypi-profile init --username your-pypi-name --fetch
```

## Security notes

- Proof-of-control signing is built around a local secret key. Keep that key out of version control.
- `serve --allow-code` is opt-in. Do not enable it for untrusted code.
- Verification proves account co-control, not legal identity or the truth of every profile claim.

For the fuller package docs, see `docs/installation.md`, `docs/usage/quickstart.md`, and `docs/security.md` in
this package directory.

## Legal

Apache license to match the Warehouse license for theme assets.

Not associated with the PSF. Trademarked logos are removed from the profile UI.

[PyPI is a trademark](https://pypi.org/trademarks/) of the Python Software Foundation.

[PyPI's template and theme](https://github.com/pypi/warehouse/blob/main/LICENSE) are Apache-licensed via
Warehouse.
