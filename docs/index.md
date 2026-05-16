# pypi-profile

`pypi-profile` is a PyPI-centered profile site generator for package publishers. It lets you keep profile data in `pypi_profile.toml`, sign public identity claims, render a live or static site, and ship the same profile data inside a Python package.

## What ships today

The current implementation includes:

- a `pypi-profile` CLI with `init`, `validate`, `inspect`, `serve`, `doctor`, `fetch-claims`, `fetch`, `dump`, `keygen`, `sign`, `verify`, `update-proofs`, `build`, `find-profiles`, `gui`, `key-info`, `key-list`, `key-rotate`, `key-recover`, `key-export`, and `key-import`
- a Tkinter desktop GUI for the easier local authoring flow
- a FastAPI + Jinja2 site renderer with matching JSON endpoints
- a static site builder for publishing to GitHub Pages, Netlify, Cloudflare Pages, or another static host
- minisign-based signing and verification for proof-of-control claims
- a minimal pluggy integration for discovering installed `pypi_profile.plugins` entry points

## Start here

1. Use [Quick Start - GUI](gui.md) for the easiest end-to-end flow.
1. Use [Quick Start - CLI](quickstart.md) if you want to stay in the terminal.
1. Read [Usage](basic-usage.md) for ongoing maintenance tasks after the first setup.
1. Read [Key management](key-management.md) before rotating, exporting, importing, or recovering signing keys.
1. Read [Signing and verification](signing.md) for the trust model and what signed claims do and do not prove.
1. Read [Advanced usage: pluggy plugins](advanced-usage.md) for the current extension story.

## Current status

- **Works now:** authoring `pypi_profile.toml`, importing JSON Resume data, fetching live metadata, generating keys, signing and verifying external claims, building a static site, and using the GUI.
- **Works as examples:** the repo includes `john_doe` and `matthewdeanmartin` profile packages that include `pypi_profile.toml` in published distributions.
- **Still early:** the pluggy surface is real but intentionally small, and the broader extension model described in the spec is not fully wired yet.

The docs here describe the code as it exists now, not the longer-term spec target.
