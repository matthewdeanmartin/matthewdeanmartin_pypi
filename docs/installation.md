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

The base package is enough for authoring, validating, inspecting, and serving profiles.

Optional network and signing behavior is still evolving. If `doctor` reports optional dependencies missing, that is not necessarily an installation failure; it may just mean those feature areas are not installed or not fully shipped yet.
