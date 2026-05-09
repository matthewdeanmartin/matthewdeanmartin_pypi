# Roadmap

This page summarizes the roadmap **as inferred from `spec/spec.md` and `spec/remaining.md`**. It is intentionally forward-looking; do not read it as a list of features that are already shipped.

## Highest-priority gaps

The largest gaps between the current implementation and the spec are:

1. signed claims and verification flows
2. richer CLI coverage, especially `sign`, `verify`, and `build`
3. a stable distribution layout for `pypi_profile.toml` inside published wheels
4. a fuller plugin system with explicit `allow_code` behavior
5. static site export

## Planned work areas

### Signing and verification

The spec and remaining-work notes point toward:

- minisign-based signing
- public-key material embedded in the profile data
- proof tokens for external profile claims
- a verifier that checks declared external URLs
- verification status surfaced on the website and API

### CLI expansion

The current CLI already covers `init`, `validate`, `inspect`, `serve`, `doctor`, `fetch`, and `dump`, but the spec calls for:

- `build` for static export
- `sign`
- `verify`
- richer `fetch`
- stronger validation diagnostics
- a more capable `inspect`

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

- treat the existing server and CLI as the **usable core**
- treat signed verification, static export, and full plugin extensibility as **planned but not finished**
- use the spec to understand the intended direction, not the exact shipped feature set
