"""Test suite for backend health check endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_liveness_probe() -> None:
    """Verify that /health/live returns HTTP 200 with alive status."""
    response = client.get("/health/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "alive"
    assert payload["service"] == "backend"
    assert "version" in payload


@pytest.mark.asyncio
async def test_readiness_probe_healthy() -> None:
    """Verify that /health/ready returns HTTP 200 when all backing services are ready."""
    with patch(
        "backend.app.health.service.HealthService.evaluate_readiness",
        new_callable=AsyncMock,
        return_value=(True, {"database": "healthy", "redis": "healthy"}),
    ):
        response = client.get("/health/ready")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["service"] == "backend"
        assert payload["dependencies"]["database"] == "healthy"
        assert payload["dependencies"]["redis"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_probe_degraded() -> None:
    """Verify that /health/ready returns HTTP 503 when a backing service is unreachable."""
    with patch(
        "backend.app.health.service.HealthService.evaluate_readiness",
        new_callable=AsyncMock,
        return_value=(False, {"database": "unreachable", "redis": "healthy"}),
    ):
        response = client.get("/health/ready")
        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == "unhealthy"
        assert payload["dependencies"]["database"] == "unreachable"
        assert payload["dependencies"]["redis"] == "healthy"
