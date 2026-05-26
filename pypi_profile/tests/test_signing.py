"""Tests for signing, claims, and verifier modules."""

from __future__ import annotations

import sys

import pytest

from pypi_profile.claims import (
    PROOF_PREFIX,
    build_claim,
    build_compact_claim,
    decode_claim,
    encode_claim,
    is_compact_claim,
    is_expired,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# --- claims.py tests --------------------------------------------------------


def test_build_claim_fields():
    claim = build_claim(
        profile_package="pypi-profile-test",
        pypi_username="test",
        claim_type="controls-url",
        subject_url="https://example.com",
        key_id="AABBCCDD",
    )
    assert claim["claim"] == "controls-url"
    assert claim["subject"] == "https://example.com"
    assert claim["pypi_username"] == "test"
    assert "nonce" in claim
    assert "issued_at" in claim
    assert "expires_at" in claim


def test_encode_decode_claim_roundtrip():
    claim = build_claim(
        profile_package="pypi-profile-test",
        pypi_username="test",
        claim_type="controls-url",
        subject_url="https://example.com",
        key_id="AABBCCDD",
    )
    claim["signature"] = "fakesig=="
    token = encode_claim(claim)
    assert token.startswith(PROOF_PREFIX)
    recovered = decode_claim(token)
    assert recovered["subject"] == "https://example.com"
    assert recovered["signature"] == "fakesig=="


def test_decode_claim_strips_prefix():
    claim = build_claim(
        profile_package="pkg",
        pypi_username="u",
        claim_type="controls-url",
        subject_url="https://x.com",
        key_id="00",
    )
    token = encode_claim(claim)
    bare_token = token[len(PROOF_PREFIX) :].strip()
    recovered = decode_claim(bare_token)
    assert recovered["subject"] == "https://x.com"


def test_is_expired_future():
    claim = {"expires_at": "2099-01-01T00:00:00Z"}
    assert not is_expired(claim)


def test_is_expired_past():
    claim = {"expires_at": "2000-01-01T00:00:00Z"}
    assert is_expired(claim)


def test_is_expired_missing():
    assert not is_expired({})


def test_build_compact_claim_fields():
    claim = build_compact_claim(
        profile_package="pypi-profile-test",
        pypi_username="test",
        subject_url="https://mastodon.social/@test",
    )
    assert claim["p"] == "pypi-profile-test"
    assert claim["u"] == "test"
    assert claim["s"] == "https://mastodon.social/@test"
    assert isinstance(claim["i"], int)
    assert isinstance(claim["e"], int)
    assert claim["e"] > claim["i"]
    assert "n" in claim
    assert is_compact_claim(claim)
    assert not is_compact_claim({"subject": "x"})


def test_compact_claim_encode_decode_roundtrip():
    claim = build_compact_claim(
        profile_package="pypi-profile-test",
        pypi_username="test",
        subject_url="https://mastodon.social/@test",
    )
    claim["g"] = "fakesig"
    token = encode_claim(claim)
    assert token.startswith(PROOF_PREFIX)
    recovered = decode_claim(token)
    assert recovered["s"] == "https://mastodon.social/@test"
    assert recovered["g"] == "fakesig"
    assert is_compact_claim(recovered)


def test_compact_claim_is_expired_unix():
    import time

    assert not is_expired({"p": "x", "s": "y", "e": int(time.time()) + 9999})
    assert is_expired({"p": "x", "s": "y", "e": int(time.time()) - 1})
    assert not is_expired({"p": "x", "s": "y"})


# --- signing.py + verifier.py integration tests (require py-minisign) -------

pytest.importorskip("minisign", reason="py-minisign not installed")


def test_generate_keypair_and_sign_verify(tmp_path):
    from pypi_profile.signing import generate_keypair, sign_controls_url
    from pypi_profile.verifier import verify_claim_signature

    sk_path, pk_path, pub_b64 = generate_keypair(
        key_dir=tmp_path, password="", force=True
    )
    assert sk_path.exists()
    assert pk_path.exists()
    assert pub_b64

    proof = sign_controls_url(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        sk_path=sk_path,
        password="",
    )
    assert proof.startswith(PROOF_PREFIX)

    claim = decode_claim(proof)
    assert claim["subject"] == "https://github.com/testuser"
    assert claim["claim"] == "controls-url"
    assert "signature" in claim

    assert verify_claim_signature(claim, pub_b64)


def test_compact_sign_verify_roundtrip(tmp_path):
    from pypi_profile.signing import generate_keypair, sign_controls_url
    from pypi_profile.verifier import verify_claim_signature

    sk_path, _pk_path, pub_b64 = generate_keypair(
        key_dir=tmp_path, password="", force=True
    )

    proof = sign_controls_url(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://mastodon.social/@testuser",
        sk_path=sk_path,
        password="",
        compact=True,
    )
    assert proof.startswith(PROOF_PREFIX)
    assert len(proof) < 500

    claim = decode_claim(proof)
    assert is_compact_claim(claim)
    assert claim["s"] == "https://mastodon.social/@testuser"
    assert claim["p"] == "pypi-profile-test"
    assert "g" in claim
    assert "signature" not in claim

    assert verify_claim_signature(claim, pub_b64)


def test_compact_sign_verify_wrong_key(tmp_path):
    from pypi_profile.signing import generate_keypair, sign_controls_url
    from pypi_profile.verifier import verify_claim_signature

    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, password="", force=True)
    _sk2, _pk2, pub_b64_other = generate_keypair(
        key_dir=tmp_path / "other", password="", force=True
    )

    proof = sign_controls_url(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://mastodon.social/@testuser",
        sk_path=sk_path,
        compact=True,
    )
    claim = decode_claim(proof)
    assert not verify_claim_signature(claim, pub_b64_other)


