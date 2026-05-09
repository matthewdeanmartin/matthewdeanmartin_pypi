# matthewdeanmartin_pypi

Monorepo for the **pypi-profile** project — the missing PyPI profile page.

Bata: Rapidly evolving.

## Packages

| Package                                    | Description                                                |
|--------------------------------------------|------------------------------------------------------------|
| [`pypi_profile/`](pypi_profile/)           | Main CLI (`pipx install pypi-profile`). Plugin host.       |
| [`matthewdeanmartin/`](matthewdeanmartin/) | Data/plugin package for Matthew Martin's PyPI profile.     |
| [`john_doe/`](john_doe/)                   | Example/test plugin — demonstrates two plugins coexisting. |

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
