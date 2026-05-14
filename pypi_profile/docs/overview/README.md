# pypi-profile

`pypi-profile` is a PyPI maintainer profile generator centered on a `pypi_profile.toml` file.

It can scaffold a profile, validate it, inspect it, serve it locally as a small FastAPI site, emit JSON for the
same data, and sign proof-of-control claims for external profile URLs.

## What ships today

The current package includes:

- a CLI with `init`, `validate`, `inspect`, `serve`, `dump`, `doctor`, `fetch`, `keygen`, `sign`, `verify`,
  `update-proofs`, `build`, `find-profiles`, and `gui`
- a TOML-first schema for identity, packages, projects, hiring, contact, succession, and verification data
- a FastAPI + Jinja2 renderer for the profile site and API endpoints
- a minisign-based verification flow for proving co-control of external links

## How to read the docs

These docs describe the **usable, shipped behavior** of the package.

They are not a promise that every future extension idea is already stable. In particular, this doc set focuses on
the current authoring, serving, and verification workflow.

## Start here

1. Read [Installation](../installation.md) to pick an install method and optional extras.
1. Follow [Quick start](../usage/quickstart.md) to create and preview a profile.
1. Read [Security](../security.md) before publishing signed proofs or enabling code execution.

## Core workflow

For most users, the day-to-day loop is:

1. create `pypi_profile.toml`
1. run `pypi-profile validate`
1. run `pypi-profile serve`
1. optionally use `inspect`, `dump`, `fetch`, `build`, or `verify`
