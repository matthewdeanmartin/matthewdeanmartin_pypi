# Contributing to pypi-profile

This page covers everything you need to contribute to the `pypi-profile` package itself — the CLI,
server, static builder, signing system, and tests.

## Prerequisites

You need:

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) — the package and workspace manager this project uses
- Git

You do not need a PyPI account or a published package to contribute to the core tool.

## Clone and set up

```bash
git clone https://github.com/matthewdeanmartin/matthewdeanmartin_pypi.git
cd matthewdeanmartin_pypi
uv sync --all-extras
```

`uv sync` installs the entire workspace into a local virtual environment. `--all-extras` includes
optional dependencies like signing tools, the GUI, and development tools. All subsequent commands
must use `uv run` so that they run inside this environment rather than against whatever Python
happens to be on your system `PATH`.

After setup, confirm the CLI works:

```bash
uv run pypi-profile --help
```

## Workspace layout

```
matthewdeanmartin_pypi/
├── pyproject.toml             ← workspace manifest (lists members, nothing else)
├── uv.lock                    ← locked dependency tree for reproducibility
│
├── pypi_profile/              ← the main package (this is what you'll work in)
│   ├── pyproject.toml         ← package metadata and dev dependencies
│   ├── Makefile               ← quality gate targets (lint, test, typecheck, ...)
│   └── pypi_profile/          ← importable source code
│       ├── cli.py             ← argparse entry point
│       ├── server.py          ← FastAPI app factory
│       ├── builder.py         ← static site generator
│       ├── models.py          ← Pydantic data models
│       ├── loader.py          ← TOML loading and plugin discovery
│       ├── claims.py          ← claim encoding/decoding
│       ├── signing.py         ← keypair management and signing
│       ├── verifier.py        ← signature verification
│       ├── fetcher.py         ← PyPI/GitHub/GitLab/Mastodon data fetching
│       ├── importers.py       ← JSON Resume and FUNDING.yml import
│       ├── finder.py          ← pypi_profile.toml file discovery
│       ├── key_management.py  ← key rotate/recover/export/import
│       ├── plugin_spec.py     ← pluggy hook specification
│       ├── plugin_manager.py  ← pluggy plugin discovery
│       ├── wizard.py          ← interactive terminal wizard
│       ├── gui.py             ← Tkinter desktop GUI
│       └── log.py             ← logging configuration
│
├── john_doe/                  ← example profile plugin (test fixture)
├── matthewdeanmartin/         ← author's real profile plugin
└── pypi_ds/                   ← Jinja2 design system and CSS
```

The `pypi_profile/` directory appears twice: once as the workspace member directory (containing
`pyproject.toml` and `Makefile`) and once as the importable Python package inside it. This is
normal Python packaging.

## Running the tests

```bash
uv run pytest pypi_profile/tests/ -v
```

Or through Make:

```bash
uv run make -C pypi_profile test
```

The test suite uses:

- **pytest** — test runner
- **pytest-cov** — coverage measurement
- **pytest-xdist** — parallel test execution (`-n 4` locally, `auto` in CI)
- **pytest-timeout** — kills tests that hang (60-second limit)

Tests that make real network requests are marked `@pytest.mark.slow`. These are skipped in the CI
job but can be run locally with `pytest -m slow`.

## Running the quality gate

The Makefile has a `check` target that runs everything:

```bash
uv run make -C pypi_profile check
```

This runs in order: format check, lint, security audit, tests, smoke dry-run, type check, and
metadata checks. If any step fails the gate stops. `check-ci` is the same but uses the CI
variants of format and test commands.

Individual targets you may want during development:

```bash
uv run make -C pypi_profile format      # auto-format with isort + black + ruff
uv run make -C pypi_profile lint-check  # lint without auto-fixing
uv run make -C pypi_profile typecheck   # mypy strict mode
uv run make -C pypi_profile test        # pytest with coverage
uv run make -C pypi_profile security    # bandit + uv audit + pip-audit
```

## Code conventions

**Type annotations**: All new code must have type annotations. The project runs mypy in strict
mode, which means no `Any` unless explicitly typed, no untyped function parameters, and no ignored
return types. If you are unfamiliar with Python type annotations, the [mypy cheat
sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html) is a good reference.

**Docstrings**: Use Google style. The CI checks docstring coverage with `interrogate`. New public
functions need at minimum a one-line summary. Multi-paragraph docstrings are not required.

**No underscore-prefix private convention**: Do not name functions or variables with a leading
underscore to indicate "private". This convention is not used here. If something is not part of
the public API, that is fine — just do not mark it with `_`. The one exception is truly unused
variables where a `_` as the whole name (not prefix) is idiomatic Python.

