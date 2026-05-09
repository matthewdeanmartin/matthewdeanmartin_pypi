# AGENTS.md — guidance for AI contributors

## Always use `uv run` — never bare `python`

This is a **uv workspace**. The system Python does not have the project dependencies installed.
Every Python invocation must go through `uv run`.

```bash
# CORRECT
uv run pytest
uv run python -c "from pypi_profile.importers import from_json_resume; ..."
uv run pypi-profile --help

# WRONG — will fail with ModuleNotFoundError or the wrong interpreter
python -m pytest
python -c "from pypi_profile.importers import ..."
pip install ...
.venv/Scripts/python ...
.venv/bin/python ...
```

If any command fails with "module not found" or "command not found":

```bash
uv sync --all-extras   # then retry with uv run
```

## Workspace layout

```
matthewdeanmartin_pypi/       ← repo root (run all uv commands from here)
├── pyproject.toml            ← workspace manifest only ([tool.uv.workspace])
├── pypi_profile/             ← main package + CLI  (import: pypi_profile)
├── john_doe/                 ← example profile plugin
├── matthewdeanmartin/        ← author's own profile package
└── pypi_ds/                  ← Jinja2 design system
```

Run `uv run` from the **repo root** to resolve all workspace members at once.
Running from inside a sub-package directory also works.

## Name collision warning

`python -m pypi_profile` fails because Python resolves the `pypi_profile/` *directory* before
the installed package. Use the CLI entry point instead:

```bash
uv run pypi-profile --help
```

Or invoke a specific module with a full dotted path:

```bash
uv run python -c "from pypi_profile.cli import main; main()"
```

## Common commands

```bash
uv sync --all-extras                        # install / refresh all dependencies
uv run pytest pypi_profile/tests/ -v       # main package tests
uv run pytest john_doe/tests/ -v           # example plugin tests
uv run pypi-profile init --help
uv run pypi-profile fetch <toml-path>
uv run pypi-profile serve <toml-path>
uv run make check                           # lint + typecheck + test + security
uv run make lint
uv run make typecheck
uv run make test
```

## Running inline Python

```bash
uv run python -c "
from pypi_profile.importers import from_json_resume
from pathlib import Path
data = from_json_resume(Path('john_doe/resume.json'))
print(data['profile']['display_name'])
"
```

## Python conventions

- All new code must have type annotations.
- Docstrings follow **Google style**.
- Line length is 120 characters (black + ruff configured to match).
- Leading `_` means "unused variable", not "private". Use `__all__` to declare public surfaces.

## Tests

- Test files live in `tests/` inside each sub-package.
- Plain `def test_*` functions; no class wrapper required.
- `hypothesis` is available for property-based tests.

## Commits

Prefer a single clean commit per logical change.
