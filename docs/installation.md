# Installation

## End users

### Recommended: `pipx`

```bash
pipx install pypi-profile
```

### Alternative: `pip`

```bash
pip install pypi-profile
```

## From this repository

This repo is a `uv` workspace.

For local work on the main package:

```bash
git clone https://github.com/matthewdeanmartin/matthewdeanmartin_pypi.git
cd matthewdeanmartin_pypi\pypi_profile
uv sync
uv run pypi-profile --help
```

## Optional capabilities

The base package is enough for authoring, validating, inspecting, and serving
profiles.

### Signing and verification

The `keygen`, `sign`, and `verify` commands require `py-minisign`:

```bash
pipx install "pypi-profile[sign]"
```

If you already have `pypi-profile` installed via `pipx`, inject the extra
dependency without reinstalling:

```bash
pipx inject pypi-profile py-minisign
```

### Live fetch

`fetch`, and the `--fetch` flag on `init`, use `httpx` for faster HTTP
requests. Install the `fetch` extra to pull it in:

```bash
pipx install "pypi-profile[fetch]"
```

### Everything at once

```bash
pipx install "pypi-profile[all]"
```

Run `pypi-profile doctor` after installation to confirm which optional
dependencies are available.
