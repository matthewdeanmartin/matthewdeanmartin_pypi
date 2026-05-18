# Static Site Generation Plan

## Context

`pypi-profile` currently runs as a FastAPI + Jinja2 server. Users who want to publish
their profile publicly face a multi-step install process:

```bash
pipx install pypi-profile
pipx inject pypi-profile matthewdeanmartin
pypi-profile serve matthewdeanmartin
```

That's fine for power users running locally. For a public, always-on URL, users need a
**single-command static export** that produces files they can drop onto GitHub Pages,
Cloudflare Pages, or any static host — without any server-side Python.

This document plans a static site generation capability alongside (not replacing) the
existing dynamic server.

______________________________________________________________________

## Design principles

1. **One command.** `pypi-profile build <source> --output dist/` is the entire workflow.
1. **Self-contained output.** The `dist/` directory contains everything: HTML, CSS, JS,
   JSON, and image assets. No CDN dependencies, no Python required at runtime.
1. **All resources bundled in pypi-profile.** Users must not need to install Node, npm,
   Angular CLI, or any non-Python build tool. All JS/CSS/template assets ship inside the
   `pypi-profile` Python package.
1. **Maximum template reuse.** The Jinja2 templates used by the server are also used for
   the static build — they render to plain HTML files. No second template language.
1. **JSON as the data contract.** Every page writes a corresponding `api/*.json` file.
   The same JSON drives both static HTML generation and any client-side enhancement.
1. **JSON Resume as first-class citizen.** `resume.json` (JSON Resume format) is stored
   alongside `pypi_profile.toml` and published as `api/resume.json`.
1. **Minisign via WASM/JS.** The static site includes a small JS bundle that can verify
   signed claims client-side using the `minisign-wasm` npm library. This bundle ships
   pre-built inside pypi-profile — users never touch npm.
1. **Publication out of scope.** `build` writes files; where users deploy them is their
   business. We document GitHub Pages, Cloudflare Pages, and Netlify as examples.

______________________________________________________________________

## Architecture overview

```
pypi-profile build <source> --output dist/
│
├── Python side (existing server code reused)
│   ├── loader.py         → load ProfileData + resume.json
│   ├── server.py routes  → called headlessly to render HTML
│   ├── Jinja2 templates  → same templates as serve mode
│   └── static assets     → CSS, images, favicon from pypi_ds
│
├── New: builder.py
│   ├── Iterates all known routes
│   ├── Renders each route to static HTML via Starlette TestClient
│   ├── Writes HTML files (index.html, packages/index.html, …)
│   ├── Writes JSON files (api/profile.json, api/packages.json, …)
│   ├── Writes api/resume.json from resume.json source
│   ├── Copies static assets (pypi_ds CSS, images, favicon)
│   └── Copies pre-built minisign-wasm JS bundle
│
└── New: static/ directory inside pypi_profile package
    ├── js/
    │   ├── minisign-verify.js   (pre-built bundle, ~150 KB)
    │   └── verification.js      (thin glue layer, reads api/verification.json)
    └── (no other framework JS — HTML is pre-rendered)
```

The static site is **pre-rendered HTML, not a SPA**. There is no Angular, React, or Vue.
The earlier mention of Angular in the user request is re-scoped: what we want is a
self-contained static export that works without a server, not an Angular SPA. Angular
would require a Node build pipeline bundled inside pypi-profile, which violates principle 3.

The only client-side JS is the minisign verification widget, which is optional and
gracefully degrades: if JS is disabled, the page shows the last-known verification status
from the pre-rendered HTML.

______________________________________________________________________

## Static site URL structure

