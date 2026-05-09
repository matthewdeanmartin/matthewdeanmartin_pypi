# Remaining Work

Phase 1 is complete. This document tracks what is still required to reach the v1 success criteria defined in `spec.md`.

Items are grouped by area. Within each group they are roughly ordered by dependency — earlier items unblock later ones.

---
JSON Resume import. 

- Need to implement.

---

## Signing and verification (minisign)

The signature backend is decided: **minisign**. Nothing here is implemented yet.

- [ ] Add `minisign` (or `pyminisign`) as an optional dependency in `pyproject.toml`
- [ ] `pypi_profile/signing.py` — generate a minisign keypair; write public key to `pypi_profile.toml` and private key to a local key file
- [ ] `pypi_profile/claims.py` — build the signed-claim JSON object (profile package name, PyPI username, claim type, subject URL, issued/expires timestamps, nonce, signature backend, signature value)
- [ ] Base64url-encode the claim to a copy-paste-friendly `pypi-profile-proof: <token>` string
- [ ] `pypi-profile sign controls-url --url <url>` CLI subcommand — signs a URL claim with the local private key and prints the proof string
- [ ] `pypi_profile/verifier.py` — fetch a declared external URL, scan for a `pypi-profile-proof:` token, decode and validate the signature against the public key in the profile
- [ ] `pypi-profile verify <source>` CLI subcommand — runs the verifier against all declared `[[profiles]]` entries and reports per-claim status (`verified`, `unverified`, `invalid`, `expired`)
- [ ] Update the `/verification` page and `/api/verification.json` endpoint to reflect live claim status when a verification cache/result is available
- [ ] `doctor` check: report whether `minisign` / `pyminisign` is importable and a key file is present

---

## CLI gaps

Several subcommands from the spec are stubbed or missing.

- [ ] `pypi-profile sign` — currently absent; depends on signing work above
- [ ] `pypi-profile verify` — currently absent; depends on verifier work above
- [ ] `pypi-profile fetch` — retrieve live PyPI JSON metadata for each declared package, compare self-asserted roles against actual maintainer lists, report discrepancies
- [ ] `pypi-profile init` — currently writes a flat TOML only; extend to optionally scaffold a full minimal Python package skeleton (`pyproject.toml`, `__init__.py`, `__about__.py`, `LICENSE`, `README.md`) with `--package-name` flag
- [ ] `pypi-profile init` — optional `--github-actions` flag to emit a trusted-publishing workflow hint
- [ ] `pypi-profile build` — static site export (see Phase 2 section below)
- [ ] `pypi-profile inspect` — currently only reads TOML; extend to accept a `.whl` path, extract and display wheel metadata, warn if the wheel contains importable Python modules (execution risk)
- [ ] `validate` — URL format checking for `[[profiles]]` and `[[projects]]` entries
- [ ] `validate` — warn when a claim is marked `verified` but no public key is present in `[verification]`

---

## Packaging: wheel-internal TOML location

The spec requires a stable, predictable location for `pypi_profile.toml` inside a published wheel.

- [ ] Decide the canonical path: `<dist>.dist-info/pypi_profile.toml` or a data directory (open question 2 in spec)
- [ ] Update `loader.find_profile()` to look in the chosen `dist-info` location when resolving an installed package name
- [ ] Update `hatch` build config in each profile package's `pyproject.toml` to include the TOML at that path
- [ ] Update `inspect` to report the discovered TOML path inside a wheel or installed dist-info

---

## Plugin system (allow-code path)

The pluggy wiring exists but the hook API is minimal and the allow-code path is not enforced.

- [ ] Expand `PypiProfileSpec` hookspecs: `get_profile_data`, `get_extra_pages`, `get_extra_routes`, `get_jinja_globals`, `validate_profile`, `get_verification_backends`
- [ ] `server.build_app()` — when `allow_code=True`, call `pm.hook.get_extra_routes()` and register returned FastAPI routers
- [ ] `server.build_app()` — when `allow_code=True`, merge `pm.hook.get_jinja_globals()` into the template environment
- [ ] Document the hook API so third-party plugin authors know what to implement
- [ ] Add a warning banner to the served site when running with `--allow-code`
- [ ] Enforce that `build_plugin_manager()` is never called (and plugins never loaded) unless `allow_code=True`

---

## Schema and validation hardening

- [ ] Add `schema_version` field to `[profile]` so consumers can detect breaking changes (open question 3)
- [ ] Generate and publish a JSON Schema artifact from the Pydantic models (open question 4)
- [ ] Add `skills` list to the data model (mentioned in the hiring section of the spec but not yet in `models.py`)
- [ ] Add `resume_url` / `resume_links` to the hiring or identity section
- [ ] Validate that `start_date` / `end_date` in `[[work_experience]]` are parseable dates or `"present"`
- [ ] Validate that `last_reviewed` in `[succession]` is a valid date