def test_compact_status_from_tokens(tmp_path):
    from pypi_profile.signing import generate_keypair, sign_controls_url
    from pypi_profile.verifier import status_from_tokens

    sk_path, _pk, pub_b64 = generate_keypair(key_dir=tmp_path, password="", force=True)

    proof = sign_controls_url(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://mastodon.social/@testuser",
        sk_path=sk_path,
        compact=True,
    )

    status = status_from_tokens(
        [proof],
        subject_url="https://mastodon.social/@testuser",
        pypi_username="testuser",
        profile_package="pypi-profile-test",
        public_key_b64=pub_b64,
    )
    assert status == "verified"


def test_verify_claim_signature_wrong_key(tmp_path):
    from pypi_profile.signing import generate_keypair, sign_controls_url
    from pypi_profile.verifier import verify_claim_signature

    sk_path, _pk_path, _pub_b64 = generate_keypair(
        key_dir=tmp_path, password="", force=True
    )
    _sk2, _pk2, pub_b64_other = generate_keypair(
        key_dir=tmp_path / "other", password="", force=True
    )

    proof = sign_controls_url(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        sk_path=sk_path,
        password="",
    )
    claim = decode_claim(proof)
    assert not verify_claim_signature(claim, pub_b64_other)


def test_find_proof_tokens():
    from pypi_profile.verifier import find_proof_tokens

    text = """
    Some page content.
    pypi-profile-proof: abc123XYZ==
    More content.
    """
    tokens = find_proof_tokens(text)
    assert len(tokens) == 1
    assert "abc123XYZ" in tokens[0]


def test_find_proof_tokens_none():
    from pypi_profile.verifier import find_proof_tokens

    assert find_proof_tokens("no tokens here") == []


def test_fetch_page_rejects_non_http_scheme():
    from pypi_profile.verifier import fetch_page

    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        fetch_page("file:///tmp/proof.txt")


# --- patch_proofs_in_toml tests ---------------------------------------------

MINIMAL_TOML = """\
[profile]
kind = "individual"
display_name = "Test User"

[identity]
pypi_username = "testuser"

[[profiles]]
kind = "github"
label = "GitHub"
url = "https://github.com/testuser"
verification = "self_asserted"

[verification]
public_key = ""
preferred_signature_backend = "minisign"
"""


