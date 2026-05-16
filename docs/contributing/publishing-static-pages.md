# Publishing a profile package with a static site

This page walks through setting up your own profile package — a Python package that contains your
`pypi_profile.toml` and can be published to PyPI — and then automatically deploying the generated
static site to GitHub Pages on every push.

## What you are building

By the end of this guide you will have:

- A Python package (e.g. `your-name`) on PyPI that contains your profile data.
- A GitHub Pages site at `https://yourusername.github.io/your-repo/` that is rebuilt automatically
  every time you push a change.
- Proof-of-control tokens pre-signed and stored in the TOML so the static build works without a
  private key.

## Step 1 — Create the package structure

Create a directory for your profile package:

```
your-name/
├── pyproject.toml
├── README.md
├── LICENSE
├── resume.json          ← optional, from jsonresume.org
└── your_name/
    ├── __init__.py
    ├── __about__.py
    ├── py.typed
    └── pypi_profile.toml
```

The importable Python package (`your_name/`) must have a valid Python identifier name (underscores
not hyphens). The published package name on PyPI (`your-name`) can use hyphens.

### `your_name/__about__.py`

```python
__version__ = "0.1.0"
```

### `your_name/__init__.py`

```python
from pypi_profile.plugin_spec import hookimpl
from your_name.__about__ import __version__

__all__ = ["__version__"]

@hookimpl
def get_profile_data() -> dict:  # type: ignore[type-arg]
    """Return profile data contributed by this package."""
    return {
        "author": "Your Name",
        "pypi_username": "your-pypi-username",
    }
```

The `@hookimpl` decorator registers this function as a plugin hook implementation. When
`pypi-profile serve` starts in hub mode, it calls `get_profile_data()` on every registered
plugin.

### `your_name/py.typed`

Create this as an empty file. It tells type checkers (mypy, pyright) that your package has type
annotations and they should use them.

```bash
touch your_name/py.typed
```

### `your_name/pypi_profile.toml`

This is the main profile data file. Generate a starter with:

```bash
pip install pypi-profile
pypi-profile init --username your-pypi-username --fetch --output your_name/pypi_profile.toml
```

Or write it by hand. Here is a minimal example:

```toml
[profile]
kind = "individual"
display_name = "Your Name"
summary = "Python developer and open-source contributor."

[identity]
legal_name = "Your Full Name"
display_name = "Your Name"
pypi_username = "your-pypi-username"
timezone = "UTC"
location = "City, Country"

[[profiles]]
kind = "github"
label = "GitHub"
url = "https://github.com/your-github-username"
verification = "self_asserted"
rel_me = true
stored_proof = ""

[[packages]]
name = "your-package"
role = "maintainer"
state = "active"
summary = "What it does."
url = "https://pypi.org/project/your-package/"

[verification]
public_key = ""
preferred_signature_backend = "minisign"
```

## Step 2 — Configure `pyproject.toml`

```toml
[project]
name = "your-name"
version = "0.1.0"
description = "PyPI profile for Your Name"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [{ name = "Your Name", email = "you@example.com" }]
keywords = ["pypi", "profile"]
dependencies = ["pypi-profile>=0.2.0"]

[project.urls]
Homepage = "https://yourusername.github.io/your-repo/"
Repository = "https://github.com/yourusername/your-repo"

[project.scripts]
your-name-profile = "pypi_profile.cli:main"

[project.entry-points."pypi_profile.plugins"]
your_name = "your_name"

[build-system]
requires = ["hatchling>=1.27.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["your_name"]
include = [
    "your_name/**/*.py",
    "your_name/py.typed",
    "your_name/pypi_profile.toml",
    "/README.md",
    "LICENSE",
]

[tool.hatch.build.targets.sdist]
include = ["/README.md", "LICENSE", "/your_name"]
```

Three things to pay attention to:

1. **`[project.entry-points."pypi_profile.plugins"]`**: This registers your package as a plugin.
   When someone installs your package and runs `pypi-profile serve`, your profile appears in the
   hub automatically.

2. **`[tool.hatch.build.targets.wheel] include`**: The `pypi_profile.toml` must be explicitly
   listed here. Hatchling does not automatically include data files unless you tell it to.

3. **`[project.scripts]`**: The optional CLI alias means `pip install your-name` also gives the
   user a `your-name-profile` command that runs the same CLI as `pypi-profile`.

## Step 3 — Sign your external accounts

First, generate a signing key:

```bash
pypi-profile keygen
```

This writes `~/.pypi_profile/minisign.key` (the secret key — keep this private) and
`~/.pypi_profile/minisign.pub` (the public key — safe to publish). It also auto-patches
`public_key` into your TOML if `pypi_profile.toml` is in the current directory.

Next, sign each external account you listed in `[[profiles]]`:

```bash
pypi-profile sign controls-url your_name/pypi_profile.toml --url https://github.com/your-github-username
```

This prints a proof token. Paste it somewhere on your GitHub profile page (bio, README, or a
pinned comment). GitHub renders this as plain text in its HTML, so the verifier can find it.

Now store the proof in the TOML so the static build works without the private key:

```bash
pypi-profile update-proofs your_name/pypi_profile.toml
```

This signs every `[[profiles]]` entry and writes the proof token into the `stored_proof` field.
Commit the updated TOML — the proof tokens contain no secret material and are safe to publish.

Verify everything worked:

```bash
pypi-profile verify your_name/pypi_profile.toml
```

## Step 4 — Test the site locally

```bash
pip install -e .
pypi-profile serve your_name/pypi_profile.toml
```

Open `http://127.0.0.1:8000` and check each page. Then build the static output:

