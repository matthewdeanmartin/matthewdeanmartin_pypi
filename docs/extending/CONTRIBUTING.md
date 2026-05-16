# Contributing

## Setup

This repository is a `uv` workspace. Clone the repo and install all workspace dependencies from the repo root:

```bash
git clone https://github.com/matthewdeanmartin/matthewdeanmartin_pypi.git
cd matthewdeanmartin_pypi
uv sync --all-extras
```

## Common package commands

Run package-specific checks from the workspace root:

```bash
uv run make -C pypi_profile lint
uv run make -C pypi_profile typecheck
uv run make -C pypi_profile test
uv run make -C pypi_profile check
```

## Docs updates

The package docs live under `pypi_profile/docs/` and are configured by `pypi_profile/mkdocs.yml`.

When changing user-facing behavior, update:

- `README.md` for the package summary shown on GitHub and PyPI
- `docs/installation.md` for install guidance
- `docs/usage/quickstart.md` for the shortest working flow
- `docs/security.md` for signing, verification, and safe operation guidance
