# Quick start

This is the shortest path from zero to a local `pypi-profile` site.

## 1. Install the CLI

```bash
pipx install pypi-profile
```

## 2. Create a starter profile

Interactive mode is the default when you run in a terminal:

```bash
pypi-profile init --username your-pypi-name
```

For scripted use:

```bash
pypi-profile init --username your-pypi-name --no-interactive
```

That writes `pypi_profile.toml` in the current directory.

## 3. Validate the file

```bash
pypi-profile validate pypi_profile.toml
```

## 4. Serve the site locally

```bash
pypi-profile serve pypi_profile.toml
```

The default address is `http://127.0.0.1:8000`.

## 5. Inspect the generated data

```bash
pypi-profile inspect pypi_profile.toml
pypi-profile dump pypi_profile.toml
```

`inspect` is a quick human-readable summary. `dump` prints the validated model as JSON.

## Optional: bootstrap from existing data

If you already have a JSON Resume file:

```bash
pypi-profile init --from-json-resume resume.json --output pypi_profile.toml
```

If you want to prefill from live service data:

```bash
pypi-profile init --username your-pypi-name --fetch
pypi-profile fetch pypi_profile.toml
```

## Optional: build a static site

```bash
pypi-profile build pypi_profile.toml --output dist
```

## Optional: add signed proof-of-control

Generate a keypair once:

```bash
pypi-profile keygen
```

Add the printed public key to `[verification]` in your TOML, then sign an external URL claim:

```bash
pypi-profile sign controls-url pypi_profile.toml --url https://github.com/your-name
```

Paste the generated token onto that external page, then store proofs locally:

```bash
pypi-profile update-proofs pypi_profile.toml
pypi-profile verify pypi_profile.toml
```

Read [Security](../security.md) before relying on signed claims in a published profile.