---

## Live PyPI metadata enrichment (`fetch`)

- [ ] `pypi_profile/pypi_client.py` — async HTTP client (httpx) that fetches `https://pypi.org/pypi/<name>/json` for each declared package
- [ ] Compare fetched maintainer/owner list against the self-asserted role in `[[packages]]`
- [ ] Expose enriched data as `ClaimStatus` (`verified` if PyPI confirms ownership, `unverified` otherwise)
- [ ] Cache fetch results to a local `.pypi_profile_cache/` directory so the server doesn't re-fetch on every request
- [ ] Surface enriched status on the `/packages` page and `/api/packages.json`

---

## Static site export (Phase 2)

- [ ] `pypi_profile/builder.py` — iterate all registered routes, render each to a static HTML file
- [ ] Write rendered HTML, CSS, and JSON files to `--output` directory
- [ ] Copy static assets (`/static/pypi_ds/`) into the output tree
- [ ] `pypi-profile build <source> --output dist/` CLI subcommand
- [ ] Handle the search form gracefully (omit or replace with a static note)
- [ ] Document how to publish the output to GitHub Pages / Netlify / Cloudflare Pages
- [ ] Add `make build-john-doe` target to the root Makefile as a demo

---

## Design and templates

- [ ] Remove the search form from the profile site header (it points to `None` and makes no sense on a profile page); replace with a simple text logo or site title link
- [ ] `/people` (or `/humans`) detail page — one card per human in `[[humans]]` with bio, role, and links; already referenced in the spec but not yet implemented
- [ ] Multi-human summary page — when `len(profile.humans) > 1`, link to per-human detail pages
- [ ] Accessible verification badges: ensure `self_asserted` is conveyed by text label, not colour alone (the current `badge` macro uses neutral tone but double-check contrast)
- [ ] `<meta>` description tag per page (currently uses the pypi_ds generic default)
- [ ] OpenGraph / Twitter card tags on the summary page
- [ ] Print stylesheet or `/resume` PDF-export hint

---

## Testing gaps

- [ ] Tests for `cli.py` subcommands: `validate` (invalid TOML), `init` (file already exists without `--force`), `inspect` (missing source), `doctor` (missing dep)
- [ ] Tests for the signing and verification modules once implemented
- [ ] Tests for `fetch` / PyPI client with mocked HTTP responses
- [ ] Property-based tests (Hypothesis) for `ProfileData` round-trip: `model_dump()` → `model_validate()` → `model_dump()` equality
- [ ] Integration test: `init` → write TOML → `validate` → `serve` → `GET /` returns 200

---

## Open questions to resolve before v1 freeze

From `spec.md` section "Open Questions":

1. ~~Which signature backend?~~ **Resolved: minisign.**
2. Exact wheel-internal path for `pypi_profile.toml` — needs decision before publishing any profile packages.
   3. should be resources/ 
3. Should schema version be independent of package version? Suggest yes; add `schema_version = "1"` to `[profile]`.
   4. yes
4. Formal JSON Schema artifact — generate from Pydantic with `model_json_schema()` and publish as `pypi_profile/schema.json`.
   5. yes
5. PyPI classifier for profile packages — propose `Topic :: System :: Software Distribution :: Profile` or similar; file with PyPI.
   6. uh, don't think we can make up new ones
6. How much live PyPI metadata to fetch and compare — see "Live PyPI metadata enrichment" above.
   7. ALL OF IT. All that we can fetch. which probably is going to be package list.
7. Static export contract for plugin-provided dynamic features — defer plugin static export to a post-v1 milestone.
   8. Just expect that plugin stuff will have breaks if it is too dynamic?
8. Distribute the component library (`pypi_ds`) separately — give `pypi_ds` its own `pyproject.toml` and workspace membership so it can be published and depended on normally.
   9. Nah, not yet. 
9. Built-in plugins for GitHub, GitLab, Mastodon — defer to post-v1 unless a simple read-only fetcher can ship as part of `fetch`.
   10. Support all three on day one. Future will be extras.
10. Expired or rotated verification keys — add `key_id` field and an `[[old_keys]]` table to `[verification]`; mark claims signed by old keys as `expired`.
    11. Sure if that is something minisign supports

---

## Before publishing any profile package to PyPI

- [ ] Finalise the wheel-internal TOML location (open question 2)
- [ ] Add a `pypi-profile` PyPI classifier to each profile package once approved
- [ ] Confirm the `pypi_ds` design system does not include any Warehouse-proprietary assets before shipping
- [ ] Write a short `README.md` for `pypi_profile/` explaining how to create, publish, and serve a profile package
