# PEP: `pypi-profile` — PyPI’s Missing Profile Page

## Abstract

This document specifies `pypi-profile`, a public profile website generator and server for Python package publishers. The project provides a way for PyPI account holders, teams, companies, foundations, and other publishing principals to publish human-readable and machine-readable profile data as PyPI packages.

A `pypi-profile` site answers a question that PyPI itself currently leaves mostly implicit: **who is behind this package, what role do they play, how can they be contacted, what else do they maintain, and how can a reader gain confidence that the profile is controlled by the same party that publishes the PyPI package?**

The initial implementation provides a FastAPI + Jinja2 website with a component library visually and idiomatically close to PyPI’s design language. A future phase adds static site export and data-only installation via a companion `data-package` tool.

## Status

Draft.

## Motivation

PyPI is excellent at presenting package metadata, release history, distribution files, and project links. It is much less expressive as a profile system for package publishers. Maintainers often need to communicate information that does not naturally fit inside a single package page, including:

* who they are;
* whether they are an individual, team, company, LLC, foundation, or other principal;
* what packages they maintain;
* what their role is in each package;
* whether a project is active, archived, deprecated, seeking maintainers, or in security-only mode;
* how to hire, contract with, sponsor, or contact them;
* what their professional background is;
* who can speak for a project if the current maintainer is unavailable;
* which external profiles are actually controlled by the same PyPI publisher.

`pypi-profile` fills this gap by treating PyPI itself as the root publication channel. The basic proof is simple: **the PyPI account holder published a package containing profile data and verification material.** Additional evidence can then be layered on top through signatures, OIDC-based CI metadata, and signed claims placed on external profile sites.

The tone and positioning of the project is:

> This is PyPI’s missing profile page.

The project should be useful to open-source maintainers, consultants, companies, teams, job seekers, technical recruiters, and users trying to evaluate the maintenance and continuity story behind packages they depend on.

## Goals

`pypi-profile` aims to provide:

1. A standard package-based profile format for Python package publishers.
2. A TOML-first, human-editable data model.
3. A FastAPI + Jinja2 server for rendering PyPI-inspired public profile websites.
4. A Jinja2 component library that maps PyPI package-page idioms to profile-page idioms.
5. Support for multiple kinds of principals, including individuals, teams, companies, LLCs, foundations, and collectives.
6. Support for one profile package describing one or many human participants.
7. Clear distinction between self-asserted claims and verified claims.
8. A plugin mechanism, based on pluggy, that can add data, pages, endpoints, validators, signing helpers, and UI components.
9. A safe-by-default execution model where profile code is not run unless explicitly enabled.
10. Tools for creating, validating, serving, signing, verifying, inspecting, and eventually exporting profile websites.
11. A future path for static site generation and data-only consumption.

## Non-Goals

`pypi-profile` is not intended to be:

1. A replacement for PyPI or Warehouse.
2. A package publishing tool.
3. A general social network.
4. A full LinkedIn replacement.
5. A payment platform.
6. A private profile hosting system.
7. A secret manager.
8. A trustless identity system.
9. A browser-based profile editor in the initial version.
10. A sandbox for untrusted arbitrary Python code.

The project may eventually inspire Warehouse itself. If Warehouse or another PyPI-adjacent service adopts the core ideas, that is considered a success rather than a conflict.

## Terminology

### Principal

A principal is the entity represented by a profile package. A principal may be:

* an individual person;
* a pseudonymous person;
* a team;
* a company;
* an LLC;
* a nonprofit;
* a foundation;
* an open-source collective;
* a project stewardship group.

### Human

A human is a person associated with a principal. A profile package may describe one human or many humans.

### Profile Package

A profile package is a Python distribution published to PyPI that contains `pypi-profile` data. It may optionally contain code implementing pluggy hooks, but code execution is disabled by default.

### Data-Only Profile Package

A data-only profile package is a package whose profile data can be extracted and rendered without importing or executing Python code.

### Verified Claim

A verified claim is a claim supported by a verification mechanism such as:

* publication by a PyPI account;
* a public key included in a PyPI-published profile package;
* a signature placed on an external website or profile page;
* OIDC-based CI metadata associated with the package publication process;
* other supported verification backends.

