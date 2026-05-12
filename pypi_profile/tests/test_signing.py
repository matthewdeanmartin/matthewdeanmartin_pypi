"""Tests for signing, claims, and verifier modules."""

from __future__ import annotations

import pytest

from pypi_profile.claims import (PROOF_PREFIX, build_claim, decode_claim,
                                 encode_claim, is_expired)

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
    import sys
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomllib  # type: ignore[no-reuse-def]

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

    import sys
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomllib  # type: ignore[no-reuse-def]

    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)

    new_proof = data["profiles"][0]["stored_proof"]
    assert new_proof.startswith("pypi-profile-proof:")
    assert new_proof != "pypi-profile-proof: old"
