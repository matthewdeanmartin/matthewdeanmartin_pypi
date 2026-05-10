# Roadmap

This page summarizes the roadmap **as inferred from `spec/spec.md` and `spec/remaining.md`**. It is intentionally forward-looking; do not read it as a list of features that are already shipped.

## Highest-priority gaps

The largest gaps between the current implementation and the spec are:

1. a stable distribution layout for `pypi_profile.toml` inside published wheels
2. a fuller plugin system with explicit `allow_code` behavior
3. static site export (`build` command)
4. richer CLI coverage, especially `build` and stronger validation diagnostics

## Planned work areas

### Signing and verification

The core signing flow is shipped. The following remain:

- key rotation support: marking claims signed by an old key as `expired` rather
  than `invalid`
- an `[[old_keys]]` table in `[verification]` for tracking rotated keys
- caching verification results so the server does not re-fetch on every page load
- surfacing a verification summary on the main `/` page, not just `/verification`

### CLI expansion

The current CLI covers `init`, `validate`, `inspect`, `serve`, `doctor`,
`fetch`, `dump`, `keygen`, `sign`, and `verify`. The spec additionally calls for:

- `build` for static export
- richer `fetch` with more complete ownership comparisons
- stronger validation diagnostics (URL format, missing keys)
- a more capable `inspect` for wheel inspection

### Packaging conventions

The roadmap still needs a final answer for where `pypi_profile.toml` lives inside a wheel. The remaining-work notes lean toward a predictable packaged resource location and follow-on loader/build updates.

### Plugin architecture

The intended plugin model is broader than the current one. Planned hooks include:

- extra pages
- extra routes
- template globals
- validators
- verification backends

The spec also expects code execution to stay opt-in and clearly separated from data-only mode.

### Schema and validation

The remaining-work notes call out:

- a `schema_version`
- published JSON Schema output
- additional fields such as skills and resume links
- stricter date validation
- stronger verification-related checks

### Live metadata enrichment

The current fetch path already talks to PyPI and social/code hosting services, but the roadmap goes further:

- more complete maintainer/ownership comparisons
- cache-aware enrichment for the rendered site and API
- broader package metadata exposure

### Website and design

The spec describes several pages and behaviors that are only partially present today, including:

- better multi-human views
- improved verification badges and accessibility handling
- richer metadata tags
- print or resume export support

### Static export and hosting

Phase 2 in the spec adds static output so a rendered profile can be published to GitHub Pages, Netlify, Cloudflare Pages, or similar hosts without a live FastAPI server.

## Practical reading of the roadmap

If you are evaluating the project today:

- treat the existing server, CLI, and signing flow as the **usable core**
- treat static export and full plugin extensibility as **planned but not finished**
- use the spec to understand the intended direction, not the exact shipped feature set
