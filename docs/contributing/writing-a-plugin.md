# Writing a profile plugin package

A **profile plugin** is a Python package that ships a `pypi_profile.toml` file and registers
itself so that `pypi-profile serve` and related commands can find it automatically. This page
walks through building one from scratch.

The `john_doe` directory in this repository is the canonical example. Everything described here
mirrors what you find there.

## What a plugin package is

A profile plugin is a regular Python package with two additions:

1. A `pypi_profile.toml` file bundled inside the wheel.
2. An entry point in the `pypi_profile.plugins` group that points to a module implementing the
   `get_profile_data()` hook.

When the plugin is installed (via `pip install your-profile-package`), `pypi-profile` can
discover it through Python's standard entry-point mechanism and serve or build its profile without
any further configuration.

## Why use a plugin instead of just a TOML file?

A standalone `pypi_profile.toml` file works fine for local use. The plugin approach adds:

- **Installability**: anyone can `pip install your-package` to get your profile data.
- **Hub support**: installed profiles appear automatically in `pypi-profile serve` (hub mode).
- **Package-name resolution**: `pypi-profile serve your-package-name` works without specifying a
  file path.
- **Version history on PyPI**: each release of your profile package is a snapshot of your profile
  at that point in time.

## Package layout

```
my-profile/
├── pyproject.toml
├── README.md
├── LICENSE
└── my_profile/
    ├── __init__.py        ← implements get_profile_data()
    ├── __about__.py       ← version string
    ├── py.typed           ← empty file; tells type checkers about annotations
    └── pypi_profile.toml  ← your profile data
```

## `my_profile/__about__.py`

```python
__version__ = "0.1.0"
```

This file is the single source of truth for the version number. Metadata tools can read it and
sync it into `pyproject.toml` during a release.

## `my_profile/__init__.py`

```python
from pypi_profile.plugin_spec import hookimpl
from my_profile.__about__ import __version__

__all__ = ["__version__"]


@hookimpl
def get_profile_data() -> dict:  # type: ignore[type-arg]
    """Return profile metadata contributed by this plugin."""
    return {
        "author": "My Name",
        "pypi_username": "my-pypi-username",
    }
```

**What `@hookimpl` does**: It decorates `get_profile_data` with a pluggy marker that tells the
`pypi-profile` plugin manager "this module provides an implementation of the `get_profile_data`
hook." Without this decorator the function exists but pluggy ignores it.

**What the return value is**: Currently the return value is informational metadata. The primary
source of profile data is `pypi_profile.toml`, not this function. The hook exists so that future
versions of `pypi-profile` can call plugins for computed or dynamic data.

**The `# type: ignore[type-arg]` comment**: `dict` without type parameters causes a mypy warning
in strict mode. The hook spec uses an unparameterised `dict` (to match what pluggy expects), so
silencing the warning here is the right call. Do not remove it without updating the spec.

## `my_profile/pypi_profile.toml`

This is where your actual profile data goes. See [Data model](../developer/data-model.md) for
the complete field reference. Here is a realistic starting point:

```toml
[profile]
kind = "individual"
display_name = "My Name"
summary = "Python developer focused on data tooling and open-source maintenance."

[identity]
legal_name = "My Full Name"
display_name = "My Name"
pypi_username = "my-pypi-username"
pronouns = "they/them"
timezone = "America/Chicago"
location = "Chicago, IL, USA"

[[profiles]]
kind = "github"
label = "GitHub"
url = "https://github.com/my-github-username"
verification = "self_asserted"
rel_me = true
stored_proof = ""

[[profiles]]
kind = "mastodon"
label = "Mastodon"
url = "https://fosstodon.org/@my-mastodon-username/123456789"
verification = "self_asserted"
rel_me = true
stored_proof = ""

[[packages]]
name = "my-first-package"
role = "maintainer"
state = "active"
summary = "Does something useful."
url = "https://pypi.org/project/my-first-package/"

[[packages]]
name = "my-second-package"
role = "author"
state = "maintained"
summary = "A stable library."
url = "https://pypi.org/project/my-second-package/"

[[contact_methods]]
kind = "email"
label = "Professional email"
value = "me@example.com"
audience = ["hiring", "consulting"]
visibility = "public"

[verification]
public_key = ""
preferred_signature_backend = "minisign"
```

## `pyproject.toml`

```toml
[project]
name = "my-profile"
version = "0.1.0"
description = "PyPI profile for My Name"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [{ name = "My Name", email = "me@example.com" }]
keywords = ["pypi", "profile", "plugin"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = ["pypi-profile>=0.2.0"]

[project.urls]
Repository = "https://github.com/my-github-username/my-profile"
Homepage = "https://my-github-username.github.io/my-profile/"

[project.scripts]
my-profile = "pypi_profile.cli:main"

[project.entry-points."pypi_profile.plugins"]
my_profile = "my_profile"

[build-system]
requires = ["hatchling>=1.27.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["my_profile"]
include = [
    "my_profile/**/*.py",
    "my_profile/py.typed",
    "my_profile/pypi_profile.toml",
    "/README.md",
    "LICENSE",
]

[tool.hatch.build.targets.sdist]
include = ["/README.md", "LICENSE", "/my_profile"]
```

### Key pieces explained

**`[project.entry-points."pypi_profile.plugins"]`**

```toml
[project.entry-points."pypi_profile.plugins"]
my_profile = "my_profile"
```

