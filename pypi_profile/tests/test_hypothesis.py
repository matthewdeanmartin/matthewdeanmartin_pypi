"""Property-based tests using Hypothesis.

Focused on pure, deterministic functions where fuzzing yields real value:
encoding/decoding roundtrips, regex parsing, sanitisation, and expiry logic.
"""

from __future__ import annotations

import string
from datetime import datetime, timedelta, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

printable_text = st.text(alphabet=string.printable, min_size=0, max_size=200)
safe_text = st.text(min_size=1, max_size=100)
nonempty_text = st.text(
    min_size=1, max_size=80, alphabet=string.ascii_letters + string.digits + "-_."
)

# Reasonable datetimes — avoid edge cases like year 0 or year 9999 overflow
reasonable_datetime = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2035, 12, 31),
    timezones=st.just(timezone.utc),
)


# ---------------------------------------------------------------------------
# claims.py — encode / decode roundtrip
# ---------------------------------------------------------------------------


class TestClaimsEncodeDecodeRoundtrip:
    """encode_claim followed by decode_claim must recover the original dict."""

    @given(
        profile_package=nonempty_text,
        pypi_username=nonempty_text,
        subject_url=nonempty_text,
        nonce=nonempty_text,
        issued=reasonable_datetime,
    )
    def test_full_claim_roundtrip(
        self, profile_package, pypi_username, subject_url, nonce, issued
    ):
        from pypi_profile.claims import build_claim, decode_claim, encode_claim

        expires = issued + timedelta(days=365)
        claim = build_claim(
            profile_package=profile_package,
            pypi_username=pypi_username,
            claim_type="controls-url",
            subject_url=subject_url,
            key_id="AABBCCDD",
            issued_at=issued,
            expires_at=expires,
            nonce=nonce,
        )
        token = encode_claim(claim)
        recovered = decode_claim(token)
        assert recovered == claim

    @given(
        profile_package=nonempty_text,
        pypi_username=nonempty_text,
        subject_url=nonempty_text,
        nonce=nonempty_text,
        issued=reasonable_datetime,
    )
    def test_compact_claim_roundtrip(
        self, profile_package, pypi_username, subject_url, nonce, issued
    ):
        from pypi_profile.claims import build_compact_claim, decode_claim, encode_claim

        expires = issued + timedelta(days=365)
        claim = build_compact_claim(
            profile_package=profile_package,
            pypi_username=pypi_username,
            subject_url=subject_url,
            issued_at=issued,
            expires_at=expires,
            nonce=nonce,
        )
        token = encode_claim(claim)
        recovered = decode_claim(token)
        assert recovered == claim

    @given(nonempty_text)
    def test_decode_strips_prefix(self, payload_text):
        """decode_claim must handle tokens with or without the proof prefix."""
        from pypi_profile.claims import PROOF_PREFIX, decode_claim, encode_claim

        claim = {"key": payload_text}
        token_with_prefix = encode_claim(claim)
        # Token already has prefix; also test stripping it manually
        assert token_with_prefix.startswith(PROOF_PREFIX)
        token_bare = token_with_prefix[len(PROOF_PREFIX) :].strip()
        assert decode_claim(token_with_prefix) == decode_claim(token_bare)

    @given(
        profile_package=nonempty_text,
        pypi_username=nonempty_text,
        subject_url=nonempty_text,
    )
    def test_encode_always_starts_with_prefix(
        self, profile_package, pypi_username, subject_url
    ):
        from pypi_profile.claims import PROOF_PREFIX, build_compact_claim, encode_claim

        claim = build_compact_claim(
            profile_package=profile_package,
            pypi_username=pypi_username,
            subject_url=subject_url,
        )
        token = encode_claim(claim)
        assert token.startswith(PROOF_PREFIX)

    @given(
        profile_package=nonempty_text,
        pypi_username=nonempty_text,
        subject_url=nonempty_text,
    )
    def test_encoded_token_is_string(self, profile_package, pypi_username, subject_url):
        from pypi_profile.claims import build_compact_claim, encode_claim

        claim = build_compact_claim(
            profile_package=profile_package,
            pypi_username=pypi_username,
            subject_url=subject_url,
        )
        assert isinstance(encode_claim(claim), str)