### Self-Asserted Claim

A self-asserted claim is profile data published by the profile package but not independently verified by `pypi-profile`.

Self-asserted data is useful and expected. The UI must label it honestly.

### Profile Site

A profile site is the rendered website served or generated by `pypi-profile`.

## Package Naming

The canonical project name is:

```text
pypi-profile
```

The import package is:

```python
pypi_profile
```

The CLI command is:

```bash
pypi-profile
```

Profile packages SHOULD use one of the following naming conventions:

```text
pypi-profile-<pypi-username>
<pypi-username>-profile
pypi-profile-<organization-or-team-name>
```

The preferred convention is:

```text
pypi-profile-<pypi-username>
```

A profile package MAY describe multiple humans, especially when the principal is a team, company, collective, or organization.

## Data Model Overview

Profile data is TOML-first. TOML is preferred because it is human-editable, familiar to Python package publishers, and already central to modern Python packaging through `pyproject.toml`.

The canonical profile file SHOULD be located at:

```text
pypi_profile.toml
```

Inside a wheel, the profile file SHOULD be stored in a predictable data location, such as:

```text
<distribution>.dist-info/pypi_profile.toml
```

or another location specified by the final packaging implementation.

The profile schema SHOULD support at least the following sections:

```toml
[profile]
kind = "individual" # individual | team | company | llc | foundation | collective | project | other
display_name = "Example Maintainer"
summary = "Python maintainer, consultant, and package publisher."

[identity]
legal_name = "Example Maintainer"
display_name = "Example Maintainer"
pypi_username = "example"
pronouns = ""
timezone = "America/New_York"
location = "United States"

[[humans]]
id = "example"
display_name = "Example Maintainer"
role = "Owner"

[[profiles]]
kind = "github"
label = "GitHub"
url = "https://github.com/example"
verification = "signed-profile-claim"

[[contact_methods]]
kind = "email"
label = "Professional email"
value = "example@example.com"
audience = ["hiring", "consulting", "security"]
visibility = "public"

[[packages]]
name = "example-package"
role = "maintainer"
state = "active"
summary = "An example Python package."

[[projects]]
name = "Example Project"
url = "https://example.com/project"
role = "creator"
state = "active"

[[work_experience]]
organization = "Example LLC"
title = "Principal Consultant"
start_date = "2020-01"
end_date = "present"
summary = "Python, backend, and packaging work."

[hiring]
open_to_work = true
employment = true
contracting = true
consulting = true
speaking = false
sponsorship = true

[contracting]
legal_entity = "Example LLC"
engagement_types = ["fixed-bid", "hourly", "retainer"]

[succession]
policy = "If unreachable for 90 days, contact the named successor."

[[succession.contacts]]
name = "Successor Name"
contact = "successor@example.com"
scope = ["example-package"]

[verification]
public_key = "..."
preferred_signature_backend = "ssh"
```

The exact schema may evolve, but the first stable release MUST preserve the distinction between identity, package/project roles, contact methods, hiring/contracting metadata, verification, and succession.

## Claim Status

Every meaningful profile claim SHOULD be classifiable as one of:

```text
self_asserted
verified
unverified
invalid
expired
unknown
```

The UI MUST NOT imply that all profile data is verified merely because it appears in a package published on PyPI.

The UI SHOULD visibly distinguish between:

* “Published by this PyPI account”;
* “Self-asserted by the profile package”;
* “Verified by signature”;
* “Verified by OIDC publication metadata”;
* “Verification failed”;
* “Verification not attempted.”

## Verification Model

The root proof is publication through PyPI: a PyPI account holder published a profile package.

Additional verification is based on public keys and signed claims. A profile package may include a public key. The corresponding private key is used to sign claims that can be placed on external websites or profile pages controlled by the same principal.

For example, a user might place a signed claim in:

* a personal website;
* a GitHub profile README;
* a GitLab profile page;
* a Mastodon bio or profile metadata field;
* a project documentation site;
* a PyPI project description;
* another profile system that permits user-editable text.

`pypi-profile` can then fetch public profile sites and look for signed data chunks proving that the holder of the private key associated with the PyPI-published profile package also controls the external profile location.

### Signed Claim Shape