This is the registration mechanism. The key (`my_profile`) is the plugin name. The value
(`"my_profile"`) is the Python module to import. When Python installs your package, it writes this
to a file at `my_profile-0.1.0.dist-info/entry_points.txt`. The `pypi-profile` tool reads that
file at startup.

The value on the right must be a valid Python import path. It points to the module that has the
`@hookimpl`-decorated `get_profile_data()` function. If your function were in a sub-module, you
would write `"my_profile.hooks"` instead.

**`[tool.hatch.build.targets.wheel] include`**

By default, hatchling only includes Python source files in the wheel. You must explicitly list
`my_profile/pypi_profile.toml` here, or it will not be included and commands like
`pypi-profile serve my-profile` will fail with "cannot find pypi_profile.toml".

**`[project.scripts]`**

```toml
my-profile = "pypi_profile.cli:main"
```

This is optional but convenient. It creates a `my-profile` shell command that is an alias for the
`pypi-profile` CLI. Anyone who installs your package gets both `pypi-profile` (from the
dependency) and `my-profile` (from your package). You can document it in your README as
`my-profile serve` instead of `pypi-profile serve my-profile`.

## Sign your external accounts

After writing the TOML, sign any `[[profiles]]` entries that you want to show as verified:

```bash
# Generate a keypair (once; saves to ~/.pypi_profile/)
pypi-profile keygen

# Sign each external URL
pypi-profile sign controls-url my_profile/pypi_profile.toml \
    --url https://github.com/my-github-username

# Store all proofs in the TOML (so static builds work without the key)
pypi-profile update-proofs my_profile/pypi_profile.toml

# Verify the round-trip
pypi-profile verify my_profile/pypi_profile.toml
```

Commit `my_profile/pypi_profile.toml` after `update-proofs` writes the `stored_proof` values.

## Test locally

Install your package in editable mode and run the server:

```bash
pip install -e .
pypi-profile serve my-profile
```

Open `http://127.0.0.1:8000` and confirm your profile loads correctly.

Check that the hub lists it alongside any other installed profiles:

```bash
pypi-profile serve   # no source argument = hub mode
```

Open `http://127.0.0.1:8000/profiles` to see the listing.

## Write a test

A minimal test confirms the plugin loads and the TOML is valid:

```python
# tests/test_plugin.py
from pathlib import Path
from importlib import resources

from pypi_profile.loader import load_profile


def test_profile_toml_is_valid():
    toml_path = Path(str(resources.files("my_profile").joinpath("pypi_profile.toml")))
    profile = load_profile(toml_path)
    assert profile.identity.pypi_username == "my-pypi-username"
    assert profile.profile.display_name


def test_get_profile_data():
    import my_profile
    data = my_profile.get_profile_data()
    assert "pypi_username" in data
```

`resources.files("my_profile")` is the standard way to locate package data files. It works whether
the package is installed normally or in editable mode.

## Coexistence with other plugins

Multiple profile plugins can be installed at the same time. The hub shows all of them. They do not
conflict because each plugin owns its own `pypi_profile.toml` namespace.

To verify that two plugins work side by side, install them both and run the hub:

```bash
pip install john-doe my-profile
pypi-profile serve
```

Both should appear at `http://127.0.0.1:8000/profiles`.

## Using the plugin as a workspace member (advanced)

If you are developing your profile plugin in a uv workspace alongside `pypi-profile` itself (as
the `john_doe` and `matthewdeanmartin` packages do in this repo), add your package to the
workspace's `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["pypi_profile", "john_doe", "matthewdeanmartin", "my-profile"]
```

Then in your plugin's `pyproject.toml`, point the dependency to the workspace source:

```toml
[tool.uv.sources]
pypi-profile = { workspace = true }
```

This means `uv sync` from the repo root installs your local development version of `pypi-profile`
as the dependency instead of downloading it from PyPI. Useful for developing both at once.

## What `find_profile` accepts

After your package is installed, these all work:

```bash
# By package name (uses dist-info to find bundled pypi_profile.toml)
pypi-profile serve my-profile
pypi-profile build my-profile --output dist
pypi-profile inspect my-profile

# By file path (direct)
pypi-profile serve my_profile/pypi_profile.toml

# By directory (scans for pypi_profile.toml inside)
pypi-profile serve my_profile/
```

The `find_profile()` function in `loader.py` tries each form in order: direct file path,
directory scan, then installed package name.

## Checklist before publishing

- [ ] `pypi_profile.toml` is listed in `[tool.hatch.build.targets.wheel] include`
- [ ] `py.typed` is listed in `[tool.hatch.build.targets.wheel] include`
- [ ] Entry point `[project.entry-points."pypi_profile.plugins"]` is present
- [ ] `@hookimpl` is on `get_profile_data()` in `__init__.py`
- [ ] `pypi-profile verify my_profile/pypi_profile.toml` passes for all signed links
- [ ] `stored_proof` is filled in for all signed `[[profiles]]` entries
- [ ] `public_key` in `[verification]` matches your keypair
- [ ] `pypi-profile build my-profile --output dist` runs without errors
- [ ] `pip install -e . && pypi-profile serve my-profile` shows correct content
- [ ] Tests pass: `pytest tests/`
- [ ] Wheel contains the TOML: `unzip -l dist/*.whl | grep pypi_profile.toml`