```
dist/
├── index.html                   ← /  (summary page)
├── packages/
│   └── index.html               ← /packages
├── projects/
│   └── index.html               ← /projects
├── resume/
│   └── index.html               ← /resume
├── hiring/
│   └── index.html               ← /hiring
├── contact/
│   └── index.html               ← /contact
├── verification/
│   └── index.html               ← /verification (pre-rendered, JS recheck optional)
├── succession/
│   └── index.html               ← /succession
├── people/
│   └── index.html               ← /people (if humans list non-empty)
├── api/
│   ├── profile.json
│   ├── packages.json
│   ├── projects.json
│   ├── people.json
│   ├── resume.json              ← from resume.json source file
│   └── verification.json
└── static/
    ├── pypi_ds/                  ← CSS, images, favicon (copied from pypi_ds package)
    └── js/
        ├── minisign-verify.js    ← pre-built WASM bundle
        └── verification.js       ← glue code
```

The path `packages/index.html` lets GitHub Pages serve `/packages` without a trailing
slash redirect by using the `index.html` convention supported by all major static hosts.

______________________________________________________________________

## Data flow

### Build-time (Python)

```
ProfileData (from pypi_profile.toml)
    │
    ├── Pydantic .model_dump()  ──→  api/profile.json
    ├── packages list           ──→  api/packages.json
    ├── projects list           ──→  api/projects.json
    ├── humans list             ──→  api/people.json
    ├── verification.json (last known claim results, from --verify flag or cache)
    │
    └── Jinja2 render (via TestClient GET /)
            │
            ├── GET /            → index.html
            ├── GET /packages    → packages/index.html
            ├── GET /projects    → projects/index.html
            ├── GET /resume      → resume/index.html
            ├── GET /hiring      → hiring/index.html
            ├── GET /contact     → contact/index.html
            ├── GET /verification → verification/index.html
            ├── GET /succession  → succession/index.html
            └── GET /people      → people/index.html (if humans non-empty)

resume.json (JSON Resume format, from --resume-file or auto-discovered)
    └──────────────────────────────→  api/resume.json (published as-is)
```

### Runtime (browser, optional JS)

```
verification/index.html loads verification.js
    │
    └── fetch("../api/verification.json")
            │
            └── for each claim with status != "verified":
                    load minisign-verify.js (WASM)
                    fetch claim subject URL
                    scan for pypi-profile-proof: token
                    verify signature in-browser
                    update UI badge
```

The client-side re-verification is a **nice-to-have**. Build output is correct without it.
The pre-rendered HTML always shows the build-time verification state.

______________________________________________________________________

## JSON Resume integration

JSON Resume (`resume.json`) becomes a first-class data citizen:

1. **Storage:** `resume.json` lives at the package root alongside `pypi_profile.toml`.
   Profile packages SHOULD include it in the wheel (in `resources/`).

1. **Import:** `pypi-profile init --from-json-resume resume.json` already imports
   JSON Resume into the TOML format (implemented in `importers.py`). No change needed.

1. **Export:** `pypi-profile build` always writes `api/resume.json` if a `resume.json`
   is found. The JSON file is published verbatim — it is the user's canonical resume.

1. **Auto-discovery:** `loader.py` gets a `find_resume()` helper that looks for
   `resume.json` next to `pypi_profile.toml`, in the package's `resources/` dir, or at
   a path given by `--resume-file`. If not found, `api/resume.json` is skipped silently.

1. **Resume page:** The `/resume` HTML page continues to render from the work_experience
   data in the TOML (already implemented). The JSON endpoint is an additional artifact
   for tooling that knows the JSON Resume schema.

______________________________________________________________________

## Minisign JS bundle

The static site needs client-side signature verification. The library is
[`minisign-wasm`](https://github.com/nicowillis/minisign-wasm) (MIT licensed,
~150 KB gzipped).

### How it ships

The pre-built bundle is **vendored** into the pypi-profile package at:

```
pypi_profile/pypi_profile/static/js/minisign-verify.js
```

This is a one-time vendor operation. The bundle is checked into the repo. When
`minisign-wasm` releases a security fix we update the vendored file.

Rationale: vendoring avoids a Node/npm requirement for users. The bundle is small and
MIT licensed.

### Thin glue layer (`verification.js`)