**uv run, always**: Never call bare `python` or `pip`. Always use `uv run python` or `uv run pytest`. The project uses a uv workspace and the system Python does not have the dependencies.

**No new files unless necessary**: Prefer editing existing modules. Do not create abstraction
layers, helper utilities, or wrapper modules for one-shot changes. Three similar lines is better
than a premature abstraction.

**Comments only when the why is non-obvious**: Do not add comments that describe what the code
does (the code already does that). Add a comment when there is a hidden constraint, a subtle
invariant, or a workaround for a specific external bug.

## Linting and formatting tools

The project uses:

- **ruff** — fast linter and formatter (replaces flake8, isort, black for most things)
- **black** — code formatter (consistent style, no arguments)
- **isort** — import ordering (profile `black` so it agrees with black)
- **pylint** — deeper lint checks that ruff does not cover
- **mypy** — static type checker
- **bandit** — security-focused linter (checks for common security mistakes)

If you add a `# noqa` or `# type: ignore` comment, add a brief explanation why. Bare suppressions
are harder to review.

## Changing the TOML schema

The TOML schema is defined in `pypi_profile/models.py` as Pydantic models. To add a new field:

1. Add the field to the appropriate Pydantic class with a default value.
1. If the field needs validation (e.g. it must be one of a fixed set of values), use a `Literal`
   type annotation.
1. Update any templates that should render the new field.
1. Add a test that loads a TOML with the new field and checks the value.
1. Document the field in [Data model](../developer/data-model.md).

Example: adding `languages: list[str] = []` to `IdentitySection`:

```python
# models.py
class IdentitySection(BaseModel):
    legal_name: str = ""
    display_name: str = ""
    pypi_username: str = ""
    pronouns: str = ""
    timezone: str = ""
    location: str = ""
    languages: list[str] = []   # new field
```

Because the default is `[]`, existing TOML files that do not have `languages` will still load
without error.

## Adding a CLI command

All commands live in `cli.py`. The pattern is:

1. Add a subparser in the section that defines subparsers.
1. Write a `cmd_yourcommand(args: argparse.Namespace) -> int` function.
1. Register it: `subparsers_map["yourcommand"] = cmd_yourcommand`.
1. Write tests in `pypi_profile/tests/test_cli_commands.py`.

Commands should return `0` on success and `1` on user error. They should check `args.dry_run`
before doing any write or network operation.

## Adding a route to the server

1. Open `server.py`.
1. Add a route handler inside `build_app()` following the existing pattern:

```python
@app.get("/myroute", response_class=HTMLResponse)
async def myroute(request: Request) -> HTMLResponse:
    return render("pypi_profile/myroute.html", {"request": request, "profile": profile})
```

3. Create `pypi_profile/templates/pypi_profile/myroute.html`.
1. Add the route to `STATIC_ROUTES` in `builder.py` so the static builder renders it.
1. Add a test in `test_server.py` that calls the route via `TestClient`.

## The static builder

`builder.py` works by running `TestClient(app).get(route)` for every route in `STATIC_ROUTES` and
writing the response text to a file. This means adding a route automatically makes it available to
the static build — you just need to add it to `STATIC_ROUTES`.

`static_mode=True` is passed to `build_app` when building. This tells the verification page to
use `stored_proof` from the TOML instead of making live HTTP requests.

## Testing the server

The server tests in `test_server.py` use `starlette.testclient.TestClient`:

```python
from starlette.testclient import TestClient
from pypi_profile.server import build_app
from pypi_profile.loader import load_profile

profile = load_profile(Path("john_doe/john_doe/pypi_profile.toml"))
app = build_app(profile)
client = TestClient(app)

def test_homepage():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "John Doe" in resp.text
```

`TestClient` runs the ASGI app in-process. No real HTTP server is started. Tests run fast.

## CI

GitHub Actions runs the quality gate on every push or pull request that touches files in
`pypi_profile/**`, `pypi_ds/**`, `john_doe/**`, or `pyproject.toml`. The workflow file is at
`.github/workflows/build_pypi_profile.yml`.

The CI job:

1. Checks out the code with pinned action SHAs (for supply-chain safety).
1. Sets up Python 3.14 and uv.
1. Runs `uv sync` to install dependencies.
1. Runs `uv run make check-ci`.
1. Runs `uv build` to verify the wheel builds.

If you want to run the same checks locally before pushing:

```bash
uv run make -C pypi_profile check-ci
```

## Submitting a change

1. Create a branch from `main`.
1. Make your changes.
1. Run `uv run make -C pypi_profile check` to confirm everything passes.
1. Open a pull request against `main`.
1. The CI job will run automatically. Fix any failures before asking for review.

The project does not currently have a formal RFC process. For large changes (new features, schema
changes, new commands), open an issue first to discuss the approach before writing the code.
