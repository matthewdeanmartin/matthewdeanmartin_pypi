# matthewdeanmartin

The profile page PyPI won't let you make.

PyPI author pages are anemic -- no bio, no trust signals, no `rel=me`, no way to tell if you
should trust a maintainer. This package fills that gap. Install it, run it, and get a real
profile with linked accounts, contact policy, continuity plan, and trust signals.

If this package is old and has never been flagged as malicious, that is itself a trust signal.

## Install

```bash
pip install matthewdeanmartin
```

## Usage

```bash
# Formatted text (default)
matthewdeanmartin

# Markdown output
matthewdeanmartin --markdown

# Machine-readable JSON
matthewdeanmartin --json

# Or with --format
matthewdeanmartin --format text
matthewdeanmartin --format markdown
matthewdeanmartin --format json

# Version
matthewdeanmartin --version
```

## Sample Output

### Text (default)

```
===================
Matthew Dean Martin
===================
  Open-source Python developer. Author of 50+ packages on PyPI. Professional software engineer.

=============
Trust Signals
=============
  Pypi Account Created: 2019
  Github Account Created: 2015
  Packages Published: 50+
  Consistent Identity: Same username across GitHub, PyPI, LinkedIn, StackOverflow
  Open Source Contributions: Active contributor and maintainer since 2019

===============
Linked Accounts
===============
           github: https://github.com/matthewdeanmartin [rel=me verified]
             pypi: https://pypi.org/user/matthewdeanmartin/
         linkedin: https://www.linkedin.com/in/matthewdeanmartin/
    stackoverflow: https://stackoverflow.com/users/33264/matthewmartin

==============
Contact Policy
==============
  Bug Reports: Yes
    -> webform: https://github.com/matthewdeanmartin/matthewdeanmartin_pypi/issues
  Job Offers: No
  Maintainer Apply: Yes
    -> Open an issue on the relevant repo
  Security Contact: matthewdeanmartin@gmail.com (email)
  Maintenance Status: active
  Support Policy: best-effort
  Collects Telemetry: No

=====================
Funding / Sponsorship
=====================
  github: matthewdeanmartin

===============
Continuity Plan
===============
  Inactivity Threshold: 365 days
  Handoff Policy: consent-required
  Notes: If I am inactive for over a year, packages may be transferred to willing maintainers on a per-repo basis.

==================
Package Trust Info
==================
  This package is published on PyPI. Its age and history are
  independently verifiable at:
    https://pypi.org/project/matthewdeanmartin/
  An old, unflagged package is itself a trust signal.
```

### Markdown (`--markdown`)

When rendered, the markdown output produces tables and links suitable for pasting into
GitHub issues, READMEs, or any markdown-capable viewer:

---

# Matthew Dean Martin

Open-source Python developer. Author of 50+ packages on PyPI. Professional software engineer.

## Trust Signals

| Signal                    | Value                                                      |
|---------------------------|------------------------------------------------------------|
| Pypi Account Created      | 2019                                                       |
| Github Account Created    | 2015                                                       |
| Packages Published        | 50+                                                        |
| Consistent Identity       | Same username across GitHub, PyPI, LinkedIn, StackOverflow |
| Open Source Contributions | Active contributor and maintainer since 2019               |

## Linked Accounts

| Platform      | Link                                                                              | Verified |
|---------------|-----------------------------------------------------------------------------------|----------|
| github        | [Primary GitHub account, active since 2015](https://github.com/matthewdeanmartin) | rel=me   |
| pypi          | [PyPI profile](https://pypi.org/user/matthewdeanmartin/)                          |          |
| linkedin      | [Professional profile](https://www.linkedin.com/in/matthewdeanmartin/)            |          |
| stackoverflow | [StackOverflow profile](https://stackoverflow.com/users/33264/matthewmartin)      |          |

---

## Prior Art

- [john-resume](https://pypi.org/project/john-resume/) -- a resume as a pip package

## What This Is Not

This is not a security tool. It does not verify identities cryptographically (yet).
It is a social trust artifact: a persistent, independently verifiable statement of
"here is who I am across the internet."

## License

MIT