```javascript
// verification.js — runs on verification/index.html
// Reads api/verification.json, rechecks any unverified claims in-browser.
// Degrades gracefully: if minisign-verify.js fails to load, page still shows
// the pre-rendered build-time status.
```

This file is ~50 lines, hand-written, checked into the repo at
`pypi_profile/pypi_profile/static/js/verification.js`.

### Template change

The `verification.html` Jinja2 template gains a `static_mode` context variable.
When `static_mode=True` (set during static build), the template emits:

```html
<script src="{{ static_root }}/js/minisign-verify.js"></script>
<script src="{{ static_root }}/js/verification.js"></script>
```

When `static_mode=False` (serve mode), those script tags are omitted — verification
is done server-side via `verifier.py`.

______________________________________________________________________

## New CLI command: `build`

```bash
pypi-profile build <source> [--output dist/] [--verify] [--resume-file path/to/resume.json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `source` | required | same as `serve`: package name, path to .toml, or directory |
| `--output` | `dist/` | output directory (created if absent, overwritten if present) |
| `--verify` | off | run minisign verification before building; embed results in verification.json |
| `--resume-file` | auto | path to JSON Resume file; auto-discovered if not given |
| `--base-url` | `/` | base URL prefix for asset paths (e.g. `/myuser` for GitHub Pages subpath) |

### Exit codes

- `0` — success
- `1` — profile load/validation error
- `2` — output directory error

### Example output

```
Building static site for matthewdeanmartin...
  ✓ Loaded profile: Matthew Dean Martin (individual)
  ✓ Rendered 8 pages
  ✓ Wrote 6 JSON files
  ✓ Copied static assets (pypi_ds)
  ✓ Copied minisign JS bundle
  ✓ Resume: api/resume.json written
  
Output: dist/  (42 files, 1.2 MB)

Next steps:
  GitHub Pages:   push dist/ contents to gh-pages branch
  Cloudflare Pages: connect repo, set build output to dist/
  Netlify:         drag and drop dist/ folder
```

______________________________________________________________________

## Jinja2 template changes

The existing templates need minimal changes:

1. **`base.html`** — add `base_url` context variable (default `/`). All `static/` paths
   use `{{ base_url }}/static/...` instead of hardcoded `/static/...`.
   This is needed for GitHub Pages subpath deployments.

1. **`verification.html`** — add `static_mode` context variable. When true, emit the
   JS bundle script tags.

1. **All templates** — internal navigation links use `{{ base_url }}/packages` etc.
   instead of `/packages`. This is already partially handled by the design system
   but needs auditing.

No new template language. No template duplication. Same Jinja2 files, new context vars.

______________________________________________________________________

## `builder.py` — implementation sketch

```python
# pypi_profile/builder.py

from pathlib import Path
from starlette.testclient import TestClient

from pypi_profile.loader import find_profile, load_profile, find_resume
from pypi_profile.server import build_app

STATIC_ROUTES = [
    ("/", "index.html"),
    ("/packages", "packages/index.html"),
    ("/projects", "projects/index.html"),
    ("/resume", "resume/index.html"),
    ("/hiring", "hiring/index.html"),
    ("/contact", "contact/index.html"),
    ("/verification", "verification/index.html"),
    ("/succession", "succession/index.html"),
    ("/people", "people/index.html"),
]

JSON_ROUTES = [
    ("/api/profile.json", "api/profile.json"),
    ("/api/packages.json", "api/packages.json"),
    ("/api/projects.json", "api/projects.json"),
    ("/api/people.json", "api/people.json"),
    ("/api/verification.json", "api/verification.json"),
]


