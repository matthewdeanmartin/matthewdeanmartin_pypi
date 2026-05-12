# john-doe

Example `pypi-profile` plugin — a minimal **data package** that publishes a profile website for a fictional PyPI publisher named John Doe.

This package exists to show how any PyPI publisher can ship their profile as an installable package that `pypi-profile` can serve as a website.

## How it works

1. The package ships a `pypi_profile.toml` inside the `john_doe/` directory.
2. When installed, `pypi-profile` discovers this file via the `pypi_profile.plugins` entry-point.
3. Running `pypi-profile serve john-doe` (the installed package name) boots a local web server for the profile.

## Quick start

```bash
# Install pypi-profile and this example plugin together
pipx install pypi-profile
pipx inject pypi-profile john-doe

# Serve the profile
pypi-profile serve john-doe
```

Or with `uv` from the workspace root:

```bash
uv run --package pypi-profile pypi-profile serve john_doe/john_doe/pypi_profile.toml
```

## Development (from `john_doe/` directory)

```bash
make sync       # install all dependencies
make serve      # serve the profile locally
make validate   # validate pypi_profile.toml
make inspect    # inspect without executing code
make dump       # dump profile as JSON
make init       # re-run wizard to regenerate pypi_profile.toml
make update     # re-fetch live PyPI/GitHub data
make check      # full quality gate
make publish    # publish to PyPI
```

## Does the pypi_profile.toml belong in the wheel?

Yes. The `pypi_profile.toml` is **the data** this package ships. It is included in both the wheel and the sdist so that after installation `pypi-profile` can locate it via `importlib.metadata` (`dist.locate_file("pypi_profile.toml")`). The private signing key is never stored in the TOML — only the public key goes there.
