# Plugin system

`pypi-profile` uses [pluggy](https://pluggy.readthedocs.io/) to discover installed profile
packages. This page explains how that works.

## What pluggy is

pluggy is a plugin framework built by the pytest team. The central idea is:

- The **host application** (here: `pypi-profile`) defines a set of **hook specs** — function
  signatures that plugins may implement.
- **Plugin packages** implement those functions and register themselves via a Python entry point.
- The framework discovers all registered plugins at runtime and calls them when the host asks.

You do not need to know how pluggy works internally to write a plugin. The pattern is simple:
implement a function with the right name, add an `@hookimpl` decorator, and register it.

## Hook specification

The spec lives in `pypi_profile/plugin_spec.py`:

```python
import pluggy

hookspec = pluggy.HookspecMarker("pypi_profile")
hookimpl = pluggy.HookimplMarker("pypi_profile")

class PypiProfileSpec:
    @hookspec
    def get_profile_data(self) -> dict:
        """Return a dict of profile data contributed by this plugin."""
```

`hookspec` marks functions that plugins *may* implement. `hookimpl` marks the implementations
in plugin modules. Both markers use the string `"pypi_profile"` as a namespace so they do not
collide with other pluggy-based tools.

Currently there is one hook: `get_profile_data()`. Its return value is informational — plugins
can return a dict, but the primary mechanism for profile data is the bundled `pypi_profile.toml`
file described below.

## Plugin discovery

`pypi_profile/plugin_manager.py` builds the plugin manager at startup:

```python
import importlib.metadata
import pluggy
from pypi_profile.plugin_spec import PypiProfileSpec

def build_plugin_manager() -> pluggy.PluginManager:
    pm = pluggy.PluginManager("pypi_profile")
    pm.add_hookspecs(PypiProfileSpec)
    for ep in importlib.metadata.entry_points(group="pypi_profile.plugins"):
        plugin_module = ep.load()
        pm.register(plugin_module)
    return pm
```

`importlib.metadata.entry_points` is a Python standard library function that reads the
`dist-info` metadata of every installed package in the current environment and returns all
entry points that belong to the group `"pypi_profile.plugins"`. This is how pytest discovers test
plugins, how Babel discovers extension packages, and how many other Python tools work.

## How profile packages are discovered for the hub

Beyond the pluggy hook, `loader.py`'s `discover_installed_profiles()` function finds installed
profiles for the hub (`/profiles` listing and `serve` with no source argument). It uses two methods:

**Method 1: Entry point registration (preferred)**

```python
for entry_point in meta.entry_points(group="pypi_profile.plugins"):
    module_name = entry_point.value.partition(":")[0]
    candidate = Path(str(resources.files(module_name).joinpath("pypi_profile.toml")))
    if candidate.exists():
        seen_paths[candidate.resolve()] = entry_point.dist.name
```

`resources.files(module_name)` is the standard way to access package data files without caring
where on disk the package is installed. It works with regular installs, editable installs, and
zipimport.

**Method 2: Distribution scan (fallback)**

```python
for dist in meta.distributions():
    for package_file in dist.files or []:
        if package_file.name == "pypi_profile.toml":
            candidate = Path(str(dist.locate_file(package_file)))
            if candidate.exists():
                seen_paths.setdefault(candidate.resolve(), dist.metadata.get("Name", ...))
```

This scans every installed package for a file literally named `pypi_profile.toml`. It is slower
but catches packages that ship the TOML without registering an entry point.

## What a minimal plugin package looks like

The `john_doe` package in this repo is the canonical example:

```
john_doe/
├── pyproject.toml
├── john_doe/
│   ├── __init__.py        ← implements get_profile_data() with @hookimpl
│   ├── __about__.py       ← version string
│   ├── py.typed           ← marker file for type checkers
│   └── pypi_profile.toml  ← bundled profile data
└── tests/
    └── test_plugin.py
```

`john_doe/__init__.py`:

```python
from pypi_profile.plugin_spec import hookimpl

@hookimpl
def get_profile_data() -> dict:
    return {
        "author": "John Doe",
        "pypi_username": "john_doe",
        "github": "https://github.com/john_doe",
    }
```

`john_doe/pyproject.toml` (relevant sections):

```toml
[project]
name = "john-doe"
dependencies = ["pypi-profile>=0.1.0"]

[project.entry-points."pypi_profile.plugins"]
john_doe = "john_doe"

[tool.hatch.build.targets.wheel]
include = [
    "john_doe/**/*.py",
    "john_doe/py.typed",
    "john_doe/pypi_profile.toml",
    "/README.md",
    "LICENSE",
]
```

The critical piece is the entry point:

```toml
[project.entry-points."pypi_profile.plugins"]
john_doe = "john_doe"
```

This says: "when the group `pypi_profile.plugins` is queried, I provide a plugin called
`john_doe` implemented by the module `john_doe`." When you `pip install john-doe`, Python records
this in the package's `dist-info/entry_points.txt` and it becomes visible to `importlib.metadata`.

## What the TOML file inside the package does

The `pypi_profile.toml` file bundled inside the wheel is what actually provides profile data to
the hub and to commands like `pypi-profile serve john-doe`. When you run:

```bash
pypi-profile serve john-doe
```

`loader.find_profile("john-doe")` calls `meta.distribution("john-doe")`, then
`dist.locate_file("pypi_profile.toml")` to get the path to the bundled TOML, and
`load_profile(that_path)` to parse it.

For this to work, `pypi_profile.toml` must be included in the built wheel. With hatchling, add it
to the `include` list in `[tool.hatch.build.targets.wheel]`.

## The `py.typed` marker

`py.typed` is an empty file that tells type checkers (mypy, pyright) that the package contains
type annotations. Without it, type checkers ignore the package's type information. Include it in
your wheel alongside the `.py` files.

## Coexistence of multiple plugins

Multiple profile packages can be installed at the same time. The hub lists all of them at
`/profiles`. Each profile is independent — they do not share data, they do not conflict, and
installing one does not break another.

The `serve` command without a source argument starts a hub that shows all of them:

```bash
pypi-profile serve
```

The command with a source argument serves only one:

```bash
pypi-profile serve john-doe
pypi-profile serve matthewdeanmartin
```
