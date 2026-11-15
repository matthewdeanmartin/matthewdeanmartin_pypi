# Contributing

## Repo layout

This repository is a `uv` workspace with three main members:

- `pypi_profile/` - the main CLI and renderer
- `matthewdeanmartin/` - a real profile/plugin package
- `john_doe/` - an example profile/plugin package used for tests and demos

## Local setup

For work on `pypi-profile`, use the package directory:

```bash
cd pypi_profile
uv sync
```

Run the CLI through `uv run`:

```bash
uv run pypi-profile --help
```

## Common commands

```bash
uv run make check
uv run pytest tests -v
uv run mkdocs build
```

## Working conventions

- use type annotations on new Python code
- keep docstrings in Google style
- prefer `uv run` over bare `python`
- keep docs aligned with the shipped behavior, and call out roadmap items explicitly when they come from `spec/`

## CI and publishing

The root repository now has separate GitHub Actions workflows for:

- building `pypi_profile`
- building `matthewdeanmartin`
- publishing `pypi_profile`
- publishing `matthewdeanmartin`

That separation keeps package feedback clearer in this workspace monorepo.

### Releasing pypi-profile

Record user-facing changes in `pypi_profile/CHANGELOG.md` and run
`make -C pypi_profile changelog-check`. A push to `main` that changes
`pypi_profile/` creates or refreshes a draft GitHub release. You can also run
`make -C pypi_profile draft-gha` to dispatch that draft workflow.

Review and publish the draft release tagged `pypi-profile-vX.Y.Z` on GitHub.
The release workflow checks that its tag points at the current `main`, then
uses keepachangelog-manager to promote `[Unreleased]`, bump
`pypi_profile/pyproject.toml` and `pypi_profile/pypi_profile/__about__.py`,
and open a release PR. It refreshes the workspace lockfile on that branch,
runs the package checks, and uploads the built distribution to PyPI. Merge
the release PR after the upload succeeds. Releases with other tag prefixes
do not start this package's workflow.
