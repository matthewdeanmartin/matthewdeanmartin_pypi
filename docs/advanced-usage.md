# Advanced usage: pluggy plugins

This page describes the pluggy extension story as it exists in the current codebase.

## What exists today

`pypi-profile` currently ships:

- a pluggy plugin manager that discovers `pypi_profile.plugins` entry points
- a single hook spec: `get_profile_data() -> dict[str, Any]`
- example plugin packages in this repo: `john_doe` and `matthewdeanmartin`

The hook spec today is intentionally small:

```python
@hookspec
def get_profile_data(self) -> dict[str, Any]:
    ...
```

## What plugin packages look like now

The current example packages register an entry point and include `pypi_profile.toml` in the built wheel:

```toml
[project.entry-points."pypi_profile.plugins"]
john_doe = "john_doe"

[tool.hatch.build.targets.wheel]
include = [
    "john_doe/**/*.py",
    "john_doe/pypi_profile.toml",
]
```

That matches the current code in this repo:

- pluggy discovery is implemented in `plugin_manager.py`
- the hook spec lives in `plugin_spec.py`
- example packages expose `get_profile_data()` from their package root

## What works well right now

The current plugin/package path is useful for:

1. publishing a profile package that ships `pypi_profile.toml`
1. installing that package and targeting it by package name
1. experimenting with lightweight data hooks

Because `find_profile()` can resolve installed distributions by name, commands such as these work when the package is installed and exposes `pypi_profile.toml`:

```bash
pypi-profile inspect your-package-name
pypi-profile serve your-package-name
pypi-profile build your-package-name --output dist
```

## What is still limited

The pluggy surface is not yet the broad extension API described in the spec.

As of the current code:

- there is no shipped hook surface for extra pages, extra routes, validators, verification backends, or template globals
- the main rendering and build flow does not yet expose a large plugin-driven feature set
- `--allow-code` exists on `serve` and is surfaced in the GUI, but the overall code-execution model is still evolving

Treat the current plugin layer as **early infrastructure**, not a stable extension contract.

## Data packages versus plugin hooks

These are related but not identical:

- **data package**: a Python distribution that ships `pypi_profile.toml`
- **pluggy plugin**: an installed package registered in `pypi_profile.plugins`

Today, the practical packaging value mostly comes from shipping `pypi_profile.toml` in the distribution. The pluggy hook is present, but still minimal.

## JSON Resume import

JSON Resume import is not a pluggy feature. It is built into `init`.

Use the dedicated page for field-mapping details:

- [JSON Resume Import](skills/json-resume.md)
