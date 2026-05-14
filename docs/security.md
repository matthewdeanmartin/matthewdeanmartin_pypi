# Security

`pypi-profile` publishes public profile data and can also sign proof-of-control claims for external accounts.

The main security concerns are:

1. protecting the local signing key
2. understanding what signed verification does and does not prove
3. only enabling code execution when you trust the code being loaded

## Safe defaults

- `serve` does not execute extra code unless you pass `--allow-code`
- the GUI also keeps plugin code execution off by default unless you explicitly choose an `--allow-code` path
- HTTP fetches are limited to `http` and `https` URLs
- verification reads public pages live, so scraper-hostile or heavily JavaScript-driven pages may fail to verify

If you do not need code execution, keep `--allow-code` off.

## Protect the signing key

Generate a keypair with:

```bash
pypi-profile keygen
```

When a usable system keyring is available, `pypi-profile` stores the secret key there and also keeps a disk copy
under `~/.pypi_profile/`.

Treat the secret key like a password:

- never commit it to version control
- avoid copying it into CI or shared build machines
- back it up to an encrypted location if you rely on the disk copy
- use `--keyring-identity` or `PYPI_PROFILE_KEYRING_USERNAME` when managing multiple identities

If the key is lost or exposed:

1. generate a new keypair
2. update `[verification].public_key` in `pypi_profile.toml`
3. republish the profile package
4. re-sign stored proofs with `pypi-profile update-proofs --force`

## What verification proves

A verified proof means the same actor controlled:

- the PyPI-published profile package that contains the public key
- the private key that signed the proof token
- the external page where the proof token was posted

That is useful proof of **account co-control**.

## What verification does not prove

Verification does **not** prove:

- legal identity
- employment, biography, or skill claims
- that an external account has never been compromised
- that every field in the profile is independently verified

Treat signed claims as technical proof of control over a URL, not as a blanket endorsement of every statement in the
profile.

## Publishing checklist

Before publishing a signed profile:

- run `pypi-profile doctor`
- generate a keypair with `pypi-profile keygen`
- add the printed public key to `[verification]`
- sign each external URL with `pypi-profile sign controls-url ...`
- paste each proof token onto the corresponding external page
- store proof strings in the TOML with `pypi-profile update-proofs`
- verify the round-trip with `pypi-profile verify`
- keep `--allow-code` disabled unless you trust the code path you are enabling

## Reporting a vulnerability

Please report security issues privately rather than in a public issue.

- GitHub private advisories: <https://github.com/matthewdeanmartin/matthewdeanmartin_pypi/security/advisories/new>
- Email: <matthewdeanmartin@gmail.com>

If you are running third-party code-bearing packages with `--allow-code`, prefer a local virtual environment or a
containerized deployment so that plugin execution is isolated from unrelated credentials and files.