def test_patch_proofs_success(tmp_path):
    """Happy path: proof is inserted and the file remains valid TOML."""
    from pypi_profile.signing import generate_keypair, patch_proofs_in_toml

    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text(MINIMAL_TOML, encoding="utf-8")

    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, force=True)

    updated = patch_proofs_in_toml(
        toml_path=toml_path,
        profile_package="pypi-profile-testuser",
        pypi_username="testuser",
        sk_path=sk_path,
    )

    assert updated == ["https://github.com/testuser"]

    # File must still parse as valid TOML with stored_proof present.
    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)

    profiles = data["profiles"]
    assert len(profiles) == 1
    assert profiles[0]["stored_proof"].startswith("pypi-profile-proof:")


def test_patch_proofs_rollback_on_corrupt(tmp_path, mocker):
    """If the regex produces invalid TOML, the original file is restored."""
    from pypi_profile.signing import generate_keypair, patch_proofs_in_toml

    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text(MINIMAL_TOML, encoding="utf-8")

    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, force=True)

    # Corrupt the output by injecting a broken proof line.
    original_subn = __import__("re").subn

    def corrupt_subn(pattern, repl, string, **kwargs):
        result, n = original_subn(pattern, repl, string, **kwargs)
        if n:
            # Inject a bare equals sign that makes TOML invalid.
            result = result.replace('stored_proof = "', 'stored_proof = \n"')
        return result, n

    mocker.patch("pypi_profile.signing.re.subn", side_effect=corrupt_subn)

    with pytest.raises(ValueError, match="invalid TOML"):
        patch_proofs_in_toml(
            toml_path=toml_path,
            profile_package="pypi-profile-testuser",
            pypi_username="testuser",
            sk_path=sk_path,
        )

    # File must be identical to the original — rolled back.
    assert toml_path.read_text(encoding="utf-8") == MINIMAL_TOML


def test_patch_proofs_skips_existing(tmp_path):
    """Entries with an existing stored_proof are skipped unless force=True."""
    from pypi_profile.signing import generate_keypair, patch_proofs_in_toml

    toml_with_proof = MINIMAL_TOML + 'stored_proof = "pypi-profile-proof: existing"\n'
    # Rebuild with stored_proof inside the [[profiles]] block.
    toml_with_proof = MINIMAL_TOML.replace(
        'verification = "self_asserted"\n',
        'verification = "self_asserted"\nstored_proof = "pypi-profile-proof: existing"\n',
    )

    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text(toml_with_proof, encoding="utf-8")
    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, force=True)

    updated = patch_proofs_in_toml(
        toml_path=toml_path,
        profile_package="pypi-profile-testuser",
        pypi_username="testuser",
        sk_path=sk_path,
        force=False,
    )

    assert updated == []
    # File unchanged.
    assert toml_path.read_text(encoding="utf-8") == toml_with_proof


def test_patch_proofs_force_overwrites(tmp_path):
    """force=True re-signs even when stored_proof already exists."""
    from pypi_profile.signing import generate_keypair, patch_proofs_in_toml

    toml_with_proof = MINIMAL_TOML.replace(
        'verification = "self_asserted"\n',
        'verification = "self_asserted"\nstored_proof = "pypi-profile-proof: old"\n',
    )

    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text(toml_with_proof, encoding="utf-8")
    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, force=True)

    updated = patch_proofs_in_toml(
        toml_path=toml_path,
        profile_package="pypi-profile-testuser",
        pypi_username="testuser",
        sk_path=sk_path,
        force=True,
    )

    assert updated == ["https://github.com/testuser"]

    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)

    new_proof = data["profiles"][0]["stored_proof"]
    assert new_proof.startswith("pypi-profile-proof:")
    assert new_proof != "pypi-profile-proof: old"


MULTI_PROFILE_TOML = """\
[profile]
kind = "individual"
display_name = "Test User"

[identity]
pypi_username = "testuser"

[[profiles]]
kind = "github"
label = "GitHub"
url = "https://github.com/testuser"
verification = "self_asserted"

[[profiles]]
kind = "mastodon"
label = "Mastodon"
url = "https://mastodon.social/@testuser/99999"
verification = "self_asserted"

[verification]
public_key = ""
preferred_signature_backend = "minisign"
"""


