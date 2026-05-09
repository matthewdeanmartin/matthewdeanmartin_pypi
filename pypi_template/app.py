import sys
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import ChoiceLoader, FileSystemLoader
from starlette.templating import Jinja2Templates

project_root = Path(__file__).resolve().parent
repo_root = project_root.parent

if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from pypi_ds.paths import static_root_path, template_root_path

app = FastAPI(title="PyPI Template Demo")

template_loader = ChoiceLoader(
    [
        FileSystemLoader(str(project_root / "templates")),
        FileSystemLoader(str(template_root_path())),
    ]
)
templates = Jinja2Templates(directory=str(project_root / "templates"))
templates.env.loader = template_loader

app.mount(
    "/static/pypi_ds",
    StaticFiles(directory=str(static_root_path())),
    name="pypi_ds_static",
)


def build_catalog() -> list[dict[str, object]]:
    return [
        {
            "slug": "pypi-ds",
            "name": "pypi-ds",
            "version": "0.1.0",
            "description": "Reusable Jinja2 components, layouts, and assets shaped by Warehouse's UI.",
            "meta": "Design system · Released May 2026",
            "release_date": "May 9, 2026",
            "released": "May 9, 2026",
            "status_text": "Latest version",
            "status_tone": "good",
            "pip_command": "pip install pypi-ds",
            "summary": "A PyPI-flavored template library for other websites.",
            "project_links": [
                {
                    "label": "Documentation",
                    "href": "https://example.invalid/docs/pypi-ds",
                },
                {"label": "Source", "href": "https://example.invalid/src/pypi-ds"},
                {"label": "Issues", "href": "https://example.invalid/issues/pypi-ds"},
            ],
            "maintainers": ["PyPI team", "Packaging WG", "Site builders"],
            "release_history": [
                {
                    "version": "0.1.0",
                    "released": "May 2026",
                    "notes": "Standalone Warehouse-style design system",
                },
                {
                    "version": "0.0.5",
                    "released": "Apr 2026",
                    "notes": "Refined layout, package card, and footer",
                },
                {
                    "version": "0.0.1",
                    "released": "Mar 2026",
                    "notes": "Initial extraction prototype",
                },
            ],
            "files": [
                {
                    "filename": "pypi_ds-0.1.0-py3-none-any.whl",
                    "meta": "36 kB · Universal wheel",
                    "href": "/static/pypi_ds/images/logo-small.svg",
                },
                {
                    "filename": "pypi_ds-0.1.0.tar.gz",
                    "meta": "24 kB · Source distribution",
                    "href": "/static/pypi_ds/images/logo-large.svg",
                },
            ],
        },
        {
            "slug": "warehouse-search-demo",
            "name": "warehouse-search-demo",
            "version": "2.3.1",
            "description": "A catalog demo that shows package cards, filters, and a Warehouse-like results layout.",
            "meta": "Demo app · Released Apr 2026",
            "release_date": "Apr 21, 2026",
            "released": "Apr 21, 2026",
            "status_text": "Stable release available",
            "status_tone": "warn",
            "pip_command": "pip install warehouse-search-demo",
            "summary": "A realistic search page fixture for template integration.",
            "project_links": [
                {
                    "label": "Documentation",
                    "href": "https://example.invalid/docs/warehouse-search-demo",
                },
                {
                    "label": "Source",
                    "href": "https://example.invalid/src/warehouse-search-demo",
                },
            ],
            "maintainers": ["Search team", "Design systems"],
            "release_history": [
                {
                    "version": "2.3.1",
                    "released": "Apr 2026",
                    "notes": "Improved search summaries",
                },
                {
                    "version": "2.3.0",
                    "released": "Mar 2026",
                    "notes": "Added filter sidebar",
                },
            ],
            "files": [
                {
                    "filename": "warehouse_search_demo-2.3.1-py3-none-any.whl",
                    "meta": "18 kB · Universal wheel",
                    "href": "/static/pypi_ds/images/blue-cube.svg",
                }
            ],
        },
        {
            "slug": "simple-index-kit",
            "name": "simple-index-kit",
            "version": "1.4.0",
            "description": "A small starter for package indexes and internal artifact catalogs with a PyPI-like feel.",
            "meta": "Starter kit · Released Feb 2026",
            "release_date": "Feb 2, 2026",
            "released": "Feb 2, 2026",
            "status_text": "Verified metadata",
            "status_tone": "good",
            "pip_command": "pip install simple-index-kit",
            "summary": "A compact package portal starter.",
            "project_links": [
                {
                    "label": "Documentation",
                    "href": "https://example.invalid/docs/simple-index-kit",
                },
                {
                    "label": "Source",
                    "href": "https://example.invalid/src/simple-index-kit",
                },
            ],
            "maintainers": ["Infra team"],
            "release_history": [
                {
                    "version": "1.4.0",
                    "released": "Feb 2026",
                    "notes": "Improved mobile table layouts",
                },
                {
                    "version": "1.3.0",
                    "released": "Jan 2026",
                    "notes": "Added package detail sidebar",
                },
            ],
            "files": [
                {
                    "filename": "simple_index_kit-1.4.0.tar.gz",
                    "meta": "14 kB · Source distribution",
                    "href": "/static/pypi_ds/images/white-cube.svg",
                }
            ],
        },
    ]


