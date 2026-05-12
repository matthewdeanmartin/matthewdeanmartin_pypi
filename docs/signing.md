# Signing and verification

`pypi-profile` uses [minisign](https://jedisct1.github.io/minisign/) to let a
profile owner prove they control external accounts — a GitHub profile, a
Mastodon bio, a personal website, and so on.

This page explains how the mechanism works, what it actually proves, and where
it can fail or be misunderstood.

---

## What problem this solves

Publishing a profile package to PyPI already proves one thing: the PyPI account
holder put that data there. A reader can check the PyPI release history and know
that whoever controls `pypi-profile-example` on PyPI is the author of the data.

The open question is cross-account linking. A profile can claim:

```toml
[[profiles]]
kind = "github"
url = "https://github.com/example"
```

But that claim is **self-asserted**. Anyone who publishes a `pypi-profile-*`
package can list any GitHub URL. There is nothing stopping a bad actor from
claiming someone else's account.

Signed proofs solve this. The idea is that the same person who controls the
PyPI account also places a short signed token on the external page. A reader
who fetches both can check that the signature was made with the key embedded in
the PyPI package, and therefore that the same entity controls both places.

---

## How minisign works

Minisign is a small, opinionated signing tool built on the Ed25519 algorithm.
Ed25519 is a modern elliptic-curve signature scheme. It has these relevant
properties:

- **Key generation produces two files.** A *secret key* (never shared) and a
  *public key* (safe to publish).
- **Signing is a one-way operation.** You feed data to the secret key and get
  back a signature blob. The secret key is never transmitted.
- **Verification needs only the public key.** Anyone with the public key and the
  original data can check whether the signature is genuine. No secret is
  involved in verification.
- **Signatures are unforgeable without the secret key.** If a signature verifies
  correctly against a public key, the data was signed by whoever holds the
  matching secret key.
- **There is no central authority.** Minisign does not use a certificate chain
  or a trusted third party. Trust is rooted entirely in whoever published the
  public key.

`py-minisign` is the Python library that provides these operations. It is an
optional dependency; the base `pypi-profile` package works without it, but the
`keygen`, `sign`, and `verify` commands require it.

---

## The signing flow, step by step

### 1. Generate a keypair

```bash
pypi-profile keygen
```

This writes two files under `~/.pypi_profile/`:

```
~/.pypi_profile/minisign.key   ← secret key, never share this
~/.pypi_profile/minisign.pub   ← public key, paste this into your TOML
```

The command prints the public key as a base64 string. Copy it into your profile:

```toml
[verification]
public_key = "RWQ..."
preferred_signature_backend = "minisign"
```

The public key is safe to publish anywhere. Treat the secret key like a
password: keep it private, back it up, never commit it to version control.

### 2. Sign a claim for an external URL

```bash
pypi-profile sign controls-url pypi_profile.toml \
    --url https://github.com/example
```

Internally, this builds a JSON claim document:

```json
{
  "profile_package": "pypi-profile-example",
  "pypi_username": "example",
  "claim": "controls-url",
  "subject": "https://github.com/example",
  "issued_at": "2026-05-10T12:00:00Z",
  "expires_at": "2027-05-10T12:00:00Z",
  "nonce": "550e8400-e29b-41d4-a716-446655440000",
  "key_id": "AABBCCDDEEFF0011",
  "signature_backend": "minisign"
}
```

That document is serialized to canonical JSON bytes, signed with the secret key,
and the resulting minisign signature blob is embedded as a `signature` field.
The whole thing is then base64url-encoded into a single-line token:

```text
pypi-profile-proof: eyJwcm9maWxlX3BhY2thZ2UiOiAi...
```

### 3. Paste the token onto the external page

Place the token somewhere on the page you are claiming. For example:

- In a GitHub profile README
- In a Mastodon post (see [Mastodon workflow](#mastodon-workflow) below)
- In a GitLab profile description
- In the text of a personal website
- In a project README on PyPI

The token is plain text and intentionally compact. It does not matter whether it
appears in a comment, a paragraph, a code block, or a metadata field, as long as
the raw text is accessible to an HTTP fetch.

### 4. Store proofs in the TOML for static builds

If you publish a static site (via `pypi-profile build`), the private key is not
available at build time. Run `update-proofs` locally after signing to store the
proof strings in the TOML:

```bash
pypi-profile update-proofs pypi_profile.toml
```

This signs every `[[profiles]]` entry that does not yet have a `stored_proof`
and writes the proof strings directly into the TOML file. Commit the result.
The static build reads `stored_proof` instead of calling the private key.

To re-sign everything (e.g. after key rotation):

```bash
pypi-profile update-proofs pypi_profile.toml --force
```

### 5. Verify

```bash
pypi-profile verify pypi_profile.toml
```

The verifier:

1. Reads `public_key` from `[verification]`.
2. For each `[[profiles]]` entry, fetches the URL.
3. Scans the page text for any line matching `pypi-profile-proof: <token>`.
4. Decodes each token it finds.
5. Checks that `subject`, `pypi_username`, and `profile_package` match what is
   in the profile.
6. Checks that `expires_at` has not passed.
7. Verifies the minisign signature against the embedded public key.

Results are reported as `verified`, `unverified`, `invalid`, or `expired`.

The same check runs live when a visitor loads `/verification` in the served site
and appears in `/api/verification.json`.

---

## What a verified claim actually proves

A `verified` result means:

> The entity that published `pypi-profile-example` to PyPI, under the PyPI
> account `example`, also placed a correctly signed token at
> `https://github.com/example` — signed with the private key whose public
> counterpart appears in that same PyPI package.

This is a meaningful proof of co-control. It is not a weak claim. Producing the
token requires both:

- write access to the external page, and
- possession of the secret key corresponding to the public key in the PyPI package.

Both conditions must be true simultaneously. Neither alone is sufficient.

---

## What a verified claim does NOT prove

This is the part that is easy to misread.

### It does not prove legal identity

The claim connects a PyPI account, a cryptographic key, and an external URL.
It says nothing about a legal name, a physical address, an employer, or any
government-issued identity document.

The profile data may contain a legal name, but that field is self-asserted.
`pypi-profile` has no way to verify it.

### It does not prove the content of the external page is accurate

The claim proves the profile owner controls `https://github.com/example`. It
does not prove that the GitHub bio, README, or repository list accurately
represents the person's skills, employment, or professional history.

### It does not prove the PyPI package maintainer list is controlled by one person

A PyPI project may have multiple maintainers. Publishing a profile package
proves one account published the data, not that the entire named project
belongs exclusively to that account.

### It does not prove the linked external account has not been compromised

If the GitHub account was later taken over by someone else, an old proof token
on that page could still verify correctly — because the token only proves that
the page *was* controlled by the keyholder when the token was placed, not that
it still is.

Expiry dates mitigate this: a proof with a one-year expiry stops verifying
automatically after that window. Shorter expiry windows reduce exposure at the
cost of requiring more frequent re-signing.

### It does not prove absence of malicious intent

Verification is a proof of technical co-control, not a character reference.
Someone who has verified every claim on their profile is not thereby more
trustworthy in a human or professional sense.

### It does not make self-asserted data verified

Fields like `work_experience`, `skills`, and `contact_methods` remain
self-asserted regardless of whether other claims are verified. The UI labels
them accordingly. Do not conflate "this profile has some verified claims" with
"everything in this profile is verified."

---

## The trust model in plain terms

Think of it as a **chain of co-control**, not a certificate authority hierarchy.

```
PyPI account (publishes pypi-profile-example)
   └─ embeds public key ABCD1234
        └─ secret key ABCD1234 signed the token at github.com/example
             └─ token is present at github.com/example
```

Breaking any link in that chain breaks the proof:

| Link | What breaks it |
|---|---|
| PyPI account | Someone publishes a profile package from a different PyPI account |
| Public key | The profile TOML contains a public key that does not match the signing key |
| Token | The external page does not contain a valid token for this profile |
| Expiry | The token's `expires_at` is in the past |
| Signature | The signature was produced with a different secret key |

---

## Mastodon workflow

Mastodon posts have a URL, but that URL is not known until after the post is
created. The recommended workflow is:

1. **Create a blank post** (or a placeholder post) on Mastodon.
2. **Copy the post URL** from the browser address bar, e.g.
   `https://fosstodon.org/@yourname/123456789`.
3. **Add it to your TOML:**

   ```toml
   [[profiles]]
   kind = "mastodon"
   label = "Mastodon"
   url = "https://fosstodon.org/@yourname/123456789"
   verification = "self_asserted"
   rel_me = true
   ```

4. **Sign it:**

   ```bash
   pypi-profile sign controls-url pypi_profile.toml \
       --url https://fosstodon.org/@yourname/123456789
   ```

5. **Edit the Mastodon post** to include the `pypi-profile-proof: ...` token
   that was printed. Mastodon allows editing posts.

6. **Store the proof in the TOML** so static builds work without the private key:

   ```bash
   pypi-profile update-proofs pypi_profile.toml
   ```

7. **Verify:**

   ```bash
   pypi-profile verify pypi_profile.toml
   ```

Note: The verifier fetches the post URL as plain HTML. Mastodon renders post
content in the server-side HTML, so the token will be found without requiring
JavaScript.

---

## `rel="me"` links

Mastodon and some other platforms use the HTML `rel="me"` attribute to establish
bidirectional identity links between accounts. When a Mastodon profile contains
`<a rel="me" href="https://example.com">`, and the linked page contains
`<a rel="me" href="https://mastodon.social/@you">`, Mastodon marks the link as
verified.

To opt a profile link into `rel="me"` output, set `rel_me = true`:

```toml
[[profiles]]
kind = "mastodon"
label = "Mastodon"
url = "https://fosstodon.org/@yourname/123456789"
rel_me = true

[[profiles]]
kind = "github"
label = "GitHub"
url = "https://github.com/yourname"
rel_me = true
```

The served and built pages will render the corresponding anchors as
`<a href="..." rel="me">`. This is independent of the minisign proof-of-control
mechanism — you can use `rel_me` with or without a `stored_proof`.

---

## What can go wrong

### Stale tokens

A proof token is valid until `expires_at`. If you change your public key (for
example, because the secret key was lost or compromised), old tokens signed with
the old key will no longer verify against the new public key. You must re-sign
all external claims with the new key and re-paste the new tokens.

The `key_id` field in the token records which key produced the signature, so
tooling can report "signed by an old key" rather than just "invalid."

### Key loss

If you lose the secret key, you cannot sign new claims. You will need to
generate a new keypair, update `public_key` in your TOML, republish the package,
and re-sign all external claims. There is no key recovery mechanism.

When `keyring` is installed and a usable backend is active (macOS Keychain,
Windows Credential Manager, libsecret on Linux), `pypi-profile keygen`
automatically stores the secret key there in addition to the disk file at
`~/.pypi_profile/minisign.key`. Subsequent `sign` and `update-proofs` commands
load the key from the keyring first and fall back to disk.

If you are not using a keyring backend, back up
`~/.pypi_profile/minisign.key` to an encrypted location (password manager,
encrypted archive). Never commit it to version control.

### Secret key exposure

If the secret key is exposed — for example committed to a public repository by
accident — any holder can sign claims on your behalf. Generate a new keypair
immediately, update the profile, and republish.

Old claims signed by the compromised key will continue to verify until they
expire or until you remove the old public key from the profile.

### URL content is fetched at verify time

The verifier fetches the external URL at the moment `verify` is run (or when a
visitor loads `/verification`). If the external page is slow, returns an error,
or requires JavaScript to render content, the fetch will fail and the result
will be `unverified` rather than `verified`.

Plain-text placement of the token is more reliable than token placement inside
JavaScript-rendered content.

### External pages that redirect

The verifier follows HTTP redirects. The `subject` URL in the claim must match
the *declared* URL in `[[profiles]]`, not the final redirect destination.
If your GitHub profile redirects, make sure the declared URL is what the verifier
will use for the match check.

### Token placed in a section of the page not returned by HTTP

Some profile services return rich HTML that contains visible bios only after a
JavaScript render. The verifier performs a plain HTTP GET, not a headless browser
fetch. If the token is only present in dynamically loaded content, it will not be
found.

For services like GitHub and Mastodon where the bio is in the raw HTML, this
works. For single-page apps that require JavaScript, it may not.

---

## Common misunderstandings

### "I have a verified badge, so readers should trust everything in my profile"

No. The verification badge on `/verification` means some external URLs were
confirmed as co-controlled with the PyPI account. It says nothing about
self-asserted fields like employment history, skills, or contact methods.

### "If the claim says `verified`, PyPI has endorsed this person"

No. `pypi-profile` is an independent tool. Verification is done by
`pypi-profile`'s own verifier. PyPI has not endorsed or reviewed the profile.

### "Other people can verify my profile"

Yes — that is the design. Anyone who runs `pypi-profile verify` against your
published profile package, or visits `/verification` on your served site, will
see the same live check. The mechanism is transparent and publicly auditable.

### "I need to keep the proof token secret"

No. The token is designed to be pasted publicly. It contains no secret
information. The signature embedded in it is produced by the secret key, but it
cannot be used to recover the secret key.

### "Putting the token in my GitHub README makes GitHub responsible for the claim"

No. GitHub is only a hosting medium. The claim proves that the token was placed
there by the holder of the private key; it does not involve GitHub in any
verification capacity.

---

## Security checklist

- [ ] Install `pypi-profile[sign]` so that `keyring` and `py-minisign` are available
- [ ] Generate your keypair once with `pypi-profile keygen`
- [ ] Confirm `pypi-profile doctor` shows a keyring backend and "Secret key found in keyring"
- [ ] If no keyring backend is available, back up `~/.pypi_profile/minisign.key` to an encrypted location
- [ ] Never commit the secret key file to version control
- [ ] Add the printed public key to `[verification]` in your TOML
- [ ] Republish your profile package so the public key is in the PyPI release
- [ ] Run `pypi-profile sign controls-url` for each external URL you want to claim
- [ ] Paste each proof token onto the corresponding external page
- [ ] Run `pypi-profile update-proofs` to store proofs in the TOML for static builds
- [ ] Commit the updated TOML (the stored proofs contain no secret material)
- [ ] Run `pypi-profile verify` to confirm the round-trip works
- [ ] Set a calendar reminder to re-sign before tokens expire (default: 1 year)
- [ ] If you ever rotate your key, run `pypi-profile update-proofs --force` to re-sign all claims

---

## Signing dependencies

`py-minisign` and `keyring` are core dependencies of `pypi-profile` — no extra
is required. A plain install includes both:

```bash
pipx install pypi-profile
```

Run `pypi-profile doctor` to confirm both are present and that a keyring backend
is active.

### Keyring backend availability

| Platform | Default backend |
|---|---|
| macOS | Keychain |
| Windows | Credential Manager |
| Linux (GNOME/KDE) | libsecret / KWallet via `SecretService` |
| Linux (headless CI) | No usable backend — disk fallback is used |

On headless Linux (e.g. GitHub Actions), no keyring backend is available. The
secret key will be loaded from disk only. Do not store the secret key in CI
environments; use `update-proofs` locally and commit the stored proofs instead.

### Overriding the keyring username

If you manage multiple profiles on the same machine, set
`PYPI_PROFILE_KEYRING_USERNAME` to a different value per profile:

```bash
PYPI_PROFILE_KEYRING_USERNAME=mycompany pypi-profile keygen
PYPI_PROFILE_KEYRING_USERNAME=mycompany pypi-profile update-proofs pypi_profile.toml
```
