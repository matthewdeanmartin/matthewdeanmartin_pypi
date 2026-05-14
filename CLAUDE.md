# CLAUDE.md — Claude Code guidance for this repo

## Never use prefix of _ to mean private, it is okay to use it to mean unused.

## Always use `uv run` — never bare `python`

This is a **uv workspace**. The system Python does not have the project dependencies installed.
Every Python invocation must go through `uv run` so that uv selects the correct virtualenv and
makes the workspace packages importable.

```bash
# CORRECT
uv run pytest
uv run python -c "from pypi_profile.importers import from_json_resume; ..."
uv run pypi-profile --help

# WRONG — will fail with ModuleNotFoundError or wrong interpreter
python -m pytest
python -c "from pypi_profile.importers import ..."
.venv/Scripts/python ...        # fragile, avoid
.venv/bin/python ...            # fragile, avoid
```

If you get `ModuleNotFoundError` for any project package, the fix is always:

```bash
uv sync --all-extras
```

then retry with `uv run`.

## Workspace layout

```
matthewdeanmartin_pypi/       ← repo root (run uv commands from here)
├── pyproject.toml            ← workspace manifest only, no code
├── pypi_profile/             ← main package + CLI (pypi-profile)
│   ├── pyproject.toml
│   ├── pypi_profile/         ← importable package
│   └── tests/
├── john_doe/                 ← example profile plugin
│   ├── pyproject.toml
│   └── john_doe/
├── matthewdeanmartin/        ← author's own profile package
│   ├── pyproject.toml
│   └── matthewdeanmartin/
└── pypi_ds/                  ← design system (Jinja2 + static assets)
```

`uv run` from the **repo root** resolves the whole workspace. Running from inside a sub-package
directory works too, but the root is the canonical location.

## Name collision warning

The importable package is `pypi_profile` (underscore).
The workspace member directory is also `pypi_profile/`.
`python -m pypi_profile` does **not** work because Python resolves the directory before the
installed package. Use `uv run pypi-profile` (the CLI entry point) or
`uv run python -c "from pypi_profile.cli import main; main()"` instead.

## Common commands

```bash
uv sync --all-extras            # install / refresh all dependencies
uv run pytest pypi_profile/tests/            # run tests for the main package
uv run pytest john_doe/tests/               # run tests for the example plugin
uv run pypi-profile --help                  # CLI help
uv run pypi-profile init --fetch --username <name>   # init with live fetch
uv run pypi-profile fetch <path/to/pypi_profile.toml>
uv run pypi-profile serve <path/or/package>
uv run make check               # full quality gate (lint, typecheck, test, security)
```

## Running inline Python for quick checks

```bash
uv run python -c "
from pypi_profile.importers import from_json_resume
from pathlib import Path
data = from_json_resume(Path('john_doe/resume.json'))
print(data['profile']['display_name'])
"
```

## Tests

Tests live in `<member>/tests/`. Always run pytest through uv from the repo root or the
sub-package directory:

```bash
# from repo root
uv run pytest pypi_profile/tests/ -v

# or cd into the sub-package — uv still finds the workspace venv
cd pypi_profile
uv run pytest tests/ -v
```

The `test_server.py` tests require `fastapi` and `httpx` to be importable; if they error with
`ModuleNotFoundError: No module named 'fastapi'` run `uv sync --all-extras` from the root.
