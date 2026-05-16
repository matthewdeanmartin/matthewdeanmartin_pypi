# Quick Start - CLI

This is the terminal-first path from an empty profile to a published site and package.

## 1. Install the CLI

```bash
pipx install pypi-profile
```

## 2. Init

Create the starting file:

```bash
pypi-profile init --username your-pypi-name --output pypi_profile.toml
```

## 3. Import

The CLI does import through `init`.

Import from live services:

```bash
pypi-profile init --username your-pypi-name --fetch --output pypi_profile.toml --force
```

Import from JSON Resume:

```bash
pypi-profile init --from-json-resume resume.json --output pypi_profile.toml --force
```

Check the result:

```bash
pypi-profile inspect pypi_profile.toml
```

## 4. Add identity sites

The CLI does not have a dedicated `add-identity-site` command. Add `[[profiles]]` entries directly in `pypi_profile.toml`.

```toml
[[profiles]]
kind = "github"
label = "GitHub"
url = "https://github.com/your-name"
verification = "self_asserted"
rel_me = true
stored_proof = ""

[[profiles]]
kind = "website"
label = "Personal site"
url = "https://example.com"
verification = "self_asserted"
rel_me = true
stored_proof = ""
```

## 5. Key generation

Generate the minisign keypair:

```bash
pypi-profile keygen
```

If `pypi_profile.toml` is in the current directory, `keygen` patches `[verification].public_key` automatically.

## 6. Sign claims and update proofs

Sign a single URL when you want the token immediately:

```bash
pypi-profile sign controls-url pypi_profile.toml --url https://github.com/your-name
```

Then batch-write `stored_proof` values into the TOML:

```bash
pypi-profile update-proofs pypi_profile.toml
```

Use `--force` when you need to re-sign existing entries.

## 7. Publish signatures

Publish each proof token on the external page it proves. For CLI workflows, that usually means:

1. copy the token printed by `sign`, or copy `stored_proof` from `pypi_profile.toml`
1. paste it onto the matching external page
1. verify the round-trip

```bash
pypi-profile verify pypi_profile.toml
```

If the platform is character-limited, `sign` supports `--compact`.

## 8. Publish the static site

Build the static output:

```bash
pypi-profile build pypi_profile.toml --output dist
```

Use `--base-url` for subpath deployments such as GitHub Pages project sites:

```bash
pypi-profile build pypi_profile.toml --output dist --base-url /your-repo
```

Publish the generated `dist` directory to your static host.

## 9. Publish the package

Package publishing is outside `pypi-profile` itself. Publish the Python distribution that contains `pypi_profile.toml`.

In the example profile packages in this repo, that means:

- the wheel includes `pypi_profile.toml`
- the package can be built with `uv build`
- PyPI upload happens through the package's normal release workflow

If you are using the pluggy-style package layout, also register a `pypi_profile.plugins` entry point as described in [Advanced usage: pluggy plugins](advanced-usage.md).
