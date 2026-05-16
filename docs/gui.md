# Quick Start - GUI

The GUI is the easiest way to do the full local workflow: create the profile, add identity sites, generate keys, sign proofs, preview the site, and prepare published output.

Launch it with:

```bash
pypi-profile gui
```

## How the window is organized

1. **Top bar**: active profile, active signing key, optional key password, detected PyPI username, current public key, and keyring status.
1. **Left panel**: commands grouped as Setup, Profile, Website, Keys, and Diagnostics.
1. **Center and right panels**: arguments, output, and built-in command help.

Read-only commands run as soon as you select them. Write commands wait for **Run**.

## End-to-end workflow

### 1. Init

Use **Init** to create the starter `pypi_profile.toml`.

- `--username`: PyPI username
- `--kind`: individual, team, company, llc, foundation, collective, project, or other
- `--output`: output path

After the file exists, select it in the top bar.

### 2. Import

Use **Import** to rewrite the active file with imported data.

The GUI import path runs the CLI `init` flow with `--force` against the active profile path, so it is the GUI way to:

- fetch live data from PyPI, GitHub, GitLab, and Mastodon
- import from a JSON Resume file

### 3. Add identity sites

Use **Add Identity Site** to append a `[[profiles]]` entry without editing TOML by hand.

The GUI currently includes templates for:

- GitHub
- GitLab
- Mastodon
- Bluesky
- LinkedIn
- Twitter / X
- Blogger
- WordPress
- Personal Website
- Stack Overflow
- Keybase
- ORCID
- Other (custom)

The new entry is written directly into `pypi_profile.toml` with `verification = "self_asserted"` and an empty `stored_proof`.

### 4. Key generation

Use **Keygen** to generate the minisign keypair.

- if a usable system keyring is available, the secret key is stored there
- a disk copy is also kept as a fallback
- the generated public key is shown in command output, and the underlying `keygen` command patches a local `pypi_profile.toml` when one is present in the current working directory

### 5. Sign claims and update proofs

Use:

- **Sign Claim** when you want the token for one URL immediately
- **Update Proofs** when you want to sign all `[[profiles]]` entries and write `stored_proof` values into the TOML

### 6. Publish signatures

Use **Signatures** after **Update Proofs**.

That panel shows:

- each current proof token
- the matching URL
- where that token should be pasted for the selected platform

After you paste those tokens onto the public pages you control, run **Verify Claims**.

### 7. Publish the static site

Use:

- **Live Preview** for the FastAPI preview server
- **Build & Preview** for the static-site path

`Build & Preview` runs `build`, serves the output over HTTP, and opens the browser automatically. If you leave `--output` blank, the GUI defaults to `site\<pypi_username>\`.

After previewing, publish the generated folder to your static host.

### 8. Publish the package

The GUI does not publish to PyPI. Publish the Python package that contains `pypi_profile.toml` with your normal package release process after the profile data is ready.

## Ongoing work

After the first setup, use [Usage](basic-usage.md) for the maintenance flow and [Key management](key-management.md) for rotate, recover, export, and import tasks.

## Safety notes

- **Live Preview** keeps `--allow-code` off by default.
- The GUI is a local wrapper around the same commands the CLI runs.
- Only enable plugin code execution if you trust the installed code path.
