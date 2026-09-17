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


def test_metrics_probe() -> None:
    """Verify that /health/metrics and /metrics return HTTP 200 with uptime and pool stats."""
    for endpoint in ("/health/metrics", "/metrics"):
        response = client.get(endpoint)
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["uptime_seconds"] >= 0
        assert "db_pool" in payload
        assert "size" in payload["db_pool"]


@pytest.mark.asyncio
async def test_readiness_probe_redis_down() -> None:
    """Verify that /health/ready returns HTTP 503 when Redis is unreachable."""
    with patch(
        "backend.app.health.service.HealthService.evaluate_readiness",
        new_callable=AsyncMock,
        return_value=(False, {"database": "healthy", "redis": "unreachable"}),
    ):
        response = client.get("/health/ready")
        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == "unhealthy"
        assert payload["dependencies"]["database"] == "healthy"
        assert payload["dependencies"]["redis"] == "unreachable"


@pytest.mark.asyncio
async def test_check_redis_connectivity_failure_surfaced_cleanly() -> None:
    """Verify check_redis_connectivity handles connection failure gracefully without raising."""
    from backend.app.core.redis import check_redis_connectivity

    with patch("backend.app.core.redis.get_redis") as mock_get_redis:
        mock_client = AsyncMock()
        mock_client.ping.side_effect = ConnectionError("Redis connection refused")
        mock_get_redis.return_value = mock_client

        result = await check_redis_connectivity()
        assert result is False
