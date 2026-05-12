"""Integration tests for the FastAPI profile server."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

JOHN_DOE_TOML = (
    Path(__file__).parent.parent.parent / "john_doe" / "john_doe" / "pypi_profile.toml"
)


@pytest.fixture()
def client() -> TestClient:
    from pypi_profile.loader import load_profile
    from pypi_profile.server import build_app

    profile = load_profile(JOHN_DOE_TOML)
    app = build_app(profile)
    return TestClient(app)


def test_summary_page_renders(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "John Doe" in response.text


def test_packages_page_renders(client: TestClient) -> None:
    response = client.get("/packages")
    assert response.status_code == 200
    assert "john-doe" in response.text


def test_projects_page_renders(client: TestClient) -> None:
    response = client.get("/projects")
    assert response.status_code == 200


def test_hiring_page_renders(client: TestClient) -> None:
    response = client.get("/hiring")
    assert response.status_code == 200
    assert "Consulting" in response.text


def test_contact_page_renders(client: TestClient) -> None:
    response = client.get("/contact")
    assert response.status_code == 200


def test_verification_page_renders(client: TestClient) -> None:
    response = client.get("/verification")
    assert response.status_code == 200
    assert "PyPI-published" in response.text


def test_succession_page_renders(client: TestClient) -> None:
    response = client.get("/succession")
    assert response.status_code == 200
    assert "Succession policy" in response.text


def test_api_profile_json(client: TestClient) -> None:
    response = client.get("/api/profile.json")
    assert response.status_code == 200
    data = response.json()
    assert data["identity"]["pypi_username"] == "john_doe"


def test_api_packages_json(client: TestClient) -> None:
    response = client.get("/api/packages.json")
    assert response.status_code == 200
    pkgs = response.json()
    assert len(pkgs) == 3
    names = [p["name"] for p in pkgs]
    assert "john-doe" in names


def test_api_people_json(client: TestClient) -> None:
    response = client.get("/api/people.json")
    assert response.status_code == 200
    people = response.json()
    assert len(people) == 1
    assert people[0]["display_name"] == "John Doe"