A signed claim SHOULD include:

* profile package name;
* PyPI username or project owner claim;
* claim type;
* subject URL;
* issued timestamp;
* optional expiration timestamp;
* nonce or unique claim ID;
* signature backend;
* signature value.

Example conceptual claim:

```json
{
  "profile_package": "pypi-profile-example",
  "pypi_username": "example",
  "claim": "controls-url",
  "subject": "https://github.com/example",
  "issued_at": "2026-05-09T00:00:00Z",
  "expires_at": "2027-05-09T00:00:00Z",
  "key_id": "default",
  "signature_backend": "ssh",
  "signature": "..."
}
```

The serialized public form SHOULD be compact enough to paste into website bios and profile fields.

Example public text:

```text
pypi-profile-proof: <encoded-signed-claim>
```

The exact encoding is deferred to the implementation specification. It SHOULD be URL-safe and copy-paste friendly.

### Signature Backends

The implementation SHOULD support pluggable signature backends.

Initial candidate backends include:

* SSH signatures;
* Minisign;
* Sigstore;
* JWS/JOSE;
* GPG.

The first implementation SHOULD choose one simple default and leave room for others. SSH signatures are attractive because many developers already have SSH keys, but the final choice should consider portability, library quality, Windows support, and ease of pasting proofs into profile fields.

## OIDC and CI Evidence

A profile package MAY include evidence that publication is tied to a GitHub account, GitLab account, or another OIDC-capable CI identity.

This evidence SHOULD be represented separately from signed website claims. OIDC evidence proves something about the package publication workflow. Signed external claims prove control over other public profile locations.

The UI SHOULD describe OIDC-backed claims carefully. For example:

```text
This package was published through a trusted publishing workflow associated with github.com/example/repo.
```

This is different from saying:

```text
This human identity is legally verified.
```

`pypi-profile` MUST avoid overstating what technical proofs establish.

## Plugin Architecture

`pypi-profile` uses pluggy for extensibility.

Plugins may provide:

* additional profile data;
* validators;
* renderable sections;
* Jinja2 components;
* FastAPI routes;
* API endpoints;
* external profile fetchers;
* signature helpers;
* verification backends;
* package/project metadata enrichers;
* static export hooks.

Plugins SHOULD be discovered through Python entry points.

Example:

```toml
[project.entry-points."pypi_profile.plugins"]
github = "example_profile.github_plugin:plugin"
```

A plugin MAY add pages and endpoints to the FastAPI application. Conceptually, a plugin behaves like a FastAPI controller or router provider.

Plugins SHOULD be async-friendly because the web server is FastAPI-based. Synchronous hooks MAY be supported for simple validators and data transforms.

### Plugin Safety

By default, `pypi-profile` MUST NOT execute code from arbitrary profile packages.

Code-bearing plugins require explicit opt-in:

```bash
pypi-profile serve pypi-profile-example --allow-code
```

Without `--allow-code`, the tool MUST operate in data-only mode, reading only static profile data and rendering built-in views.

Users concerned about arbitrary package execution SHOULD use the phase 2 `data-package` pattern, which downloads wheel data through a side channel and references the profile data without importing or executing package code.

Users who enable code execution SHOULD be advised to run the server in a container or other isolated environment.

## Data-Only Mode

Data-only mode is the default safe behavior.

In data-only mode, `pypi-profile`:

* reads profile data;
* validates the profile schema;
* renders built-in pages;
* performs verification using built-in safe mechanisms;
* does not import profile package Python modules;
* does not execute profile package plugin hooks;
* does not register profile-package-provided FastAPI routes.

A data-only profile package may still include rich data. It simply cannot extend runtime behavior unless the operator opts in to code execution.

## Phase 2: `data-package` Integration

Phase 2 assumes a companion `data-package` tool exists.

The `data-package` tool downloads and exposes only the data resources from a wheel or other distribution artifact. It avoids importing or executing Python code from that distribution.

In phase 2, `pypi-profile` SHOULD support workflows such as:

```bash
data-package install pypi-profile-example
pypi-profile serve pypi-profile-example --data-only
```

or:

```bash
pypi-profile serve pypi-profile-example --data-package
```