def build_static_site(
    source: str,
    output: Path,
    verify: bool = False,
    resume_file: Path | None = None,
    base_url: str = "/",
) -> None:
    toml_path = find_profile(source)
    profile = load_profile(toml_path)

    app = build_app(profile, allow_code=False, static_mode=True, base_url=base_url)
    client = TestClient(app, raise_server_exceptions=True)

    output.mkdir(parents=True, exist_ok=True)

    for route, rel_path in STATIC_ROUTES:
        resp = client.get(route)
        if resp.status_code == 404:
            continue  # e.g. /people when no humans
        dest = output / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(resp.text, encoding="utf-8")

    for route, rel_path in JSON_ROUTES:
        resp = client.get(route)
        dest = output / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(resp.text, encoding="utf-8")

    # resume.json
    resume_path = resume_file or find_resume(toml_path)
    if resume_path and resume_path.exists():
        (output / "api" / "resume.json").write_text(
            resume_path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    _copy_static_assets(output, base_url)


def _copy_static_assets(output: Path, base_url: str) -> None:
    from pypi_profile.ds.paths import static_root_path
    import shutil

    static_src = static_root_path()
    static_dest = output / "static" / "pypi_ds"
    if static_dest.exists():
        shutil.rmtree(static_dest)
    shutil.copytree(static_src, static_dest)

    # copy pre-built JS bundle
    js_src = Path(__file__).parent / "static" / "js"
    js_dest = output / "static" / "js"
    js_dest.mkdir(parents=True, exist_ok=True)
    for js_file in js_src.iterdir():
        shutil.copy2(js_file, js_dest / js_file.name)
```

______________________________________________________________________

## New files to create

| Path | Purpose |
|------|---------|
| `pypi_profile/pypi_profile/builder.py` | Core static site generator |
| `pypi_profile/pypi_profile/static/js/minisign-verify.js` | Vendored minisign WASM bundle |
| `pypi_profile/pypi_profile/static/js/verification.js` | Thin glue layer for client-side re-verification |

## Files to modify

| Path | Change |
|------|--------|
| `pypi_profile/pypi_profile/cli.py` | Add `cmd_build` and wire up `build` subcommand |
| `pypi_profile/pypi_profile/server.py` | Accept `static_mode: bool` and `base_url: str` params; pass to template context |
| `pypi_profile/pypi_profile/loader.py` | Add `find_resume()` helper |
| `pypi_profile/pypi_profile/templates/pypi_profile/base.html` | Use `{{ base_url }}` for all asset/nav paths |
| `pypi_profile/pypi_profile/templates/pypi_profile/verification.html` | Emit JS script tags when `static_mode=True` |
| `pypi_profile/pypi_profile/gui.py` | Add `build` command entry to GUI command list |
| `pypi_profile/pyproject.toml` | Add `httpx[http2]` and `starlette[full]` to test deps (TestClient) |
| `john_doe/pyproject.toml` | Add `resources/resume.json` to package data |
| `matthewdeanmartin/pyproject.toml` | Same |

______________________________________________________________________

## Phases

### Phase 1: Core static build (no JS verification)

Goal: `pypi-profile build` produces deployable HTML + JSON without any client-side JS.

Tasks:

1. Modify `server.py` to accept `static_mode` and `base_url` context; pass through to templates.
1. Audit `base.html` and all nav/asset links — replace hardcoded `/static/` with `{{ base_url }}/static/`.
1. Add `find_resume()` to `loader.py`.
1. Implement `builder.py` using `TestClient`.
1. Add `cmd_build` to `cli.py`.
1. Add `build` to the GUI command list.
1. Write `john_doe/resume.json` as a sample (already exists at repo root level — confirm location).
1. Test: `uv run pypi-profile build john_doe/john_doe/pypi_profile.toml --output /tmp/john_doe_dist`.
1. Verify output is deployable by opening `dist/index.html` in a browser.

### Phase 2: JSON Resume as first-class citizen

Goal: `resume.json` ships with every profile package and is published at `api/resume.json`.

Tasks:

1. Confirm JSON Resume files are present in `john_doe/` and `matthewdeanmartin/`.
1. Update `hatch` / `pyproject.toml` build configs to include `resume.json` in wheel data.
1. Update `loader.find_resume()` to also check `importlib.resources` / wheel data paths.
1. Test round-trip: build → check `dist/api/resume.json` exists and is valid JSON Resume.

### Phase 3: Client-side minisign verification

Goal: The verification page can re-check claims in-browser without a server.

Tasks:

1. Source the `minisign-wasm` pre-built bundle (MIT license, ~150 KB).
   - Clone `https://github.com/nicowillis/minisign-wasm` and build, or use a CDN snapshot.
   - Vendor the built JS file to `pypi_profile/pypi_profile/static/js/minisign-verify.js`.
1. Write `verification.js` (thin glue, ~50 lines).
1. Update `verification.html` to conditionally emit script tags.
1. Test: open `dist/verification/index.html` in browser with one declared profile that has a valid proof; confirm badge updates.

### Phase 4: `--verify` flag integration

Goal: Build with live claim verification baked into the output.

Tasks:

1. In `cmd_build`, when `--verify` is passed: call the verifier, write results to a temp
   cache, then pass the cache into `build_app` so the `/api/verification.json` route
   returns live-checked results rather than `unknown`.
1. Document the recommended CI workflow:
   ```yaml
   - run: uv run pypi-profile build . --verify --output dist/
   ```

### Phase 5: Doctor and validate improvements

Tasks:

1. Add `pypi-profile doctor` check: "static build dependencies available" (starlette TestClient).
1. `pypi-profile validate` warns if `resume.json` is declared but not found.
1. Add `build` to the GUI.

______________________________________________________________________

## What we are NOT doing

- **No Angular SPA.** The initial user request mentioned Angular, but on review:

  - Angular requires a Node.js build pipeline, which would need to be bundled in pypi-profile.
  - The existing Jinja2 templates already produce correct, accessible, PyPI-styled HTML.
  - Pre-rendering Jinja2 → HTML and shipping static files is simpler and fully self-contained.
  - The only JS we need is the minisign verification widget (~150 KB vendored bundle).
  - If a future contributor wants to build an Angular-based alternative shell, the
    `api/*.json` endpoints provide the data contract they need.

- **No publication automation.** `pypi-profile build` writes files; deployment is manual.

- **No separate static template language.** Same Jinja2 templates, new context variables.

______________________________________________________________________

## Testing plan

```bash
# Phase 1 smoke test
uv run pypi-profile build john_doe/john_doe/pypi_profile.toml --output /tmp/jd_dist

# check files exist
ls /tmp/jd_dist/index.html
ls /tmp/jd_dist/packages/index.html
ls /tmp/jd_dist/api/profile.json
ls /tmp/jd_dist/static/pypi_ds/css/pypi_ds.css

# check JSON is valid
python -c "import json; json.load(open('/tmp/jd_dist/api/profile.json'))"

# open in browser
# python -m http.server 8080 --directory /tmp/jd_dist

# pytest
uv run pytest pypi_profile/tests/test_builder.py -v
```

Unit tests to write:

- `test_builder.py::test_build_creates_expected_files` — check all HTML and JSON files exist
- `test_builder.py::test_build_json_valid` — all JSON files parse without error
- `test_builder.py::test_build_base_url_prefix` — asset paths in HTML respect `--base-url`
- `test_builder.py::test_resume_json_copied` — when resume.json present, `api/resume.json` written
- `test_builder.py::test_resume_json_skipped` — when resume.json absent, no error

______________________________________________________________________

## Open questions

1. **minisign-wasm source.** Is `nicowillis/minisign-wasm` the right library? Are there
   alternatives? Needs a quick audit before Phase 3.
1. **`--base-url` default.** GitHub Pages project sites are at `/<reponame>/`. We could
   auto-detect from a `GITHUB_REPOSITORY` env var during build. Deferred.
1. **404 page.** Static hosts expect a `404.html`. Should `build` emit one?
   Probably yes — copy from a template. Deferred to Phase 1 polish.
1. **Search.** The design system header has a search form that points nowhere on static
   builds. Existing `remaining.md` already notes this: "Remove the search form from the
   profile site header." Fix in Phase 1.
