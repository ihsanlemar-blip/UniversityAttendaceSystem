"""Unit tests for middleware (backend/app/core/middleware.py)."""

import uuid

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_request_id_generated_when_missing() -> None:
    """Verify that a request without X-Request-ID receives a newly generated UUID."""
    response = client.get("/health/live")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    # Validate UUID format
    parsed = uuid.UUID(req_id)
    assert str(parsed) == req_id


def test_request_id_preserved_when_valid() -> None:
    """Verify that a valid incoming X-Request-ID is retained in response headers."""
    client_uuid = "0191eb70-7613-7d94-a102-3c58376e1001"
    response = client.get("/health/live", headers={"X-Request-ID": client_uuid})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == client_uuid


def test_request_id_replaced_when_invalid() -> None:
    """Verify that an invalid or malicious X-Request-ID is discarded and replaced."""
    invalid_ids = [
        "<script>alert(1)</script>",
        "spaces in request id",
        "id;DROP TABLE universities;",
        "a" * 200,
        "id@domain.com",
    ]
    for bad_id in invalid_ids:
        response = client.get("/health/live", headers={"X-Request-ID": bad_id})
        assert response.status_code == 200
        assigned_id = response.headers.get("X-Request-ID")
        assert assigned_id is not None
        assert assigned_id != bad_id
        # Must be a valid UUID
        assert str(uuid.UUID(assigned_id)) == assigned_id
