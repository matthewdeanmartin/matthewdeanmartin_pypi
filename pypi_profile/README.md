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


## Python 3.15 final verification — 2026-10-09

**Core supported on the tested Windows x86-64 environment:** all 347 tests pass on Python 3.15.0 final with stable published dependency wheels, including Pydantic 2.14.0/core 2.50.0. Both the local wheel and published PyPI 0.3.0 pass installed CLI help/version and real localhost HTTP checks. Existing stdlib JSON/TOML serialization works without orjson or rtoml; dependency prereleases are no longer needed.

The optional `fast` extra still lacks a compatible rtoml wheel. The complete development group remains wheels-only blocked by PyYAML and source-only linkcheckmd. The workspace lock was refreshed with `uv lock --upgrade` and passes `uv lock --check`; this does not certify all development dependencies. No runtime code change, native compilation, GitHub job or upstream report was needed.

GitHub Actions now has a separate Python 3.15.0 final application-test job for Linux and Windows. It requires stable published dependency wheels and tests the existing portable JSON/TOML backends. The broader quality gates and publishing builds stay on Python 3.14 while developer-wheel blockers remain. The Python setup action is upgraded to pinned v7.0.0.

## Python 3.15 verification — 2026-10-04 (historical)

347 tests and installed CLI help pass on 3.15.0rc3 with actual Pydantic 2.14.0b2/core 2.49.0 wheels, and on Python 3.14.7. Stable RC3 Pydantic core is wheel-blocked. The optional fast extra remains RC3 wheel-blocked by rtoml; existing portable serialization passes without orjson/rtoml. The CLI subprocess test now runs the installed executable from the tested environment outside the checkout, avoiding implicit workspace installs. No new runtime fallback was added.

Dependencies were required to have published wheels; own pure-Python workspace wheels were built locally without build isolation. Locks were refreshed with uv lock --upgrade. Full developer stacks remain separately wheel-blocked (PyYAML or source-only linkcheckmd). No upstream reports or GitHub jobs were sent; bug filing belongs to the human operator.
