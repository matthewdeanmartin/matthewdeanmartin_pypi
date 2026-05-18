# Still To Do

These are the most important gaps I still see in the app after the current quality, test, and dry-run work.

## Packaging and profile discovery

- The wheel/install-time location for `pypi_profile.toml` is still not a settled contract. That makes installed-package
  discovery less predictable than source-tree discovery.
- `inspect` and related resolution paths are strongest for local files and package directories; the "installed profile
  package" story still needs to be hardened and documented.

## Trust and verification lifecycle

- Key rotation and recovery exist, but there is not yet a first-class history model for old keys. That means previously
  published proofs cannot be explained or surfaced cleanly after a rotation.
- Verification is still focused on current proof checking. The app does not yet present a richer trust timeline such as
  rotated keys, superseded proofs, or cached verification history.

## Data validation and schema maturity

- The schema still needs a versioning story (`schema_version`) so future profile changes can evolve without ambiguity.
- Several fields that matter to real profiles still look under-modeled or under-validated, especially date-heavy
  sections and richer hiring/resume metadata.
- A published JSON Schema artifact would make downstream tooling, editor support, and external validation much easier.

## Fetch and enrichment workflow

- `fetch` is useful as a CLI action, but the fetched data is not yet a durable app feature. There is still no clear
  cache/persistence layer for fetched package and profile evidence.
- The site does not yet fully surface live enrichment results as a coherent user-facing trust signal across pages.

## GUI depth

- The GUI is a capable command launcher, but it is not yet a full profile editor. It still leans on CLI semantics rather
  than offering richer form validation, previews, and guided recovery flows.
- Long-running actions are serviceable, but the GUI could still use better progress, cancellation, and error explanation
  for non-happy-path workflows.

## Plugin and safe-execution story

- The repo still describes a plugin-extensible future more strongly than the shipped app exposes it. Plugin hooks, extra
  routes, and template integration need a clearer supported contract.
- The `allow-code` path needs stronger end-user documentation and clearer boundaries around what is and is not executed.

## Static publishing polish

- Static export works, but the publishing story still needs polish: deployment guidance, static-search behavior, and a
  cleaner contract for dynamic/plugin-backed features.
- The public site UX still has room for targeted template cleanup and better explanation of self-asserted versus
  verified data.
