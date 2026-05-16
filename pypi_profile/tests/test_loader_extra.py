"""Extra tests for loader.py to fill coverage gaps."""

from __future__ import annotations

import pytest

from pypi_profile.loader import find_profile, find_resume, load_profile


def test_load_profile_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.pypi-profile.profile]
kind = "individual"
display_name = "Test"
[tool.pypi-profile.identity]
pypi_username = "test"
[tool.pypi-profile.verification]
public_key = "pk"
""",
        encoding="utf-8",
    )

    profile = load_profile(pyproject)
    assert profile.profile.display_name == "Test"
    assert profile.verification.public_key == "pk"


def test_find_resume_locations(tmp_path):
    toml_path = tmp_path / "subdir" / "pypi_profile.toml"
    toml_path.parent.mkdir()

    # Adjacent
    resume_path = tmp_path / "subdir" / "resume.json"
    resume_path.touch()
    assert find_resume(toml_path) == resume_path

    resume_path.unlink()

    # One up
    resume_path = tmp_path / "resume.json"
    resume_path.touch()
    assert find_resume(toml_path) == resume_path

    resume_path.unlink()

    # In resources
    res_dir = tmp_path / "subdir" / "resources"
    res_dir.mkdir()
    resume_path = res_dir / "resume.json"
    resume_path.touch()
    assert find_resume(toml_path) == resume_path


def test_find_profile_dir_pypi_profile(tmp_path):
    toml = tmp_path / "pypi_profile.toml"
    toml.touch()
    assert find_profile(str(tmp_path)) == toml


def test_find_profile_dir_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.pypi-profile]\nfoo = "bar"', encoding="utf-8")
    assert find_profile(str(tmp_path)) == pyproject


def test_find_profile_dir_pyproject_no_tool(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.something-else]\nfoo = "bar"', encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        find_profile(str(tmp_path))
