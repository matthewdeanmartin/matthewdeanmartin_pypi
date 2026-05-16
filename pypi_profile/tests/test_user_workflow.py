"""Workflow tests for the core pypi-profile user journey."""

from __future__ import annotations

import argparse
import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from pypi_profile.loader import load_profile
from pypi_profile.signing import generate_keypair, patch_public_key_in_toml


@dataclass
class ProofPageServer:
    root: Path
    server: ThreadingHTTPServer
    thread: threading.Thread

    @property
    def url(self) -> str:
        """Return the proof page URL."""
        port = int(self.server.server_address[1])
        return f"http://127.0.0.1:{port}/proof.html"

    def publish(self, body: str) -> None:
        """Write the current proof page body."""
        (self.root / "proof.html").write_text(body, encoding="utf-8")

    def close(self) -> None:
        """Stop the HTTP server."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


@pytest.fixture()
def proof_page_server(tmp_path: Path) -> Iterator[ProofPageServer]:
    root = tmp_path / "proof-page"
    root.mkdir()
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    proof_server = ProofPageServer(root=root, server=server, thread=thread)
    proof_server.publish("<html><body>Proof page is not published yet.</body></html>")
    try:
        yield proof_server
    finally:
        proof_server.close()


def run_init(dest: Path) -> None:
    from pypi_profile.cli import cmd_init

    args = argparse.Namespace(
        kind="individual",
        username="alice",
        output=str(dest),
        force=False,
        from_json_resume="",
        fetch=False,
        no_interactive=True,
    )
    cmd_init(args)


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise AssertionError(f"Expected snippet not found: {old!r}")
    return text.replace(old, new, 1)


def edit_profile(toml_path: Path, proof_url: str, tmp_path: Path) -> Path:
    text = toml_path.read_text(encoding="utf-8")
    text = text.replace('display_name = "Your Name"', 'display_name = "Alice Example"')
    text = replace_once(
        text,
        'summary = "Python developer and package publisher."',
        'summary = "Builds packaging tools and publishes a verified profile site."',
    )
    text = replace_once(
        text,
        (
            "[[profiles]]\n"
            'kind = "github"\n'
            'label = "GitHub"\n'
            'url = "https://github.com/alice"\n'
            'verification = "self_asserted"'
        ),
        (
            "[[profiles]]\n"
            'kind = "website"\n'
            'label = "Proof page"\n'
            f'url = "{proof_url}"\n'
            'verification = "self_asserted"'
        ),
    )
    text = replace_once(text, 'name = "your-package"', 'name = "workflow-package"')
    text = replace_once(text, 'summary = "A Python package."', 'summary = "Exercises the end-to-end user workflow."')
    text = replace_once(
        text,
        "[hiring]\n",
        (
            "[[projects]]\n"
            'name = "workflow-site"\n'
            'url = "https://example.com/workflow-site"\n'
            'role = "creator"\n'
            'state = "active"\n'
            'summary = "Covers the static build output."\n'
            "\n[hiring]\n"
        ),
    )
    toml_path.write_text(text, encoding="utf-8")

    sk_path, pk_path, _public_key = generate_keypair(key_dir=tmp_path / "keys", password="", force=True)
    patched_public_key = patch_public_key_in_toml(toml_path, pk_path)
    assert patched_public_key
    return sk_path


def update_proofs(toml_path: Path, secret_key_path: Path) -> str:
    from pypi_profile.cli import cmd_update_proofs

    args = argparse.Namespace(
        source=str(toml_path),
        key=str(secret_key_path),
        password="",
        profile_package="",
        force=False,
    )
    cmd_update_proofs(args)
    profile = load_profile(toml_path)
    assert len(profile.profiles) == 1
    return profile.profiles[0].stored_proof


def test_init_phase_creates_a_starter_profile(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    toml_path = tmp_path / "pypi_profile.toml"

    run_init(toml_path)

    profile = load_profile(toml_path)
    captured = capsys.readouterr()

    assert toml_path.exists()
    assert "Created" in captured.out
    assert profile.identity.pypi_username == "alice"
    assert profile.packages[0].name == "your-package"
    assert profile.profiles[0].url == "https://github.com/alice"


def test_edit_phase_keeps_manual_changes_loadable(tmp_path: Path, proof_page_server: ProofPageServer) -> None:
    toml_path = tmp_path / "pypi_profile.toml"
    run_init(toml_path)

    edit_profile(toml_path, proof_page_server.url, tmp_path)

    profile = load_profile(toml_path)

    assert profile.profile.display_name == "Alice Example"
    assert profile.profile.summary == "Builds packaging tools and publishes a verified profile site."
    assert profile.profiles[0].label == "Proof page"
    assert profile.profiles[0].url == proof_page_server.url
    assert profile.packages[0].name == "workflow-package"
    assert profile.projects[0].name == "workflow-site"
    assert profile.verification.public_key


def test_update_and_verify_phases_cover_live_proof_publication(
    tmp_path: Path,
    proof_page_server: ProofPageServer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pypi_profile.cli import cmd_verify

    toml_path = tmp_path / "pypi_profile.toml"
    run_init(toml_path)
    secret_key_path = edit_profile(toml_path, proof_page_server.url, tmp_path)

    stored_proof = update_proofs(toml_path, secret_key_path)
    proof_page_server.publish(f"<html><body>{stored_proof}</body></html>")

    args = argparse.Namespace(source=str(toml_path), profile_package="")
    cmd_verify(args)
    captured = capsys.readouterr()

    assert stored_proof.startswith("pypi-profile-proof:")
    assert 'stored_proof = "pypi-profile-proof:' in toml_path.read_text(encoding="utf-8")
    assert "Proof page" in captured.out
    assert "verified" in captured.out
    assert "1/1 claims verified." in captured.out


def test_build_phase_publishes_the_verified_static_site(tmp_path: Path, proof_page_server: ProofPageServer) -> None:
    from pypi_profile.cli import cmd_build, cmd_verify

    toml_path = tmp_path / "pypi_profile.toml"
    output_path = tmp_path / "dist"

    run_init(toml_path)
    secret_key_path = edit_profile(toml_path, proof_page_server.url, tmp_path)
    stored_proof = update_proofs(toml_path, secret_key_path)
    proof_page_server.publish(f"<html><body>{stored_proof}</body></html>")
    cmd_verify(argparse.Namespace(source=str(toml_path), profile_package=""))

    cmd_build(argparse.Namespace(source=str(toml_path), output=str(output_path), resume_file="", base_url=""))

    verification_data = json.loads((output_path / "api" / "verification.json").read_text(encoding="utf-8"))
    profile_data = json.loads((output_path / "api" / "profile.json").read_text(encoding="utf-8"))
    projects_html = (output_path / "projects" / "index.html").read_text(encoding="utf-8")

    assert (output_path / "index.html").exists()
    assert verification_data["static_mode"] is True
    assert verification_data["claim_results"][0]["status"] == "verified"
    assert verification_data["claim_results"][0]["has_stored_proof"] is True
    assert profile_data["profile"]["display_name"] == "Alice Example"
    assert profile_data["packages"][0]["name"] == "workflow-package"
    assert "workflow-site" in projects_html