# ---------------------------------------------------------------------------
# claims.py — is_compact_claim detection
# ---------------------------------------------------------------------------


class TestIsCompactClaim:
    @given(
        profile_package=nonempty_text,
        pypi_username=nonempty_text,
        subject_url=nonempty_text,
    )
    def test_compact_build_is_detected_as_compact(
        self, profile_package, pypi_username, subject_url
    ):
        from pypi_profile.claims import build_compact_claim, is_compact_claim

        claim = build_compact_claim(
            profile_package=profile_package,
            pypi_username=pypi_username,
            subject_url=subject_url,
        )
        assert is_compact_claim(claim) is True

    @given(
        profile_package=nonempty_text,
        pypi_username=nonempty_text,
        subject_url=nonempty_text,
    )
    def test_full_build_is_not_compact(
        self, profile_package, pypi_username, subject_url
    ):
        from pypi_profile.claims import build_claim, is_compact_claim

        claim = build_claim(
            profile_package=profile_package,
            pypi_username=pypi_username,
            claim_type="controls-url",
            subject_url=subject_url,
            key_id="AABBCCDD",
        )
        assert is_compact_claim(claim) is False


# ---------------------------------------------------------------------------
# claims.py — is_expired
# ---------------------------------------------------------------------------


class TestIsExpired:
    @given(future_offset_days=st.integers(min_value=1, max_value=3650))
    def test_future_expiry_not_expired_full_format(self, future_offset_days):
        from pypi_profile.claims import build_claim, is_expired

        now = datetime.now(tz=timezone.utc)
        claim = build_claim(
            profile_package="pkg",
            pypi_username="user",
            claim_type="controls-url",
            subject_url="https://example.com",
            key_id="AABB",
            issued_at=now,
            expires_at=now + timedelta(days=future_offset_days),
        )
        assert is_expired(claim) is False

    @given(past_offset_days=st.integers(min_value=1, max_value=3650))
    def test_past_expiry_is_expired_full_format(self, past_offset_days):
        from pypi_profile.claims import build_claim, is_expired

        now = datetime.now(tz=timezone.utc)
        claim = build_claim(
            profile_package="pkg",
            pypi_username="user",
            claim_type="controls-url",
            subject_url="https://example.com",
            key_id="AABB",
            issued_at=now - timedelta(days=past_offset_days + 1),
            expires_at=now - timedelta(days=past_offset_days),
        )
        assert is_expired(claim) is True

    @given(future_offset_days=st.integers(min_value=1, max_value=3650))
    def test_future_expiry_not_expired_compact_format(self, future_offset_days):
        from pypi_profile.claims import build_compact_claim, is_expired

        now = datetime.now(tz=timezone.utc)
        claim = build_compact_claim(
            profile_package="pkg",
            pypi_username="user",
            subject_url="https://example.com",
            issued_at=now,
            expires_at=now + timedelta(days=future_offset_days),
        )
        assert is_expired(claim) is False

    @given(past_offset_days=st.integers(min_value=1, max_value=3650))
    def test_past_expiry_is_expired_compact_format(self, past_offset_days):
        from pypi_profile.claims import build_compact_claim, is_expired

        now = datetime.now(tz=timezone.utc)
        claim = build_compact_claim(
            profile_package="pkg",
            pypi_username="user",
            subject_url="https://example.com",
            issued_at=now - timedelta(days=past_offset_days + 1),
            expires_at=now - timedelta(days=past_offset_days),
        )
        assert is_expired(claim) is True

    def test_missing_expiry_is_not_expired_full(self):
        from pypi_profile.claims import is_expired

        assert is_expired({}) is False

    def test_malformed_expiry_is_not_expired_full(self):
        from pypi_profile.claims import is_expired

        assert is_expired({"expires_at": "not-a-date"}) is False

    def test_missing_expiry_is_not_expired_compact(self):
        from pypi_profile.claims import is_expired

        # Compact claim without 'e' — treated as not expired
        assert is_expired({"p": "pkg", "s": "https://x.com"}) is False

    @given(future_offset_days=st.integers(min_value=1, max_value=3650))
    def test_full_and_compact_agree_on_future_expiry(self, future_offset_days):
        """Both formats must report the same expiry status for equivalent timestamps."""
        from pypi_profile.claims import build_claim, build_compact_claim, is_expired

        now = datetime.now(tz=timezone.utc)
        expires = now + timedelta(days=future_offset_days)
        full_claim = build_claim(
            profile_package="pkg",
            pypi_username="user",
            claim_type="controls-url",
            subject_url="https://example.com",
            key_id="AABB",
            issued_at=now,
            expires_at=expires,
        )
        compact_claim = build_compact_claim(
            profile_package="pkg",
            pypi_username="user",
            subject_url="https://example.com",
            issued_at=now,
            expires_at=expires,
        )
        assert is_expired(full_claim) == is_expired(compact_claim)