def test_patch_proofs_distinct_per_url(tmp_path):
    """Each [[profiles]] entry must receive a proof for its own URL, not another entry's."""
    from pypi_profile.signing import generate_keypair, patch_proofs_in_toml

    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text(MULTI_PROFILE_TOML, encoding="utf-8")
    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, force=True)

    updated = patch_proofs_in_toml(
        toml_path=toml_path,
        profile_package="pypi-profile-testuser",
        pypi_username="testuser",
        sk_path=sk_path,
    )

    assert set(updated) == {
        "https://github.com/testuser",
        "https://mastodon.social/@testuser/99999",
    }

    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)

    proofs = {p["url"]: p["stored_proof"] for p in data["profiles"]}

    # Proofs must be different (different subjects)
    assert (
        proofs["https://github.com/testuser"]
        != proofs["https://mastodon.social/@testuser/99999"]
    ), "Both profiles received the same stored_proof — subject was not applied per URL"

    # Each proof must encode the correct subject URL
    github_claim = decode_claim(proofs["https://github.com/testuser"])
    subject_key = "s" if is_compact_claim(github_claim) else "subject"
    assert github_claim[subject_key] == "https://github.com/testuser"

    mastodon_claim = decode_claim(proofs["https://mastodon.social/@testuser/99999"])
    subject_key = "s" if is_compact_claim(mastodon_claim) else "subject"
    assert mastodon_claim[subject_key] == "https://mastodon.social/@testuser/99999"


def test_patch_proofs_duplicate_detection(tmp_path, mocker):
    """patch_proofs_in_toml raises ValueError and rolls back if two entries get the same proof."""
    from pypi_profile.signing import generate_keypair, patch_proofs_in_toml

    toml_path = tmp_path / "pypi_profile.toml"
    toml_path.write_text(MULTI_PROFILE_TOML, encoding="utf-8")
    original = toml_path.read_text(encoding="utf-8")
    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, force=True)

    # Force sign_controls_url to return the same proof for every call
    mocker.patch(
        "pypi_profile.signing.sign_controls_url",
        return_value="pypi-profile-proof: SAMEPROOF",
    )

    with pytest.raises(ValueError, match="duplicate stored_proof"):
        patch_proofs_in_toml(
            toml_path=toml_path,
            profile_package="pypi-profile-testuser",
            pypi_username="testuser",
            sk_path=sk_path,
        )

    # File must be rolled back to original
    assert toml_path.read_text(encoding="utf-8") == original


# --- tiny + fingerprint format tests ----------------------------------------


def test_tiny_token_length_budget():
    from pypi_profile.claims import encode_tiny_token

    sig = b"\x00" * 64
    tok = encode_tiny_token(sig)
    assert tok.startswith("t:")
    # Ed25519 sig = 86 b64url chars + "t:" prefix = 88 chars total.
    assert len(tok) == 88


def test_tiny_token_roundtrip_and_rejects_wrong_size():
    from pypi_profile.claims import decode_tiny_token, encode_tiny_token

    sig = bytes(range(64))
    tok = encode_tiny_token(sig)
    assert decode_tiny_token(tok) == sig
    with pytest.raises(ValueError):
        encode_tiny_token(b"\x00" * 63)
    with pytest.raises(ValueError):
        decode_tiny_token("not-a-tiny-token")


def test_fingerprint_length_and_parse():
    from pypi_profile.claims import fingerprint_of_full_proof, parse_fingerprint

    fp = fingerprint_of_full_proof("pypi-profile-proof: ABC", "1234567890abcdef")
    assert fp.startswith("f:")
    assert len(fp) == 35
    keyid, h = parse_fingerprint(fp)
    assert keyid == "1234567890abcdef"
    assert len(h) == 16


def test_fingerprint_rejects_short_keyid():
    from pypi_profile.claims import fingerprint_of_full_proof

    with pytest.raises(ValueError):
        fingerprint_of_full_proof("token", "abc")


