# Advanced usage

## Import from JSON Resume

The current importer can translate a JSON Resume file into the `pypi-profile` data model:

```bash
pypi-profile init --from-json-resume resume.json --output pypi_profile.toml
```

The importer already maps common fields such as:

- display name and summary
- location
- external profiles
- contact email
- work history
- projects

## Merge live service data

You can ask `init` to prefill from network sources:

```bash
pypi-profile init --username your-pypi-name --fetch
```

Or fetch against an existing profile:

```bash
pypi-profile fetch pypi_profile.toml
```

As implemented today, fetch can compare declared packages with PyPI metadata and enrich the profile from GitHub, GitLab, Mastodon, and `FUNDING.yml`.

## Use installed profile packages

The repo demonstrates the intended model with profile packages such as `matthewdeanmartin` and `john_doe`.

Once a profile package is installed, commands that accept a `source` can target the package name directly if `pypi_profile.toml` is available through the installed distribution metadata.

## Plugin-oriented setup

`pypi-profile` discovers `pypi_profile.plugins` entry points through pluggy. Today, that means package discovery and hook registration are present, but the hook surface is still deliberately small.

Use the current plugin path for **data contribution experiments**, not for a fully stable extension contract yet. The broader plugin roadmap includes extra pages, routes, Jinja globals, validators, and verification backends.

## `--allow-code`

The `serve` command exposes `--allow-code`, but the full safe-by-default plugin execution model described in the spec is still incomplete. Treat this as an evolving feature area rather than a finished extension API.

## Static builds and stored proofs

`pypi-profile build` generates a fully static site that can be deployed to
GitHub Pages, Cloudflare Pages, or any static host. The build runs without the
private key, so it cannot generate signing proofs on the fly.

The solution is to store proofs in the TOML before committing:

```bash
# Sign all URLs and write stored_proof into the TOML
pypi-profile update-proofs pypi_profile.toml

# Then build
pypi-profile build pypi_profile.toml --output dist/ --base-url /yourrepo
```

The `stored_proof` values in the TOML contain no secret material — they are safe
to commit. Anyone who fetches your published profile package sees the same data.

When new external profile URLs are added, run `update-proofs` again (it skips
URLs that already have a `stored_proof`). After rotating your signing key, run:

```bash
pypi-profile update-proofs pypi_profile.toml --force
```

## Machine-readable output

The current server already exposes JSON views for profile, package, project, people, and verification data. That makes `pypi-profile` usable as both a human-facing profile site and a structured data source.
