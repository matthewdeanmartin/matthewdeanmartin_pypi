# pypi-profile

Pypi lacks a profile or a way to tie your identity to anything outside of pypi, other than a build server, via trusted
publishing.

`pypi-profile` is a tool for uses a `pypi_profile.toml` file to track signatures that can be verified at other websites.

It supports other use cases, such as resume display, contact info, package lists, and successor information.

## What the package does

`pypi-profile` currently ships:

- GUI for quick start and feature discovery.
- a CLI for `init`, `validate`, `inspect`, `serve`, `dump`, `doctor`, `fetch`, `keygen`, `sign`, `verify`,
  `update-proofs`, `build`, `find-profiles`, `gui`, and key management (`key-info`, `key-list`, `key-rotate`,
  `key-recover`, `key-export`, `key-import`)
- a TOML-first profile format for identity, packages, projects, hiring, contact, succession, and verification
  data
- a live website for validating signatures
- a static website for validating signatures within the constraints of javascript and CORS.

## Install

### Recommended: `pipx`

```bash
pipx install pypi-profile
```

### Alternative: `pip`

```bash
pip install pypi-profile
```

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
pypi-profile inspect pypi_profile.toml
pypi-profile serve pypi_profile.toml
```

That gives you a starter TOML file and serves the profile locally at `http://127.0.0.1:8000`.

Useful follow-up commands:

```bash
pypi-profile dump pypi_profile.toml
pypi-profile doctor
```

If you already have source data, you can bootstrap from it:

```bash
pypi-profile init --from-json-resume resume.json --output pypi_profile.toml
pypi-profile init --from-skip-trace skip-trace-profile.json --output pypi_profile.toml
pypi-profile init --username your-pypi-name --fetch
```

To generate starter profiles for identities discovered across a virtual environment:

```bash
pypi-profile generate-missing --venv .venv --output-dir generated-profiles
```

## Security notes

- Proof-of-control signing is built around a local secret key. Keep that key out of version control.
- `serve --allow-code` is opt-in. Do not enable it for untrusted code.
- Verification proves account co-control, not legal identity or the truth of every profile claim.

## Legal

Apache license to match the Warehouse license for theme assets.

Not associated with the PSF. Trademarked logos are removed from the profile UI.

[PyPI is a trademark](https://pypi.org/trademarks/) of the Python Software Foundation.

[PyPI's template and theme](https://github.com/pypi/warehouse/blob/main/LICENSE) are Apache-licensed via
Warehouse.

## Project Links

- [GitHub](https://github.com/matthewdeanmartin/matthewdeanmartin_pypi)
- [PyPI](https://pypi.org/project/pypi-profile/)
- [Documentation](https://matthewdeanmartin-pypi.readthedocs.io/en/latest/)
- [Bug Tracker](https://github.com/matthewdeanmartin/matthewdeanmartin_pypi/issues)
- [Change Log](https://github.com/matthewdeanmartin/matthewdeanmartin_pypi/blob/main/pypi_profile/CHANGELOG.md)
