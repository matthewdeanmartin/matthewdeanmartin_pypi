# Developer Documentation

This section explains how `pypi-profile` works internally. It is aimed at anyone who wants to
understand the code, fix a bug, add a feature, or build on top of the tool.

## What the tool does

`pypi-profile` is a **profile site generator** for PyPI package publishers. It lets you:

1. Keep your profile data in a single TOML file (`pypi_profile.toml`).
1. Generate a live or static website from that data.
1. Cryptographically prove you control external accounts (GitHub, Mastodon, etc.).
1. Publish your profile as a Python package that others can install.

The code is structured as a **uv workspace** with four sub-packages:

```
matthewdeanmartin_pypi/
├── pypi_profile/        ← main CLI, server, and plugin host
├── john_doe/            ← example profile plugin (test fixture)
├── matthewdeanmartin/   ← author's own profile plugin (real-world example)
└── pypi_ds/             ← Jinja2 design system and static assets
```

## Topics

- [Architecture overview](architecture.md) — how the modules relate to each other
- [Data model](data-model.md) — TOML schema and Pydantic models
- [Server and templating](server.md) — FastAPI routes, Jinja2 templates, static files
- [Static site builder](builder.md) — how `pypi-profile build` works
- [Signing and verification internals](signing-internals.md) — claims, Ed25519, minisign
- [Plugin system](plugin-system.md) — pluggy integration and profile packages
- [CLI reference](cli-reference.md) — every command explained with examples
- [Fetcher and caching](fetcher.md) — live data from PyPI, GitHub, GitLab, Mastodon
