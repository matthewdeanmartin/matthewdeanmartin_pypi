"""FastAPI application for rendering pypi-profile websites."""

from __future__ import annotations

import sys
from pathlib import Path

import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pypi_profile.models import ProfileData


def resolve_ds_paths() -> tuple[Path, Path]:
    """Return (template_root, static_root) for the pypi_ds design system."""
    try:
        import pypi_ds.paths as ds_paths
        return ds_paths.template_root_path(), ds_paths.static_root_path()
    except ImportError:
        pass
    for candidate in [
        Path(__file__).parent.parent.parent.parent / "pypi_ds",
        Path(__file__).parent.parent.parent / "pypi_ds",
    ]:
        if (candidate / "paths.py").exists():
            if str(candidate.parent) not in sys.path:
                sys.path.insert(0, str(candidate.parent))
            import pypi_ds.paths as ds_paths  # type: ignore[import-not-found]
            return ds_paths.template_root_path(), ds_paths.static_root_path()
    raise ImportError("Cannot locate pypi_ds. Install it or ensure it is on PYTHONPATH.")


def build_app(profile: ProfileData, allow_code: bool = False) -> FastAPI:
    """Construct the FastAPI application for a loaded profile."""
    app = FastAPI(title="pypi-profile", docs_url=None, redoc_url=None)

    ds_template_root, ds_static_root = resolve_ds_paths()
    loader = jinja2.FileSystemLoader([
        str(Path(__file__).parent / "templates"),
        str(ds_template_root),
    ])
    env = jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape(["html"]))

    def render(template_name: str, context: dict) -> HTMLResponse:
        tmpl = env.get_template(template_name)
        html = tmpl.render(**context)
        return HTMLResponse(html)

    app.mount("/static/pypi_ds", StaticFiles(directory=str(ds_static_root)), name="pypi_ds_static")

    @app.get("/", response_class=HTMLResponse)
    async def summary(request: Request) -> HTMLResponse:
        return render("pypi_profile/summary.html", {"request": request, "profile": profile, "allow_code": allow_code})

    @app.get("/packages", response_class=HTMLResponse)
    async def packages(request: Request) -> HTMLResponse:
        return render("pypi_profile/packages.html", {"request": request, "profile": profile})

    @app.get("/projects", response_class=HTMLResponse)
    async def projects(request: Request) -> HTMLResponse:
        return render("pypi_profile/projects.html", {"request": request, "profile": profile})

    @app.get("/resume", response_class=HTMLResponse)
    async def resume(request: Request) -> HTMLResponse:
        return render("pypi_profile/resume.html", {"request": request, "profile": profile})

    @app.get("/hiring", response_class=HTMLResponse)
    async def hiring(request: Request) -> HTMLResponse:
        return render("pypi_profile/hiring.html", {"request": request, "profile": profile})

    @app.get("/contact", response_class=HTMLResponse)
    async def contact(request: Request) -> HTMLResponse:
        return render("pypi_profile/contact.html", {"request": request, "profile": profile})

    @app.get("/verification", response_class=HTMLResponse)
    async def verification(request: Request) -> HTMLResponse:
        return render("pypi_profile/verification.html", {"request": request, "profile": profile})

    @app.get("/succession", response_class=HTMLResponse)
    async def succession(request: Request) -> HTMLResponse:
        return render("pypi_profile/succession.html", {"request": request, "profile": profile})

    @app.get("/api/profile.json")
    async def api_profile() -> JSONResponse:
        return JSONResponse(profile.model_dump())

    @app.get("/api/packages.json")
    async def api_packages() -> JSONResponse:
        return JSONResponse([p.model_dump() for p in profile.packages])

    @app.get("/api/projects.json")
    async def api_projects() -> JSONResponse:
        return JSONResponse([p.model_dump() for p in profile.projects])

    @app.get("/api/people.json")
    async def api_people() -> JSONResponse:
        return JSONResponse([h.model_dump() for h in profile.humans])

    @app.get("/api/verification.json")
    async def api_verification() -> JSONResponse:
        return JSONResponse(profile.verification.model_dump())

    return app
