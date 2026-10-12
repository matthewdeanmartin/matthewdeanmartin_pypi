# matthewdeanmartin_pypi

Monorepo for the **pypi-profile** project — the missing PyPI profile page.

Bata: Rapidly evolving.

## Packages

| Package | Description |
|--------------------------------------------|------------------------------------------------------------|
| [`pypi_profile/`](pypi_profile/) | Main CLI (`pipx install pypi-profile`). Plugin host. |
| [`matthewdeanmartin/`](matthewdeanmartin/) | Data/plugin package for Matthew Martin's PyPI profile. |
| [`john_doe/`](john_doe/) | Example/test plugin — demonstrates two plugins coexisting. |

## Structure

```
matthewdeanmartin_pypi/
├── pyproject.toml          # uv workspace root
├── Makefile                # delegates to per-package Makefiles
├── pypi_profile/           # pypi-profile package
├── matthewdeanmartin/      # matthewdeanmartin plugin package
└── john_doe/               # john_doe example plugin package
```

## Quickstart

```bash
# Install all packages and dev dependencies into shared venv
uv sync --all-packages

# Run all tests
make test

# Run checks for one package
cd pypi_profile && make check
```

## Plugin system

`pypi-profile` uses [pluggy](https://pluggy.readthedocs.io/) with the entry-point group `pypi_profile.plugins`.
Any installed package that registers this entry point and implements `get_profile_data()` will be discovered
automatically.

## Prior Art

- Keyoxide - https://docs.keyoxide.org/
- Keybase - https://keybase.io/matthewmartin
-


## HTTPX2 migration verification (2026-10-04)

Direct profile-test and template dependency declarations use HTTPX2. Profile package passes all 347 tests on RC3 pre and 3.14.7. Hosting/server acceleration extras not certified; RC3 stable not run.

Dependency locks upgraded and checked. Published dependency wheels only; no native builds or GitHub jobs. Application HTTPX2 objects remain separate from third-party HTTPX objects. Current HTTPX2 releases use the OS trust store. Experimental RC3 tests may require Pydantic prerelease wheels; stable support is reported separately. Changes local; human operators decide releases and upstream reports.