# ---------------------------------------------------------------------------
# claims.py — build_claim timestamp ordering
# ---------------------------------------------------------------------------


class TestBuildClaimTimestamps:
    @given(issued=reasonable_datetime)
    def test_default_expires_is_after_issued(self, issued):
        from pypi_profile.claims import build_claim

        claim = build_claim(
            profile_package="pkg",
            pypi_username="user",
            claim_type="controls-url",
            subject_url="https://example.com",
            key_id="AABB",
            issued_at=issued,
        )
        issued_at = datetime.strptime(claim["issued_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        expires_at = datetime.strptime(
            claim["expires_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        assert expires_at > issued_at

    @given(issued=reasonable_datetime)
    def test_compact_default_expires_is_after_issued(self, issued):
        from pypi_profile.claims import build_compact_claim

        claim = build_compact_claim(
            profile_package="pkg",
            pypi_username="user",
            subject_url="https://example.com",
            issued_at=issued,
        )
        assert claim["e"] > claim["i"]

    @given(issued=reasonable_datetime)
    def test_build_claim_iso_format_is_parseable(self, issued):
        from pypi_profile.claims import build_claim

        claim = build_claim(
            profile_package="pkg",
            pypi_username="user",
            claim_type="controls-url",
            subject_url="https://x.com",
            key_id="AABB",
            issued_at=issued,
        )
        for field in ("issued_at", "expires_at"):
            dt = datetime.strptime(claim[field], "%Y-%m-%dT%H:%M:%SZ")
            assert dt is not None

    @given(issued=reasonable_datetime)
    def test_compact_timestamps_are_integers(self, issued):
        from pypi_profile.claims import build_compact_claim

        claim = build_compact_claim(
            profile_package="pkg",
            pypi_username="user",
            subject_url="https://x.com",
            issued_at=issued,
        )
        assert isinstance(claim["i"], int)
        assert isinstance(claim["e"], int)


# ---------------------------------------------------------------------------
# verifier.py — find_proof_tokens
# ---------------------------------------------------------------------------


class TestFindProofTokens:
    @given(printable_text)
    def test_tokens_always_contain_prefix(self, text):
        from pypi_profile.verifier import find_proof_tokens

        tokens = find_proof_tokens(text)
        for token in tokens:
            assert "pypi-profile-proof" in token.lower()

    @given(
        profile_package=nonempty_text,
        pypi_username=nonempty_text,
        subject_url=nonempty_text,
    )
    def test_encoded_claim_is_found_in_text(
        self, profile_package, pypi_username, subject_url
    ):
        from pypi_profile.claims import build_compact_claim, encode_claim
        from pypi_profile.verifier import find_proof_tokens

        claim = build_compact_claim(
            profile_package=profile_package,
            pypi_username=pypi_username,
            subject_url=subject_url,
        )
        token = encode_claim(claim)
        surrounding = f"Some text before\n{token}\nSome text after"
        found = find_proof_tokens(surrounding)
        assert len(found) == 1

    @given(printable_text)
    def test_returns_list(self, text):
        from pypi_profile.verifier import find_proof_tokens

        result = find_proof_tokens(text)
        assert isinstance(result, list)

    def test_empty_string_returns_empty_list(self):
        from pypi_profile.verifier import find_proof_tokens

        assert find_proof_tokens("") == []

    @given(
        profile_package=nonempty_text,
        pypi_username=nonempty_text,
        subject_url=nonempty_text,
    )
    def test_case_insensitive_prefix_is_found(
        self, profile_package, pypi_username, subject_url
    ):
        from pypi_profile.claims import build_compact_claim, encode_claim
        from pypi_profile.verifier import find_proof_tokens

        claim = build_compact_claim(
            profile_package=profile_package,
            pypi_username=pypi_username,
            subject_url=subject_url,
        )
        token = encode_claim(claim)
        uppercased = token.replace("pypi-profile-proof:", "PYPI-PROFILE-PROOF:")
        found = find_proof_tokens(uppercased)
        assert len(found) == 1


# ---------------------------------------------------------------------------
# fetcher.py — cache_path sanitisation
# ---------------------------------------------------------------------------


class TestCachePath:
    @given(safe_text)
    @settings(max_examples=50)
    def test_cache_path_is_a_path(self, key):
        from pathlib import Path

        from pypi_profile.fetcher import cache_path

        result = cache_path(key)
        assert isinstance(result, Path)

    @given(safe_text)
    @settings(max_examples=50)
    def test_cache_path_ends_with_json(self, key):
        from pypi_profile.fetcher import cache_path

        result = cache_path(key)
        assert result.name.endswith(".json")

    @given(
        st.text(
            alphabet=string.printable.replace("\\", "").replace("/", ""),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=50)
    def test_cache_path_stays_in_cache_dir(self, key):
        """Keys without path separators always resolve inside the cache dir."""
        from pypi_profile.fetcher import CACHE_DIR, cache_path

        result = cache_path(key)
        assert result.parent.name == CACHE_DIR.name

    @given(safe_text)
    @settings(max_examples=50)
    def test_cache_path_is_deterministic(self, key):
        from pypi_profile.fetcher import cache_path

        assert cache_path(key) == cache_path(key)

    @given(key=st.text(alphabet="/:@", min_size=1, max_size=20))
    @settings(max_examples=30)
    def test_cache_path_sanitises_special_chars(self, key):
        from pypi_profile.fetcher import cache_path

        result = cache_path(key)
        # Forward slashes must not appear in the filename (they'd create subdirs)
        assert "/" not in result.name


# ---------------------------------------------------------------------------
# fetcher.py — extract_github/gitlab_username
# ---------------------------------------------------------------------------


class TestExtractGithubUsername:
    @given(
        username=st.text(
            alphabet=string.ascii_letters + string.digits + "-_",
            min_size=1,
            max_size=39,
        )
    )
    def test_valid_github_url_extracts_username(self, username):
        from pypi_profile.fetcher import extract_github_username

        url = f"https://github.com/{username}"
        result = extract_github_username(url)
        assert result == username

    @given(
        username=st.text(
            alphabet=string.ascii_letters + string.digits + "-_",
            min_size=1,
            max_size=39,
        )
    )
    def test_trailing_slash_still_extracts(self, username):
        from pypi_profile.fetcher import extract_github_username

        url = f"https://github.com/{username}/"
        result = extract_github_username(url)
        assert result == username

    @given(printable_text)
    def test_non_github_url_returns_empty(self, text):
        from pypi_profile.fetcher import extract_github_username

        if "github.com" in text:
            return
        result = extract_github_username(text)
        assert result == ""

    def test_github_url_with_path_returns_empty(self):
        from pypi_profile.fetcher import extract_github_username

        assert extract_github_username("https://github.com/user/repo") == ""

    @given(
        username=st.text(
            alphabet=string.ascii_letters + string.digits + "-_",
            min_size=1,
            max_size=39,
        )
    )
    def test_extracted_username_has_no_slash(self, username):
        from pypi_profile.fetcher import extract_github_username

        url = f"https://github.com/{username}"
        result = extract_github_username(url)
        assert "/" not in result


class TestExtractGitlabUsername:
    @given(
        username=st.text(
            alphabet=string.ascii_letters + string.digits + "-_",
            min_size=1,
            max_size=39,
        )
    )
    def test_valid_gitlab_url_extracts_username(self, username):
        from pypi_profile.fetcher import extract_gitlab_username

        url = f"https://gitlab.com/{username}"
        result = extract_gitlab_username(url)
        assert result == username

    @given(
        username=st.text(
            alphabet=string.ascii_letters + string.digits + "-_",
            min_size=1,
            max_size=39,
        )
    )
    def test_trailing_slash_still_extracts(self, username):
        from pypi_profile.fetcher import extract_gitlab_username

        url = f"https://gitlab.com/{username}/"
        result = extract_gitlab_username(url)
        assert result == username

    @given(printable_text)
    def test_non_gitlab_url_returns_empty(self, text):
        from pypi_profile.fetcher import extract_gitlab_username

        if "gitlab.com" in text:
            return
        result = extract_gitlab_username(text)
        assert result == ""

    def test_gitlab_url_with_subpath_returns_empty(self):
        from pypi_profile.fetcher import extract_gitlab_username

        assert extract_gitlab_username("https://gitlab.com/user/project") == ""


# ---------------------------------------------------------------------------
# finder.py — should_skip_dir
# ---------------------------------------------------------------------------


class TestShouldSkipDir:
    @given(
        name=st.sampled_from(
            [
                ".venv",
                "venv",
                ".env",
                "env",
                "__pycache__",
                ".git",
                "node_modules",
                ".tox",
                ".mypy_cache",
                ".pytest_cache",
                "dist",
                "build",
                "temp",
                "site-packages",
                ".eggs",
            ]
        )
    )
    def test_known_skip_dirs_are_skipped(self, name):
        from pypi_profile.finder import should_skip_dir

        assert should_skip_dir(name) is True

    @given(
        name=st.sampled_from(
            [".VENV", "VENV", ".Git", "NODE_MODULES", "__PYCACHE__", "DIST"]
        )
    )
    def test_skip_is_case_insensitive(self, name):
        from pypi_profile.finder import should_skip_dir

        assert should_skip_dir(name) is True

    @given(
        suffix=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-",
            min_size=1,
            max_size=20,
        )
    )
    def test_egg_info_suffix_is_skipped(self, suffix):
        from pypi_profile.finder import should_skip_dir

        assert should_skip_dir(f"{suffix}.egg-info") is True

    @given(
        name=st.text(
            alphabet=string.ascii_letters + string.digits + "_-",
            min_size=1,
            max_size=30,
        )
    )
    def test_normal_dir_names_not_skipped(self, name):
        from pypi_profile.finder import SKIP_DIRS, should_skip_dir

        lowered_name = name.lower()
        # Exclude names that collide with the actual skip set or end in .egg-info
        if lowered_name in SKIP_DIRS or lowered_name.endswith(".egg-info"):
            return
        assert should_skip_dir(name) is False

    def test_src_not_skipped(self):
        from pypi_profile.finder import should_skip_dir

        assert should_skip_dir("src") is False

    def test_mypackage_not_skipped(self):
        from pypi_profile.finder import should_skip_dir

        assert should_skip_dir("mypackage") is False
