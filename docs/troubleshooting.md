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
2. you are expecting extension points that are specified but not fully implemented yet

The current implementation has plugin discovery, but the richer plugin execution model is still roadmap work.

## Signing or verification is missing

That is expected today. The schema already includes verification fields and the spec defines signed claims, but the end-to-end `sign` and `verify` commands are still roadmap items.

## Working from this repository

This repo is a `uv` workspace. Use `uv run`, not bare `python`.

## `uv sync` fails in the monorepo

If `uv sync` fails, re-run it from the package directory you are working in first:

```bash
cd pypi_profile
uv sync
uv run pypi-profile --help
```
