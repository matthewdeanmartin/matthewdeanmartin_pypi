"""FastAPI application for rendering pypi-profile websites."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pypi_profile.ds.paths import static_root_path, template_root_path
from pypi_profile.models import ProfileData

logger = logging.getLogger(__name__)

ClaimResult = dict[str, Any]
ProofResult = dict[str, Any]


def generate_proofs(
    profile: ProfileData,
    profile_package: str,
    claim_results: list[ClaimResult],
) -> list[ProofResult]:
    """For each unverified profile URL, attempt to generate a ready-to-paste proof string.

    Returns a list of dicts with keys: label, url, proof (str or None), error (str or None).
    Only includes profiles that are not already verified.
    """

    verified_urls = {r["url"] for r in claim_results if r.get("status") == "verified"}
    needing_proof = [link for link in profile.profiles if link.url not in verified_urls]

    if not needing_proof:
        return []

    # Use stored proofs for any entry that has one (enables static builds without the key).
    results_from_stored = []
    still_needing = []
    for link in needing_proof:
        if link.stored_proof:
            results_from_stored.append(
                {
                    "label": link.label,
                    "url": link.url,
                    "proof": link.stored_proof,
                    "error": None,
                }
            )
        else:
            still_needing.append(link)

    if not still_needing:
        return results_from_stored

    needing_proof = still_needing

    from pypi_profile.signing import sign_controls_url

    results = list(results_from_stored)
    for link in needing_proof:
        try:
            proof = sign_controls_url(
                profile_package=profile_package,
                pypi_username=profile.identity.pypi_username,
                subject_url=link.url,
            )
            results.append({"label": link.label, "url": link.url, "proof": proof, "error": None})
        except FileNotFoundError:
            logger.debug("No signing key available for %s", link.url)
            results.append({"label": link.label, "url": link.url, "proof": None, "error": "no-key"})
        except (OSError, ValueError) as exc:
            logger.warning("Failed to generate proof for %s: %s", link.url, exc)
            results.append({"label": link.label, "url": link.url, "proof": None, "error": str(exc)})
    return results


def _get_claim_results(
    profile: ProfileData,
    profile_package: str,
    static_mode: bool,
) -> list[ClaimResult]:
    """Return claim results for the verification page/API.

    In static_mode we never make live HTTP requests — instead we derive status
    from stored_proof entries already baked into the TOML, which avoids network
    calls during the build and works correctly when served as flat files.
    """
    if static_mode:
        results = []
        for link in profile.profiles:
            if link.stored_proof:
                status = "verified"
            elif link.verification in (
                "self_asserted",
                "verified",
                "unverified",
                "invalid",
                "expired",
            ):
                status = link.verification
            else:
                status = "unverified"
            results.append(
                {
                    "kind": link.kind,
                    "label": link.label,
                    "url": link.url,
                    "status": status,
                    "has_stored_proof": bool(link.stored_proof),
                }
            )
        return results

    from pypi_profile.verifier import diagnose_all_profiles

    try:
        return diagnose_all_profiles(profile, profile_package=profile_package)
    except (ImportError, OSError, ValueError):
        logger.warning("Verification failed", exc_info=True)
        return []


def build_app(
    profile: ProfileData,
    allow_code: bool = False,
    profile_package: str = "",
    static_mode: bool = False,
    base_url: str = "",
) -> FastAPI:
    """Construct the FastAPI application for a loaded profile."""
    app = FastAPI(title="pypi-profile", docs_url=None, redoc_url=None)
    if not profile_package:
        profile_package = f"pypi-profile-{profile.identity.pypi_username}"

    # If the toml has no public key, try loading it from the key file on disk.
    if not profile.verification.public_key:
        from pypi_profile.signing import read_public_key_b64

        pub_b64 = read_public_key_b64()
        if pub_b64:
            profile.verification.public_key = pub_b64
            logger.debug("Loaded public key from disk (server fallback)")

    logger.debug("Building FastAPI app (base_url=%r, static_mode=%s)", base_url, static_mode)
    ds_template_root, ds_static_root = template_root_path(), static_root_path()
    loader = jinja2.FileSystemLoader(
        [
            str(Path(__file__).parent / "templates"),
            str(ds_template_root),
        ]
    )
    env = jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape(["html"]))

    static_base = base_url.rstrip("/")

    def render(template_name: str, context: dict[str, Any]) -> HTMLResponse:
        tmpl = env.get_template(template_name)
        context.setdefault("static_mode", static_mode)
        context.setdefault("base_url", static_base)
        html = tmpl.render(**context)
        return HTMLResponse(html)

    app.mount(
        "/static/pypi_ds",
        StaticFiles(directory=str(ds_static_root)),
        name="pypi_ds_static",
    )

    @app.get("/", response_class=HTMLResponse)
    async def summary(request: Request) -> HTMLResponse:
        return render(
            "pypi_profile/summary.html",
            {"request": request, "profile": profile, "allow_code": allow_code},
        )

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
        claim_results = _get_claim_results(profile, profile_package, static_mode)
        proofs = generate_proofs(profile, profile_package, claim_results)

        return render(
            "pypi_profile/verification.html",
            {
                "request": request,
                "profile": profile,
                "claim_results": claim_results,
                "proofs": proofs,
                "static_mode": static_mode,
            },
        )

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
        claim_results = _get_claim_results(profile, profile_package, static_mode)
        return JSONResponse(
            {
                **profile.verification.model_dump(),
                "static_mode": static_mode,
                "claim_results": claim_results,
            }
        )

    return app
