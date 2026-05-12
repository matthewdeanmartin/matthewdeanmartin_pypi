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


def _generate_proofs(
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

    try:
        from pypi_profile.signing import sign_controls_url
    except ImportError:
        logger.debug("py-minisign not installed; cannot generate proofs")
        return [
            {
                "label": link.label,
                "url": link.url,
                "proof": None,
                "error": "py-minisign not installed",
            }
            for link in needing_proof
        ]

    from pypi_profile.signing import DEFAULT_KEY_DIR, DEFAULT_SK_NAME

    default_sk = DEFAULT_KEY_DIR / DEFAULT_SK_NAME
    sk_path = default_sk if default_sk.exists() else None

    if sk_path is None:
        logger.debug("No secret key on disk; skipping proof generation")
        return [
            {"label": link.label, "url": link.url, "proof": None, "error": "no-key"}
            for link in needing_proof
        ]

    results = []
    for link in needing_proof:
        try:
            proof = sign_controls_url(
                profile_package=profile_package,
                pypi_username=profile.identity.pypi_username,
                subject_url=link.url,
                sk_path=sk_path,
            )
            results.append(
                {"label": link.label, "url": link.url, "proof": proof, "error": None}
            )
        except (ImportError, OSError, ValueError) as exc:
            logger.warning("Failed to generate proof for %s: %s", link.url, exc)
            results.append(
                {"label": link.label, "url": link.url, "proof": None, "error": str(exc)}
            )
    return results


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
        import os

        from pypi_profile.signing import DEFAULT_KEY_DIR, DEFAULT_PK_NAME

        env_path = os.environ.get("PYPI_PROFILE_KEY_PATH", "")
        pk_path = (
            Path(env_path).expanduser().with_suffix(".pub")
            if env_path
            else DEFAULT_KEY_DIR / DEFAULT_PK_NAME
        )
        if pk_path.exists():
            try:
                import minisign  # type: ignore[import-untyped]

                pk = minisign.PublicKey.from_file(pk_path)
                profile.verification.public_key = pk.to_base64().decode()
                logger.debug("Loaded public key from %s (server fallback)", pk_path)
            except (ImportError, OSError, ValueError):
                logger.warning("Could not load public key from %s", pk_path, exc_info=True)
                profile.verification.public_key = ""

    logger.debug("Building FastAPI app (base_url=%r, static_mode=%s)", base_url, static_mode)
    ds_template_root, ds_static_root = template_root_path(), static_root_path()
    loader = jinja2.FileSystemLoader(
        [
            str(Path(__file__).parent / "templates"),
            str(ds_template_root),
        ]
    )
    env = jinja2.Environment(
        loader=loader, autoescape=jinja2.select_autoescape(["html"])
    )

    _static_base = base_url.rstrip("/")

    def render(template_name: str, context: dict[str, Any]) -> HTMLResponse:
        tmpl = env.get_template(template_name)
        context.setdefault("static_mode", static_mode)
        context.setdefault("base_url", _static_base)
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
        return render(
            "pypi_profile/packages.html", {"request": request, "profile": profile}
        )

    @app.get("/projects", response_class=HTMLResponse)
    async def projects(request: Request) -> HTMLResponse:
        return render(
            "pypi_profile/projects.html", {"request": request, "profile": profile}
        )

    @app.get("/resume", response_class=HTMLResponse)
    async def resume(request: Request) -> HTMLResponse:
        return render(
            "pypi_profile/resume.html", {"request": request, "profile": profile}
        )

    @app.get("/hiring", response_class=HTMLResponse)
    async def hiring(request: Request) -> HTMLResponse:
        return render(
            "pypi_profile/hiring.html", {"request": request, "profile": profile}
        )

    @app.get("/contact", response_class=HTMLResponse)
    async def contact(request: Request) -> HTMLResponse:
        return render(
            "pypi_profile/contact.html", {"request": request, "profile": profile}
        )

    @app.get("/verification", response_class=HTMLResponse)
    async def verification(request: Request) -> HTMLResponse:
        from pypi_profile.verifier import verify_all_profiles

        try:
            claim_results = verify_all_profiles(
                profile, profile_package=profile_package
            )
        except (ImportError, OSError, ValueError):
            logger.warning("Verification failed during /verification render", exc_info=True)
            claim_results = []

        proofs = _generate_proofs(profile, profile_package, claim_results)

        return render(
            "pypi_profile/verification.html",
            {
                "request": request,
                "profile": profile,
                "claim_results": claim_results,
                "proofs": proofs,
            },
        )

    @app.get("/succession", response_class=HTMLResponse)
    async def succession(request: Request) -> HTMLResponse:
        return render(
            "pypi_profile/succession.html", {"request": request, "profile": profile}
        )

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
        from pypi_profile.verifier import verify_all_profiles

        try:
            claim_results = verify_all_profiles(
                profile, profile_package=profile_package
            )
        except (ImportError, OSError, ValueError):
            logger.warning("Verification failed during /api/verification.json", exc_info=True)
            claim_results = []
        return JSONResponse(
            {
                **profile.verification.model_dump(),
                "claim_results": claim_results,
            }
        )

    return app
