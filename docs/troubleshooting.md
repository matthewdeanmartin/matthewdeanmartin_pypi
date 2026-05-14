# Troubleshooting

## `Cannot find pypi_profile.toml`

Make sure you are passing one of the source types the loader supports:

- a direct TOML path
- a directory that contains `pypi_profile.toml`
- an installed package name with an accessible `pypi_profile.toml`

## `pypi_ds` is missing

The server depends on the `pypi_ds` design system package for templates and static assets. If `doctor` reports it missing, install the project with its normal runtime dependencies instead of running the package in isolation.

## `fetch` does not return everything I expected

The current fetch implementation is opportunistic. It only queries services that are represented in the profile or inferable from the current data, and its output is cached in `.pypi_profile_cache/`.

Delete that cache directory if you want a fresh fetch.

## Plugin behavior is not showing up

That is usually one of two things:

1. the plugin package is not installed as a `pypi_profile.plugins` entry point
1. you are expecting extension points that are specified but not fully implemented yet

The current implementation has plugin discovery, but the richer plugin execution model is still roadmap work.

## `keygen`, `sign`, or `verify` says `py-minisign is required`

These commands need the optional `py-minisign` dependency. Install it:

```bash
pipx install "pypi-profile[sign]"
# or, if pypi-profile is already installed via pipx:
pipx inject pypi-profile py-minisign
```

Run `pypi-profile doctor` to confirm it is importable.

## `verify` reports `unverified` even though the token is on the page

The verifier performs a plain HTTP GET. If the token appears only in
JavaScript-rendered content (a single-page app, a React component, etc.) the
fetch will not find it. Place the token in a section of the page that is present
in the raw HTML response.

Also check that the `subject` URL in the token exactly matches the `url` field
in `[[profiles]]`. A redirect target is not the same as the declared URL.

## The secret key was lost or committed to version control

Generate a new keypair with `pypi-profile keygen --force`, update `public_key`
in your TOML, republish the package, and re-sign all external claims. Old tokens
signed by the previous key will fail verification against the new public key.

See [Signing and verification](signing.md) for the full key-rotation guidance.

## Working from this repository

This repo is a `uv` workspace. Use `uv run`, not bare `python`.

## `uv sync` fails in the monorepo

If `uv sync` fails, re-run it from the package directory you are working in first:

```bash
cd pypi_profile
uv sync
uv run pypi-profile --help
```