def build_header_nav(current_page: str) -> list[dict[str, object]]:
    nav_items = [
        {"label": "Home", "href": "/", "current": current_page == "home"},
        {"label": "Search", "href": "/search", "current": current_page == "search"},
        {
            "label": "Project",
            "href": "/projects/pypi-ds",
            "current": current_page == "project",
        },
    ]
    return nav_items


def build_secondary_nav() -> list[dict[str, object]]:
    return [
        {
            "label": "GitHub",
            "href": "https://github.com/pypi/warehouse",
            "current": False,
        },
        {"label": "Docs", "href": "https://packaging.python.org/", "current": False},
    ]


def build_footer_menus() -> list[dict[str, object]]:
    return [
        {
            "title": "Demo pages",
            "links": [
                {"label": "Home", "href": "/"},
                {"label": "Search", "href": "/search"},
                {"label": "Project detail", "href": "/projects/pypi-ds"},
            ],
        },
        {
            "title": "Design system",
            "links": [
                {
                    "label": "PyPI DS package",
                    "href": "https://github.com/pypi/warehouse",
                },
                {"label": "Warehouse", "href": "https://github.com/pypi/warehouse"},
                {"label": "Packaging guide", "href": "https://packaging.python.org/"},
            ],
        },
        {
            "title": "Try it",
            "links": [
                {"label": "Health check", "href": "/health"},
                {"label": "Search for template", "href": "/search?q=template"},
                {"label": "Search for index", "href": "/search?q=index"},
            ],
        },
    ]


def build_base_context(
    request: Request, current_page: str, page_title: str
) -> dict[str, object]:
    context = {
        "request": request,
        "asset_base": "/static/pypi_ds",
        "brand_name": "PyPI Template Demo",
        "brand_href": "/",
        "search_action": "/search",
        "header_nav_items": build_header_nav(current_page),
        "header_secondary_items": build_secondary_nav(),
        "footer_menus": build_footer_menus(),
        "footer_note": "This demo app exercises the extracted pypi_ds templates with FastAPI and uv.",
        "supporting_note": "Use it as a reference for wiring pypi_ds into another Jinja2 application.",
        "page_title": page_title,
        "top_notifications": [
            {
                "title": "Demo",
                "message": "This is a local preview app for the extracted PyPI design system.",
                "tone": "banner",
            }
        ],
    }
    return context


def match_projects(search_text: str) -> list[dict[str, object]]:
    search_value = search_text.strip().lower()
    catalog = build_catalog()

    if not search_value:
        return catalog

    matching_projects = []
    for project in catalog:
        haystack = " ".join(
            [
                str(project["name"]),
                str(project["description"]),
                str(project["summary"]),
                str(project["meta"]),
            ]
        ).lower()
        if search_value in haystack:
            matching_projects.append(project)

    return matching_projects


def find_project(project_slug: str) -> dict[str, object]:
    catalog = build_catalog()
    for project in catalog:
        if project["slug"] == project_slug:
            return project
    return catalog[0]


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    context = build_base_context(request, current_page="home", page_title="Home")
    context.update(
        {
            "search_query": "",
            "stats": [
                {"value": "3", "label": "demo projects"},
                {"value": "7", "label": "example routes"},
                {"value": "1", "label": "uv-powered app"},
                {"value": "100%", "label": "PyPI-inspired styling"},
            ],
        }
    )
    return templates.TemplateResponse(request, "home.html", context)


@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = Query(default="")) -> HTMLResponse:
    matching_projects = match_projects(q)
    search_query = q or "template"
    context = build_base_context(request, current_page="search", page_title="Search")
    context.update(
        {
            "search_query": search_query,
            "search_term": search_query,
            "results": [
                {
                    **project,
                    "href": f"/projects/{project['slug']}",
                }
                for project in matching_projects
            ],
            "result_count": len(matching_projects),
        }
    )
    return templates.TemplateResponse(request, "search.html", context)


@app.get("/projects/{project_slug}", response_class=HTMLResponse)
async def project_detail(request: Request, project_slug: str) -> HTMLResponse:
    project = find_project(project_slug)
    context = build_base_context(
        request, current_page="project", page_title=str(project["name"])
    )
    context.update(
        {
            "project": project,
            "search_query": str(project["name"]),
            "release_history_columns": [
                {"key": "version", "label": "Version"},
                {"key": "released", "label": "Released"},
                {"key": "notes", "label": "Notes"},
            ],
            "release_history_rows": project["release_history"],
            "files": project["files"],
            "project_links": project["project_links"],
            "maintainers": project["maintainers"],
        }
    )
    return templates.TemplateResponse(request, "project.html", context)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