```bash
pypi-profile build your_name/pypi_profile.toml --output dist --base-url /your-repo
```

`--base-url /your-repo` is needed because GitHub Pages serves project sites at a subpath, not at
the root. Replace `/your-repo` with the name of your GitHub repository.

Open `dist/index.html` in a browser to confirm the layout looks correct.

## Step 5 — Set up GitHub Pages

In your repository settings:

1. Go to **Settings → Pages**.
2. Under **Source**, select **GitHub Actions**.
3. Leave everything else at the defaults.

GitHub Pages with source "GitHub Actions" does not need a `gh-pages` branch or a special
configuration file. The workflow uploads the `dist/` directory as an artifact and deploys it
directly.

## Step 6 — Add the GitHub Actions workflows

Create `.github/workflows/` if it does not exist, then add two files.

### `.github/workflows/build.yml` — CI on every push

This runs on every push and pull request to verify the package builds and the site renders:

```yaml
---
name: Build

on:
  push:
    paths:
      - ".github/workflows/build.yml"
      - "your_name/**"
      - "pyproject.toml"
  pull_request:
    paths:
      - ".github/workflows/build.yml"
      - "your_name/**"
      - "pyproject.toml"

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install pypi-profile .

      - name: Validate profile
        run: pypi-profile inspect your_name/pypi_profile.toml

      - name: Build static site
        run: |
          pypi-profile build your_name/pypi_profile.toml \
            --output dist \
            --base-url /your-repo

      - name: Build wheel
        run: pip install hatch && hatch build
```

### `.github/workflows/pages.yml` — deploy to GitHub Pages on push to main

```yaml
---
name: Deploy to GitHub Pages

on:
  push:
    branches:
      - main
    paths:
      - ".github/workflows/pages.yml"
      - "your_name/**"
      - "pyproject.toml"
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install pypi-profile .

      - name: Build static site
        run: |
          pypi-profile build your_name/pypi_profile.toml \
            --output dist \
            --resume-file resume.json \
            --base-url /your-repo

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

The `pages: write` and `id-token: write` permissions are required by `deploy-pages`. The
`persist-credentials: false` on the checkout action is a security best practice that prevents the
job from accidentally pushing to the repository.

## Step 7 — Publish to PyPI

The static site does not require the package to be on PyPI, but publishing it lets other people
install your profile with `pip install your-name` and see it in the hub when they run
`pypi-profile serve`.

First, set up Trusted Publishing on PyPI:

1. Log in to PyPI.
2. Go to your account settings and then **Publishing**.
3. Add a new trusted publisher: provider GitHub Actions, repository
   `yourusername/your-repo`, workflow `publish.yml`, environment name `pypi`.

Trusted Publishing uses OIDC (a token exchange protocol) so you never need to store a PyPI API key
as a secret in GitHub. The `id-token: write` permission in the workflow allows this.

Then create `.github/workflows/publish.yml`:

```yaml
---
name: Publish to PyPI

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install hatch
        run: pip install hatch

      - name: Build distribution
        run: hatch build

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          if-no-files-found: error
          retention-days: 1

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/project/your-name/
    permissions:
      id-token: write
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

This workflow is triggered manually (`workflow_dispatch`). When you are ready to release a new
version:

1. Update the `version` in `pyproject.toml` and in `your_name/__about__.py`.
2. Commit and push to `main`.
3. Go to the Actions tab, select "Publish to PyPI", and click "Run workflow".

## What happens on a push

After setting up both workflows:

1. You edit `your_name/pypi_profile.toml` (e.g. add a new package or update your availability).
2. You commit and push to `main`.
3. The `pages.yml` workflow runs automatically:
   - Installs `pypi-profile` and your package.
   - Runs `pypi-profile build` which renders every page and JSON endpoint.
   - Uploads the `dist/` directory as a GitHub Pages artifact.
   - Deploys it to `https://yourusername.github.io/your-repo/`.
4. Within a minute or two, the live site reflects your change.

## Including `resume.json`

If you have a `resume.json` in [JSON Resume format](https://jsonresume.org/schema/), place it at
the root of your repository or next to `pypi_profile.toml`. The build command automatically copies
it to `dist/api/resume.json` and the resume page in the profile site links to it.

In the workflow, add `--resume-file resume.json` to the `pypi-profile build` command (see the
`pages.yml` example above).

## Troubleshooting

**The static site shows "unverified" instead of "verified" for my GitHub account.**

The static build uses `stored_proof` from the TOML. If `stored_proof` is empty for an entry,
re-run `pypi-profile update-proofs your_name/pypi_profile.toml` locally and commit the result.

**The build fails with `ModuleNotFoundError: No module named 'your_name'`.**

The `pip install .` step in the workflow installs your package in the current environment. If the
step is missing or the package name in `pyproject.toml` does not match the directory name, the
import fails. Check that `name = "your-name"` in `pyproject.toml` corresponds to the directory
`your_name/`.

**The pages deploy succeeds but the site shows broken asset links.**

The `--base-url` must match your GitHub Pages path. For a repository at
`github.com/yourusername/your-repo`, the Pages URL is `https://yourusername.github.io/your-repo/`
and the correct flag is `--base-url /your-repo`. For a user/org site
(`yourusername.github.io`), omit `--base-url` or set it to `/`.

**I want to pin the action SHAs for supply-chain safety.**

Replace `@v4`, `@v5`, etc. with the full commit SHA of the action. Tools like
[`zizmor`](https://github.com/woodruffw/zizmor) or `actionlint` can audit your workflows.
The workflows in this repository pin all action SHAs as an example.
