# Server and templating

`pypi_profile/server.py` contains the FastAPI application factory `build_app()`. Everything the
profile website shows — HTML pages, JSON APIs, verification results — comes from this function.

## Why FastAPI?

FastAPI is a modern Python web framework built on Starlette and Pydantic. It is used here because:

- It handles async route handlers natively, which makes the live server fast.
- Starlette's built-in `TestClient` lets the static builder call every route in-process without
  starting a real HTTP server.
- `StaticFiles` makes serving CSS and images trivial.

You do not need to know anything about async Python to read the server code. The route handlers
are simple functions that call `render()` and return an `HTMLResponse`.

## The app factory

```python
from pypi_profile.server import build_app
from pypi_profile.loader import load_profile
from pathlib import Path

profile = load_profile(Path("pypi_profile.toml"))
app = build_app(profile)
```

`build_app` takes several keyword arguments:

| Argument | Default | Meaning |
|---|---|---|
| `profile` | required | The loaded `ProfileData` object |
| `allow_code` | `False` | Enables plugin hook execution (currently minimal effect) |
| `profile_package` | `""` | Package name used in proof claims; defaults to `pypi-profile-{username}` |
| `static_mode` | `False` | When True, uses `stored_proof` instead of live verification |
| `base_url` | `""` | URL prefix for asset paths in subpath deployments |
| `hub_base` | `""` | URL of the hub root when this profile is mounted as a sub-app |
| `include_hub` | `False` | When True, adds hub routes (`/profiles`, `/profiles/search`) and mounts all installed profiles |

## Routes

### HTML pages

| Route | Template | Description |
|---|---|---|
| `GET /` | `pypi_profile/summary.html` | Profile homepage |
| `GET /packages` | `pypi_profile/packages.html` | PyPI packages list |
| `GET /projects` | `pypi_profile/projects.html` | Non-PyPI projects |
| `GET /resume` | `pypi_profile/resume.html` | Work history |
| `GET /hiring` | `pypi_profile/hiring.html` | Employment availability |
| `GET /contact` | `pypi_profile/contact.html` | Contact methods |
| `GET /verification` | `pypi_profile/verification.html` | Claim verification results |
| `GET /succession` | `pypi_profile/succession.html` | Succession planning |

When `include_hub=True`, two more routes are added:

| Route | Template | Description |
|---|---|---|
| `GET /profiles` | `pypi_profile/profiles_listing.html` | All installed profiles |
| `GET /profiles/search?q=QUERY` | `pypi_profile/profiles_search.html` | Search results |

### JSON APIs

| Route | Returns |
|---|---|
| `GET /api/profile.json` | Full `ProfileData.model_dump()` |
| `GET /api/packages.json` | List of `PackageEntry.model_dump()` |
| `GET /api/projects.json` | List of `ProjectEntry.model_dump()` |
| `GET /api/people.json` | List of `HumanEntry.model_dump()` |
| `GET /api/verification.json` | Verification section plus live claim results |
| `GET /api/profiles.json` | Summary of all installed profiles (hub mode only) |

### Static assets

CSS and images are mounted at `/static/pypi_ds`. The actual files come from the `pypi_ds`
sub-package inside the repo. `ds/paths.py` provides `static_root_path()` which uses
`importlib.resources` to locate those files regardless of where the package is installed.

## Template rendering

The `render()` helper inside `build_app` is a closure (a function defined inside another function
so it can access the outer scope's variables):

```python
def render(template_name: str, context: dict[str, Any]) -> HTMLResponse:
    tmpl = env.get_template(template_name)
    context.setdefault("static_mode", static_mode)
    context.setdefault("base_url", static_base)
    context.setdefault("hub_base", hub_base)
    html = tmpl.render(**context)
    return HTMLResponse(html)
```

Every route handler calls `render()` with a template name and a context dict. The `request`
object, `profile`, and a few flags are always in the context; route-specific data (like
`claim_results` on the verification page) is added per-route.

## Jinja2 loader setup

Jinja2 uses a `FileSystemLoader` that searches two directories in order:

```python
loader = jinja2.FileSystemLoader([
    str(Path(__file__).parent / "templates"),   # pypi_profile/templates/
    str(ds_template_root),                       # pypi_ds/templates/
])
env = jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape(["html"]))
```

`autoescape=True` for HTML means any variable rendered in a template is HTML-escaped
automatically, preventing cross-site scripting. You do not need to escape things manually.

The two-directory approach lets the app-specific templates override any template from the design
system by using the same filename.

## The verification page

The verification route is the most complex because it has to do live network requests (in live
mode) or read cached data (in static mode):

```python
@app.get("/verification", response_class=HTMLResponse)
async def verification(request: Request) -> HTMLResponse:
    claim_results = get_claim_results(profile, profile_package, static_mode)
    proofs = generate_proofs(profile, profile_package, claim_results)
    return render("pypi_profile/verification.html", {
        "request": request,
        "profile": profile,
        "claim_results": claim_results,
        "proofs": proofs,
        "static_mode": static_mode,
    })
```

`get_claim_results` has two modes:

- **Live mode** (`static_mode=False`): calls `verifier.diagnose_all_profiles()`, which fetches
  each `[[profiles]]` URL, extracts proof tokens, and checks signatures.
- **Static mode** (`static_mode=True`): reads `stored_proof` and `verification` from the TOML
  without making any HTTP requests. This is what the static builder uses.

`generate_proofs` produces ready-to-paste proof strings for any URL that does not yet have a
`stored_proof`. It calls `signing.sign_controls_url()` if a private key is available, otherwise
returns an `error: "no-key"` entry.

## Hub mode

When `include_hub=True`, the app also discovers all installed profile packages and mounts each as
a sub-app:

```python
for pkg_name, _toml_path, installed_profile in discover_installed_profiles():
    username = installed_profile.identity.pypi_username or pkg_name
    sub_app = build_app(installed_profile, static_mode=static_mode, base_url=f"/profiles/{username}", hub_base=static_base)
    app.mount(f"/profiles/{username}", sub_app)
```

Each sub-app is a fully independent FastAPI instance with its own routes, templates, and context.
The hub app just lists and searches them; clicking through takes you to the sub-app at
`/profiles/{username}`.

## Running the server manually

```python
import uvicorn
from pathlib import Path
from pypi_profile.loader import load_profile
from pypi_profile.server import build_app

profile = load_profile(Path("pypi_profile.toml"))
app = build_app(profile)
uvicorn.run(app, host="127.0.0.1", port=8000)
```

`uvicorn` is the ASGI server. It is used here the same way most FastAPI apps use it. The CLI's
`serve` command wraps this in argparse boilerplate.