The precise CLI integration is deferred, but the intent is clear: users should be able to render profile data from a PyPI-published package without executing that package’s code.

## Website Behavior

The primary v1 behavior is serving a public profile website:

```bash
pypi-profile serve pypi-profile-example
```

The server uses:

* FastAPI for routing and API endpoints;
* Jinja2 for server-side rendering;
* a PyPI-inspired component library;
* optional plugin-provided routers and components when code execution is enabled.

The site SHOULD include a summary page and detail pages.

### Summary Page

The summary page SHOULD present:

* principal name and kind;
* PyPI publication proof summary;
* verification status summary;
* primary contact methods;
* package and project highlights;
* hiring/contracting availability;
* current maintenance status;
* links to detail pages.

### Detail Pages

Detail pages MAY include:

* `/people` or `/humans`;
* `/packages`;
* `/projects`;
* `/resume`;
* `/hiring`;
* `/contracting`;
* `/verification`;
* `/succession`;
* `/contact`;
* plugin-provided pages.

A profile package representing many humans SHOULD have a summary page for the principal and detail pages for individual humans.

## PyPI-Inspired Design Language

The default theme SHOULD closely follow PyPI’s design language without requiring byte-for-byte cloning.

PyPI package-page idioms should be mapped to profile-page idioms. For example:

| PyPI Idiom          | `pypi-profile` Idiom                        |
| ------------------- | ------------------------------------------- |
| Project name        | Principal or profile name                   |
| Project description | Profile summary                             |
| Release history     | Career/package timeline                     |
| Project links       | External profiles/contact links             |
| Maintainers         | Humans and roles                            |
| Verified details    | Verification panel                          |
| Package classifiers | Skills, roles, availability, project states |
| Security contact    | Security and succession contacts            |

The design should feel immediately familiar to Python package users.

The implementation SHOULD avoid copying PyPI branding in a way that implies official PyPI endorsement unless such endorsement exists.

## Jinja2 Component Library

`pypi-profile` includes a Jinja2 component library for PyPI-like profile websites.

Components SHOULD include:

* profile header;
* verification badge;
* claim status badge;
* package card;
* project card;
* human/maintainer card;
* contact method card;
* hiring availability panel;
* contracting panel;
* resume timeline;
* role badge;
* package state badge;
* succession notice;
* proof detail table;
* external profile link list.

The component library SHOULD be usable internally by `pypi-profile` and MAY later be packaged for reuse by other Jinja2 applications.

## Static Site Export

Phase 2 SHOULD include static export:

```bash
pypi-profile build pypi-profile-example --output dist/
```

Static export should degrade gracefully. Server-only features should either:

* be omitted;
* be precomputed;
* be represented as static JSON;
* or be reimplemented with optional client-side JavaScript.

Static export SHOULD support publishing to static hosts such as GitHub Pages, GitLab Pages, Cloudflare Pages, Netlify, or ordinary web servers.

## Machine-Readable Output

The server SHOULD expose machine-readable profile data.

Suggested endpoints:

```text
/api/profile.json
/api/people.json
/api/packages.json
/api/projects.json
/api/claims.json
/api/verification.json
/openapi.json
```

The exact endpoint structure may evolve, but the API SHOULD preserve the same claim-status distinction used by the UI.

Static export SHOULD generate equivalent JSON files where practical.

## CLI

The CLI command is:

```bash
pypi-profile
```

The initial command set SHOULD include:

```bash
pypi-profile init
pypi-profile validate
pypi-profile serve
pypi-profile build
pypi-profile inspect
pypi-profile sign
pypi-profile verify
pypi-profile fetch
pypi-profile doctor
```

### `init`

Creates a starter profile.

Examples:

```bash
pypi-profile init
pypi-profile init --kind individual
pypi-profile init --kind team
pypi-profile init --package-name pypi-profile-example
```

`init` SHOULD be able to create:

* `pypi_profile.toml`;
* a minimal Python package skeleton;
* optional signing key configuration;
* example proofs;
* example package/project entries;
* optional GitHub Actions trusted publishing hints.

Publishing to PyPI remains out of scope for v1.

### `validate`

Validates local profile data.

```bash
pypi-profile validate pypi_profile.toml
```

