# Architecture overview

This page describes how the modules in `pypi_profile/pypi_profile/` relate to each other and what
each one is responsible for.

## Module map

```
pypi_profile/
├── cli.py            ← argparse entry point; dispatches to every command
├── server.py         ← FastAPI app factory; all HTML and JSON routes
├── builder.py        ← static site generator (calls server via TestClient)
├── loader.py         ← reads pypi_profile.toml; discovers installed plugins
├── models.py         ← Pydantic data models for the TOML schema
├── claims.py         ← builds and encodes signed proof-of-control claims
├── signing.py        ← minisign keypair management; signs claims
├── verifier.py       ← fetches external URLs; validates claim signatures
├── fetcher.py        ← live data from PyPI, GitHub, GitLab, Mastodon (cached)
├── importers.py      ← import from JSON Resume; merge live data into profile
├── finder.py         ← file-system scanner that locates pypi_profile.toml files
├── key_management.py ← key-rotate, key-recover, key-export, key-import
├── plugin_spec.py    ← pluggy hook spec (defines what plugins can implement)
├── plugin_manager.py ← discovers and registers installed plugins via entry points
├── wizard.py         ← interactive terminal onboarding (prompt-toolkit)
├── gui.py            ← Tkinter desktop GUI
├── log.py            ← logging setup (one logger, one handler, one call site)
└── ds/
    ├── paths.py      ← locates pypi_ds templates and static assets on disk
    └── __init__.py
```

## How data flows through a typical command

### `pypi-profile serve ./my_profile`

```
cli.py  cmd_serve()
  │
  ├─ loader.find_profile("./my_profile")   → Path to pypi_profile.toml
  ├─ loader.load_profile(path)             → ProfileData (Pydantic object)
  │
  ├─ server.build_app(profile, ...)        → FastAPI app
  │     │
  │     ├─ Jinja2 FileSystemLoader
  │     │     1. pypi_profile/templates/
  │     │     2. pypi_ds/templates/
  │     │
  │     ├─ StaticFiles at /static/pypi_ds  ← CSS + images from pypi_ds package
  │     │
  │     └─ Route handlers (/, /packages, /verification, /api/profile.json, …)
  │
  └─ uvicorn.run(app)
```

### `pypi-profile build ./my_profile --output dist`

```
cli.py  cmd_build()
  │
  ├─ builder.build_static_site("./my_profile", output=Path("dist"))
  │     │
  │     ├─ loader.find_profile()   → toml_path
  │     ├─ loader.load_profile()   → ProfileData
  │     ├─ server.build_app(profile, static_mode=True)
  │     │
  │     ├─ starlette.testclient.TestClient(app)
  │     │     for each route in STATIC_ROUTES:
  │     │         resp = client.get(route)
  │     │         write resp.text → dist/path/index.html
  │     │
  │     ├─ for each JSON route in JSON_ROUTES:
  │     │         write resp.text → dist/api/*.json
  │     │
  │     ├─ copy resume.json → dist/api/resume.json  (if found)
  │     └─ copy static assets → dist/static/pypi_ds/
  └─ done
```

### `pypi-profile sign controls-url . --url https://github.com/you`

```
cli.py  cmd_sign()
  │
  ├─ loader.find_profile(".")           → toml_path
  ├─ loader.load_profile(toml_path)     → ProfileData
  │
  ├─ signing.sign_controls_url(
  │       profile_package, pypi_username, subject_url
  │   )
  │     │
  │     ├─ claims.build_claim(...)      → unsigned claim dict
  │     ├─ json.dumps(claim)            → canonical bytes
  │     ├─ minisign.sign(bytes, secret_key)  → 64-byte signature
  │     ├─ embed signature in claim dict
  │     └─ claims.encode_claim(claim)   → "pypi-profile-proof: <base64>"
  │
  └─ print proof token
```

### `pypi-profile verify .`

```
cli.py  cmd_verify()
  │
  ├─ loader.load_profile(...)           → ProfileData
  │
  ├─ verifier.diagnose_all_profiles(profile)
  │     │
  │     for each [[profiles]] link:
  │     ├─ verifier.fetch_page(link.url)        → raw HTML text
  │     ├─ verifier.find_proof_tokens(html)     → list of token strings
  │     ├─ claims.decode_claim(token)           → dict
  │     ├─ claims.is_expired(claim)             → bool
  │     └─ verifier.verify_claim_signature(claim, public_key_b64)  → bool
  │
  └─ print table of results
```

## Key design decisions

### Pydantic for the TOML schema

Every field in `pypi_profile.toml` maps to a Pydantic model in `models.py`. Pydantic does three
things here:

1. Validates that required fields are present and have the right types.
2. Fills in sensible defaults (most fields are optional with empty defaults).
3. Provides `model_dump()` so the API endpoints can serialize the whole profile to JSON with one call.

If you add a field to the TOML schema you need to add it to the matching Pydantic class. The
validator on `ProfileData.profile` shows how to add a custom validator if the field needs coercion
beyond what Pydantic does automatically.

### FastAPI + TestClient for static generation

The static builder does not re-implement page rendering. It calls the live FastAPI app through
Starlette's built-in `TestClient`, which runs the ASGI app in-process without starting a real HTTP
server. Every response is written to disk as a file. This means the static output is always
byte-for-byte identical to what the live server would return, and any bug fixed in a route is
automatically fixed in the static build too.

The `static_mode=True` flag tells the app to use `stored_proof` values from the TOML instead of
making live HTTP requests to external URLs, which would require network access and a private key
during CI builds.

### pluggy for plugin discovery

`pluggy` is a plugin framework originally built for pytest. It lets third-party packages register
themselves as providers of certain functionality by declaring an entry point in their
`pyproject.toml`. `pypi-profile` uses it so that installing a profile package (e.g. `pip install
matthewdeanmartin`) automatically makes that profile discoverable without any manual configuration.

The discovery chain is:

1. `importlib.metadata.entry_points(group="pypi_profile.plugins")` — finds all installed packages
   that registered themselves.
2. For each, `resources.files(module_name).joinpath("pypi_profile.toml")` — locates the bundled
   TOML file inside the installed package.
3. `load_profile(toml_path)` — reads and validates it.

### tomllib / tomli for TOML parsing

Python 3.11 added `tomllib` to the standard library. On older versions the code falls back to the
`tomli` third-party package, which is API-compatible. The import at the top of `loader.py` handles
this:

```python
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
```

This pattern is common in projects that need to support Python 3.10 without dropping TOML support.

### Dual Jinja2 template loader

The server sets up a `FileSystemLoader` with two directories in priority order:

1. `pypi_profile/templates/` — app-specific templates (can override anything)
2. `pypi_ds/templates/` — design system base templates

When a template is referenced, Jinja2 searches directory 1 first. This allows a future custom
profile package to ship its own templates in directory 1 and have them take precedence over the
defaults.
