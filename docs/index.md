# pypi-profile

`pypi-profile` is a PyPI-centered profile site generator for package publishers. It lets a maintainer publish a TOML profile, validate it, inspect it, and serve it as a small FastAPI site with matching JSON endpoints.

## What it is

The current implementation ships:

- a `pypi-profile` CLI with `init`, `validate`, `inspect`, `serve`, `doctor`, `fetch`, `dump`, `keygen`, `sign`, `verify`, `update-proofs`, `build`, `find-profiles`, and `gui`
- a TOML-first schema for identity, packages, projects, hiring, contact, succession, and verification data
- a FastAPI + Jinja2 site renderer with summary, packages, projects, resume, hiring, contact, verification, and succession pages
- a static site builder for publishing the rendered profile to GitHub Pages, Netlify, Cloudflare Pages, or similar hosts
- JSON endpoints at `/api/profile.json`, `/api/packages.json`, `/api/projects.json`, `/api/people.json`, and `/api/verification.json`
- a Tkinter desktop GUI for common local authoring, signing, and inspection workflows
- a minimal pluggy integration for discovering installed `pypi_profile.plugins` entry points

## Who it is for

`pypi-profile` is aimed at:

- PyPI maintainers who want a public maintainer profile
- teams and companies that publish multiple Python packages
- consultants and job seekers who want package work, hiring, and contact details in one place
- users evaluating package stewardship, continuity, and contact paths

## As-is today

Right now, the project is best described as an **early reference implementation** of the spec:

- **works now:** authoring `pypi_profile.toml`, validating it, rendering a local site, importing JSON Resume data, fetching live data from PyPI, GitHub, GitLab, and Mastodon, the full minisign signing and verification flow (`keygen`, `sign`, `update-proofs`, `verify`), static export with `build`, and the local desktop GUI
- **works as examples:** the repo includes `john_doe` and `matthewdeanmartin` profile packages that show the format in practice
- **partly wired:** plugins are discoverable through pluggy, but the hook surface is still minimal and the `--allow-code` path is not yet the full extensibility model described in the spec
- **still evolving:** wheel packaging conventions for profile data, richer schema validation, safer and clearer plugin execution boundaries, and deeper metadata verification/reporting

The docs in this site intentionally separate the current shipped behavior from the roadmap in `spec/spec.md` and `spec/remaining.md`.

## Start here

1. Read [Quick start](quickstart.md) to generate and serve a profile.
1. Use [Basic usage](basic-usage.md) for the everyday CLI flow.
1. Use [GUI](gui.md) if you want a desktop interface for local profile editing, inspection, and signing workflows.
1. Use [Advanced usage](advanced-usage.md) for JSON Resume import, fetch, builds, and plugin-oriented setups.
1. Read [Security](security.md) and [Signing and verification](signing.md) before publishing signed claims or enabling code execution.
1. Read [Roadmap](roadmap.md) for the major remaining gaps between the current implementation and the long-term spec.