Validation SHOULD check:

* schema correctness;
* known enum values;
* malformed URLs;
* missing required fields;
* unsupported plugin declarations;
* invalid verification metadata;
* dangerous ambiguity between self-asserted and verified claims.

### `serve`

Runs the FastAPI + Jinja2 website.

```bash
pypi-profile serve pypi-profile-example
pypi-profile serve ./pypi_profile.toml
pypi-profile serve pypi-profile-example --allow-code
```

By default, `serve` MUST NOT execute profile package code.

### `build`

Generates a static site.

```bash
pypi-profile build pypi-profile-example --output dist/
```

This command is phase 2 unless implemented earlier.

### `inspect`

Inspects a wheel, source distribution, installed distribution, or local profile file without executing package code.

```bash
pypi-profile inspect pypi-profile-example-1.0.0-py3-none-any.whl
pypi-profile inspect pypi-profile-example
```

`inspect` SHOULD report:

* discovered profile files;
* whether code plugins are present;
* public keys;
* declared external claims;
* package metadata;
* warnings about execution risk.

### `sign`

Creates signed claims for placement on external sites.

```bash
pypi-profile sign controls-url --url https://github.com/example
pypi-profile sign controls-url --url https://example.com
```

The output SHOULD be copy-paste friendly.

### `verify`

Verifies profile claims.

```bash
pypi-profile verify pypi-profile-example
pypi-profile verify ./pypi_profile.toml
```

Verification SHOULD be able to:

* read public keys from the profile package;
* fetch declared external URLs;
* discover signed claim chunks;
* validate signatures;
* report claim status;
* render verification details for the site.

### `fetch`

Fetches external metadata or live package metadata.

```bash
pypi-profile fetch pypi-profile-example
```

`fetch` MAY retrieve:

* PyPI package metadata;
* GitHub/GitLab project metadata;
* external profile pages;
* verification targets.

Network access SHOULD be explicit or clearly documented.

### `doctor`

Diagnoses local configuration and profile health.

```bash
pypi-profile doctor
```

Checks MAY include:

* Python version;
* installed optional dependencies;
* whether FastAPI/Jinja2 are importable;
* plugin discovery status;
* signature backend availability;
* malformed profile data;
* static export readiness.

## Package and Project Roles

The schema SHOULD support explicit roles. Suggested role values include:

```text
author
creator
owner
maintainer
co-maintainer
contributor
release-manager
security-contact
documentation-maintainer
original-creator
current-steward
former-maintainer
sponsor
employer
client
vendor
successor
```

The schema SHOULD support explicit project/package states. Suggested state values include:

```text
active
maintained
stable
experimental
planning
paused
archived
deprecated
abandoned
transferred
seeking-maintainer
security-only
unmaintained-but-usable
superseded
private
unknown
```

The UI SHOULD make role and state visible, because these details are often more useful than a raw list of package names.

## Succession and Continuity

`pypi-profile` SHOULD support maintainer continuity data.

This is not a legal dead-man-switch system. It is static, self-asserted succession guidance that can help users, co-maintainers, and organizations understand what should happen if a maintainer becomes unavailable.

Suggested fields:

```toml
[succession]
policy = "If I am unreachable for 90 days, contact the named successor."
last_reviewed = "2026-05-09"

[[succession.contacts]]
name = "Successor Name"
contact = "successor@example.com"
scope = ["example-package"]
relationship = "co-maintainer"
verification = "self_asserted"
```

The UI SHOULD label succession data as self-asserted unless independently verified.

## Privacy and Contact Controls

The schema SHOULD support structured contact methods and contact preferences.

Examples:

```toml
[[contact_methods]]
kind = "email"
label = "Security contact"
value = "security@example.com"
audience = ["security"]
visibility = "public"

[contact_preferences]
do_contact_about = ["consulting", "package-maintenance", "security", "speaking"]
do_not_contact_about = ["cryptocurrency", "unpaid-custom-work"]
```

The project SHOULD avoid encouraging users to publish sensitive personal information unnecessarily.

Contact values may be public, obfuscated, or replaced with links to external contact forms.

## Hiring and Resume Use Case

`pypi-profile` is partly a technical resume for people who publish packages to PyPI.

