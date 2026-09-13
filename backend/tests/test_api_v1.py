"""Unit tests for API v1 root metadata endpoint."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_api_v1_metadata() -> None:
    """Verify GET /api/v1/ returns operational status and versioning."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Digital Student Attendance API"
    assert data["api_version"] == "v1"
    assert data["status"] == "operational"
    assert "environment" in data
    assert "server_time_utc" in data
