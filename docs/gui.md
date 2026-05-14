# GUI

`pypi-profile` includes a Tkinter desktop GUI for the common local workflows around creating, checking, serving,
and signing a profile.

Launch it with:

```bash
pypi-profile gui
```

## What the GUI is for

The GUI is a local convenience layer over the CLI. It is useful when you want to:

- work with a `pypi_profile.toml` file without remembering every CLI flag
- inspect the current TOML and parsed JSON output side by side
- run signing flows with a selected key and see command output in one window
- add a new identity/profile site entry without manually editing TOML for each field

It is not a separate backend. It runs the same local commands the CLI exposes.

## Layout

The window is organized into three areas:

1. **Top bar**: choose the active profile, active signing key, and optional key password.
2. **Left panel**: choose a command. Setup commands and profile commands are grouped separately.
3. **Center and right panels**: fill in arguments, run the command, read output, and view command help.

The top bar also shows:

- the resolved path of the active profile
- the PyPI username detected from the TOML
- the public key currently present in `[verification]`
- whether a usable keyring backend was detected

## How command execution works

There are two interaction modes:

- **read-only commands** run automatically when selected
- **write or long-running commands** wait for you to press **Run**

The output panel shows the underlying command and its combined stdout and stderr.

Use **Stop** to terminate a long-running command such as `serve`.

## Available commands in the GUI

### Setup commands

- **Doctor**: checks local dependencies and signing-key availability
- **Init**: creates a starter `pypi_profile.toml`
- **Keygen**: generates a minisign keypair

### Profile commands

- **Inspect**: summary view of the active profile
- **Validate**: schema validation for the TOML
- **Display TOML**: raw file contents
- **Display JSON**: parsed profile JSON
- **Fetch**: live metadata fetch from supported services
- **Verify Claims**: checks proof-of-control tokens on external URLs
- **Serve**: runs the local FastAPI site preview
- **Sign Claim**: signs a single `controls-url` proof
- **Update Proofs**: signs all profile URLs and writes `stored_proof` values
- **Add Identity Site**: appends a new `[[profiles]]` entry using platform templates

## Recommended workflow

For a first-time setup:

1. run **Init**
2. select the resulting `pypi_profile.toml` in the top bar
3. run **Validate**
4. run **Serve**
5. if you want signed claims, run **Keygen**, then **Sign Claim** or **Update Proofs**

For an existing profile:

1. select the TOML in the top bar
2. use **Inspect**, **Display TOML**, and **Display JSON** to review it
3. use **Fetch** to compare live service data
4. use **Verify Claims** to confirm external proof tokens still validate

## Signing keys in the GUI

The GUI has a global signing-key picker in the top bar.

- If a system keyring backend is active, the CLI normally loads the secret key from the keyring automatically.
- The file picker is still useful when you keep multiple keys or want to point at a non-default disk key.
- The password field is mainly for the fallback case where you are using a password-protected disk key without a
  usable keyring backend.

For multi-identity setups, switch the selected key before running **Sign Claim** or **Update Proofs**.

## Safety notes

- `Serve` keeps `--allow-code` **off by default**.
- Only enable plugin code execution if you trust the installed code path.
- The GUI runs local subprocesses for the same commands you could run in the terminal, so it should be treated as a
  local authoring tool, not a sandbox.

See [Security](security.md) for the broader signing and code-execution guidance.
