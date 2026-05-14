# Roadmap

This page summarizes the roadmap **as inferred from `spec/spec.md` and `spec/remaining.md`**. It is intentionally forward-looking; do not read it as a list of features that are already shipped.

## Highest-priority gaps

The largest gaps between the current implementation and the spec are:

1. a stable, documented distribution layout for `pypi_profile.toml` inside published wheels and installed distributions
2. stronger validation and schema hardening, including versioning and richer consistency checks
3. a clearer and safer plugin execution model around `--allow-code`
4. better inspection, publishing, and UX polish around the now-shipped GUI and static build workflow

## Planned work areas

### Signing and verification

The core signing flow is shipped. The remaining gaps are mostly around polish and lifecycle handling:

- key rotation support: marking claims signed by an old key as `expired` rather
  than `invalid`
- an `[[old_keys]]` table in `[verification]` for tracking rotated keys
- caching verification results so the server does not re-fetch on every page load
- surfacing a verification summary on the main `/` page, not just `/verification`

### CLI expansion

The CLI surface is now much broader than it was earlier in the project. It includes `init`, `validate`, `inspect`,
`serve`, `doctor`, `fetch`, `dump`, `keygen`, `sign`, `verify`, `update-proofs`, `build`, `find-profiles`, and
`gui`.

The bigger remaining CLI/documentation gaps are:

- richer `fetch` with more complete ownership and metadata comparisons
- stronger validation diagnostics such as URL checking and missing-key consistency warnings
- a more capable `inspect` for wheel and installed-distribution inspection
- clearer end-user docs for GUI-first and static-build-first workflows

### Packaging conventions

The roadmap still needs a final answer for where `pypi_profile.toml` lives inside a wheel, plus matching loader and
inspection behavior for installed packages.

### Plugin architecture

The intended plugin model is broader than the current one. The main remaining work is not basic discovery; it is
making the execution boundary safer, clearer, and more explicit.

Planned hooks and behaviors still include:

- extra pages
- extra routes
- template globals
- validators
- verification backends

The spec also expects:

- code execution to stay opt-in and clearly separated from data-only mode
- plugin loading to be impossible in the default safe path
- clearer operator-facing warnings when `--allow-code` is enabled

### Schema and validation

The remaining-work notes call out:

- a `schema_version`
- published JSON Schema output
- additional fields such as skills and resume links
- stricter date validation
- stronger verification-related checks

### Live metadata enrichment

The current fetch path already talks to PyPI and social/code hosting services. The remaining work is to make the
results deeper and more trustworthy:

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

Static export is now shipped. The remaining roadmap items are mostly around the publishing experience:

- better documentation for GitHub Pages, Netlify, and Cloudflare Pages deployment
- graceful handling for dynamic UI pieces that do not make sense in a static export
- clearer expectations for how future plugin-provided dynamic features should degrade in static builds

### GUI and local authoring UX

The desktop GUI is now shipped, but there is still room to improve the overall authoring experience:

- broader GUI coverage for commands such as static build and profile discovery
- better onboarding for first-run users
- clearer multi-identity key management guidance
- more workflow documentation that treats the GUI as a first-class entry point, not only a wrapper around CLI flags

## Practical reading of the roadmap

If you are evaluating the project today:

- treat the existing server, CLI, signing flow, static build, and GUI as the **usable core**
- treat wheel-packaging conventions, full plugin extensibility, and schema hardening as the biggest unfinished areas
- use the spec to understand the intended direction, not the exact shipped feature set