def test_tiny_sign_verify_roundtrip(tmp_path):
    from pypi_profile.signing import generate_keypair, sign_controls_url
    from pypi_profile.verifier import verify_tiny_token

    sk_path, _pk, pub_b64 = generate_keypair(key_dir=tmp_path, password="", force=True)
    tok = sign_controls_url(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        sk_path=sk_path,
        format="tiny",
    )
    assert tok.startswith("t:")
    assert len(tok) == 88
    status = verify_tiny_token(
        tok,
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        public_key_b64=pub_b64,
    )
    assert status == "verified"


def test_tiny_sign_verify_rejects_wrong_subject(tmp_path):
    from pypi_profile.signing import generate_keypair, sign_controls_url
    from pypi_profile.verifier import verify_tiny_token

    sk_path, _pk, pub_b64 = generate_keypair(key_dir=tmp_path, password="", force=True)
    tok = sign_controls_url(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        sk_path=sk_path,
        format="tiny",
    )
    bad = verify_tiny_token(
        tok,
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/somebody-else",
        public_key_b64=pub_b64,
    )
    assert bad == "invalid"


def test_tiny_sign_verify_rejects_wrong_key(tmp_path):
    from pypi_profile.signing import generate_keypair, sign_controls_url
    from pypi_profile.verifier import verify_tiny_token

    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, password="", force=True)
    _sk2, _pk2, pub_b64_other = generate_keypair(
        key_dir=tmp_path / "other", password="", force=True
    )
    tok = sign_controls_url(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        sk_path=sk_path,
        format="tiny",
    )
    assert (
        verify_tiny_token(
            tok,
            profile_package="pypi-profile-test",
            pypi_username="testuser",
            subject_url="https://github.com/testuser",
            public_key_b64=pub_b64_other,
        )
        == "invalid"
    )


def test_tiny_accepts_prior_year(tmp_path):
    """A token signed last year is still accepted within the rolling window."""
    from datetime import datetime, timezone

    from pypi_profile.claims import encode_tiny_token, tiny_message_bytes
    from pypi_profile.signing import generate_keypair, load_secret_key
    from pypi_profile.verifier import TINY_ACCEPTED_YEARS_BACK, verify_tiny_token

    sk_path, _pk, pub_b64 = generate_keypair(key_dir=tmp_path, password="", force=True)
    sk = load_secret_key(sk_path, password="")

    now = datetime.now(tz=timezone.utc)
    past_year = now.year - TINY_ACCEPTED_YEARS_BACK
    msg = tiny_message_bytes(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        year=past_year,
    )
    sig = sk.sign(msg, prehash=True)
    tok = encode_tiny_token(sig._signature)

    assert (
        verify_tiny_token(
            tok,
            profile_package="pypi-profile-test",
            pypi_username="testuser",
            subject_url="https://github.com/testuser",
            public_key_b64=pub_b64,
        )
        == "verified"
    )


def test_tiny_rejects_token_older_than_window(tmp_path):
    from datetime import datetime, timezone

    from pypi_profile.claims import encode_tiny_token, tiny_message_bytes
    from pypi_profile.signing import generate_keypair, load_secret_key
    from pypi_profile.verifier import TINY_ACCEPTED_YEARS_BACK, verify_tiny_token

    sk_path, _pk, pub_b64 = generate_keypair(key_dir=tmp_path, password="", force=True)
    sk = load_secret_key(sk_path, password="")

    too_old_year = datetime.now(tz=timezone.utc).year - (TINY_ACCEPTED_YEARS_BACK + 1)
    msg = tiny_message_bytes(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        year=too_old_year,
    )
    sig = sk.sign(msg, prehash=True)
    tok = encode_tiny_token(sig._signature)

    assert (
        verify_tiny_token(
            tok,
            profile_package="pypi-profile-test",
            pypi_username="testuser",
            subject_url="https://github.com/testuser",
            public_key_b64=pub_b64,
        )
        == "invalid"
    )


