"""Test suite for backend bootstrap health endpoints."""

from typing import Generator
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide a TestClient instance for testing routes."""
    with TestClient(app) as test_client:
        yield test_client


def test_liveness_probe(client: TestClient) -> None:
    """Verify that /health/live returns HTTP 200 with alive status."""
    response = client.get("/health/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "alive"
    assert payload["service"] == "backend"
    assert payload["version"] == "0.1.0"


def test_readiness_probe(client: TestClient) -> None:
    """Verify that /health/ready returns HTTP 200 with component statuses."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["components"]["api"] == "ok"