The hiring model SHOULD support:

* employment availability;
* consulting availability;
* contracting availability;
* sponsorship availability;
* commercial support;
* speaking availability;
* preferred contact channels;
* resume links;
* work history;
* skills;
* package/project evidence.

However, `pypi-profile` SHOULD remain package-publisher-centric. It should not become a general-purpose job board or social network.

## Security Considerations

Profile packages are Python packages. Python packages can contain arbitrary code. Therefore, `pypi-profile` MUST be safe by default.

The default behavior MUST NOT import or execute arbitrary profile package code.

Operators who use `--allow-code` are opting into plugin execution. The CLI and documentation SHOULD recommend containers or other isolation mechanisms for public deployments that run third-party profile plugins.

The verification system proves control over keys and publication channels. It does not prove legal identity, employment history, competence, trustworthiness, or absence of malicious intent.

The UI and documentation MUST avoid overstating verification.

## Accessibility Considerations

The default theme SHOULD be accessible.

At minimum, the rendered site SHOULD:

* use semantic HTML;
* provide readable contrast;
* avoid conveying verification state by color alone;
* include text labels for badges;
* support keyboard navigation;
* render useful content without JavaScript;
* make machine-readable JSON available for tooling.

## Compatibility with Warehouse

The project is designed so that Warehouse could adopt or adapt the idea in the future.

To support that possibility, `pypi-profile` SHOULD:

* use clear package metadata conventions;
* avoid unnecessary runtime coupling;
* define a stable data schema;
* expose machine-readable JSON;
* distinguish self-asserted and verified data;
* avoid branding confusion with official PyPI services.

## Reference Implementation Sketch

A reference implementation might use:

* FastAPI for web serving;
* Jinja2 for templates;
* pluggy for plugin hooks;
* Pydantic for validation models;
* `tomllib` for TOML parsing on supported Python versions;
* `tomli` as a compatibility dependency if older Python versions are supported;
* `importlib.metadata` for installed package discovery;
* standard packaging metadata for project inspection;
* optional libraries for signature backends.

The implementation SHOULD keep data parsing separate from plugin execution so that data-only mode remains robust.

## Open Questions

The following questions remain open for future refinement:

1. Which signature backend should be the default?
2. What is the exact wheel-internal location for `pypi_profile.toml`?
3. Should the schema be versioned independently of the package version?
4. Should there be a formal JSON Schema or Pydantic-generated schema artifact?
5. Should `pypi-profile` define a PyPI classifier for profile packages?
6. How much live PyPI metadata should be fetched and compared against self-asserted package roles?
7. What is the exact static export contract for plugin-provided dynamic features?
8. Should the component library be distributed separately from the main CLI/server?
9. Should there be official built-in plugins for GitHub, GitLab, Mastodon, and personal websites in v1?
10. How should expired or rotated verification keys be represented?

## Example User Story

A Python maintainer publishes:

```text
pypi-profile-example
```

The package contains:

* `pypi_profile.toml`;
* public verification key material;
* self-asserted identity, contact, package, project, resume, and hiring data;
* optional plugin code.

A reader or operator runs:

```bash
pypi-profile serve pypi-profile-example
```

By default, the site renders only data from the package. The page looks and feels like a PyPI-native profile page. It shows the principal, packages, roles, project states, contact options, hiring status, and verification summary.

If the maintainer has placed signed proof chunks on GitHub, Mastodon, and a personal website, the verification page shows which claims passed.

If the operator trusts the package enough to execute plugin code, they may run:

```bash
pypi-profile serve pypi-profile-example --allow-code
```

Additional plugin-provided pages and endpoints then become available.

## Success Criteria for Version 1

Version 1 is successful when a PyPI publisher can:

1. Create a TOML-based profile package.
2. Publish that package to PyPI.
3. Run `pypi-profile serve <profile-package>`.
4. See a PyPI-inspired public profile website.
5. Display package/project roles and maintenance states.
6. Display hiring, contracting, contact, resume, and succession information.
7. Clearly distinguish self-asserted from verified claims.
8. Generate signed proof chunks for external sites.
9. Verify at least one external profile claim.
10. Run safely by default without executing profile package code.


And heads up, we will be usin minisign