def test_fingerprint_resolver_match(tmp_path):
    from pypi_profile.signing import (
        generate_keypair,
        load_secret_key,
        sign_controls_url,
    )
    from pypi_profile.verifier import verify_fingerprint_token

    sk_path, _pk, pub_b64 = generate_keypair(key_dir=tmp_path, password="", force=True)

    full = sign_controls_url(
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        sk_path=sk_path,
        format="full",
    )

    sk = load_secret_key(sk_path, password="")
    from pypi_profile.claims import fingerprint_of_full_proof

    keyid_hex = bytes(sk._keynum_sk.key_id).hex()
    fp = fingerprint_of_full_proof(full, keyid_hex)
    assert len(fp) == 35

    status = verify_fingerprint_token(
        fp,
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://github.com/testuser",
        public_key_b64=pub_b64,
        resolver=lambda: [full],
    )
    assert status == "verified"


def test_fingerprint_resolver_no_match():
    """A fingerprint pointing at a full proof the resolver can't find stays unverified."""
    from pypi_profile.verifier import verify_fingerprint_token

    fp = "f:0123456789abcdef:fedcba9876543210"
    status = verify_fingerprint_token(
        fp,
        profile_package="pypi-profile-test",
        pypi_username="testuser",
        subject_url="https://example.com",
        public_key_b64="",
        resolver=lambda: ["pypi-profile-proof: somethingelse"],
    )
    assert status == "unverified"


def test_fingerprint_without_resolver_unverified():
    from pypi_profile.verifier import verify_fingerprint_token

    fp = "f:0123456789abcdef:fedcba9876543210"
    status = verify_fingerprint_token(
        fp,
        profile_package="x",
        pypi_username="y",
        subject_url="https://z",
        public_key_b64="",
        resolver=None,
    )
    assert status == "unverified"


def test_find_proof_tokens_picks_up_all_three_formats(tmp_path):
    from pypi_profile.signing import (
        generate_keypair,
        load_secret_key,
        sign_controls_url,
    )
    from pypi_profile.verifier import find_proof_tokens

    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, password="", force=True)

    full = sign_controls_url(
        profile_package="p",
        pypi_username="u",
        subject_url="https://example.com",
        sk_path=sk_path,
        format="full",
    )
    tiny = sign_controls_url(
        profile_package="p",
        pypi_username="u",
        subject_url="https://example.com",
        sk_path=sk_path,
        format="tiny",
    )
    sk = load_secret_key(sk_path, password="")
    from pypi_profile.claims import fingerprint_of_full_proof

    fp = fingerprint_of_full_proof(full, bytes(sk._keynum_sk.key_id).hex())

    page = f"bio: {full}\nposted: {tiny}\nptr: {fp}\n"
    found = find_proof_tokens(page)
    assert len(found) == 3
    # Verify the prefixes are preserved so downstream dispatch works.
    assert any(t.startswith("pypi-profile-proof:") for t in found)
    assert any(t.startswith("t:") for t in found)
    assert any(t.startswith("f:") for t in found)


def test_sign_controls_url_rejects_invalid_format(tmp_path):
    from pypi_profile.signing import generate_keypair, sign_controls_url

    sk_path, _pk, _pub = generate_keypair(key_dir=tmp_path, password="", force=True)
    with pytest.raises(ValueError):
        sign_controls_url(
            profile_package="p",
            pypi_username="u",
            subject_url="https://x",
            sk_path=sk_path,
            format="oversized",
        )


def test_compact_alias_still_works(tmp_path):
    """compact=True remains equivalent to format='compact' for backwards compat."""
    from pypi_profile.signing import generate_keypair, sign_controls_url
    from pypi_profile.verifier import verify_claim_signature

    sk_path, _pk, pub_b64 = generate_keypair(key_dir=tmp_path, password="", force=True)
    legacy = sign_controls_url(
        profile_package="p",
        pypi_username="u",
        subject_url="https://x",
        sk_path=sk_path,
        compact=True,
    )
    explicit = sign_controls_url(
        profile_package="p",
        pypi_username="u",
        subject_url="https://x",
        sk_path=sk_path,
        format="compact",
    )
    # Both should be compact format, both should verify.
    for tok in (legacy, explicit):
        claim = decode_claim(tok)
        assert is_compact_claim(claim)
        assert verify_claim_signature(claim, pub_b64)
