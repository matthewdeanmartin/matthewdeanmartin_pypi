# Quick start

This is the shortest path from zero to a local profile site.

## 1. Install the CLI

```bash
pipx install pypi-profile
```

You can also use `pip install pypi-profile`, but `pipx` is the cleanest option for the CLI.

## 2. Create a starter profile

```bash
pypi-profile init --username your-pypi-name
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

The default server address is `http://127.0.0.1:8000`.

## 5. Inspect the generated data

```bash
pypi-profile inspect pypi_profile.toml
pypi-profile dump pypi_profile.toml
```

## Optional: add signed proof-of-control

This requires `py-minisign`:

```bash
pipx install "pypi-profile[sign]"
```

Generate a keypair once:

```bash
pypi-profile keygen
```

Paste the printed public key into `[verification]` in your TOML, then sign a
claim for each external URL you want to link:

```bash
pypi-profile sign controls-url pypi_profile.toml \
    --url https://github.com/your-name
```

Paste the output token onto that external page, then verify:

```bash
pypi-profile verify pypi_profile.toml
```

See [Signing and verification](signing.md) for the full explanation of what
this proves and what it does not.

## Optional: bootstrap from existing data

If you already have a JSON Resume file:

```bash
pypi-profile init --from-json-resume resume.json --output pypi_profile.toml
```

If you want to prefill from live services during init:

```bash
pypi-profile init --username your-pypi-name --fetch
```
