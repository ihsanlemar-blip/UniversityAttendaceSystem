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


def test_metrics_probe_protected_in_production_from_external_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that /metrics and /health/metrics reject unauthorized requests in production."""
    from backend.app.core.config import get_settings
    from backend.app.core.constants import Environment

    settings = get_settings()
    monkeypatch.setattr(settings, "APP_ENV", Environment.PRODUCTION)
    monkeypatch.setattr(settings, "METRICS_ACCESS_KEY", "prod-metrics-secret-key-12345")
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "127.0.0.1/32")

    # 1. Unauthorized request from external IP rejected with 403
    ext_headers = {"X-Forwarded-For": "203.0.113.195"}
    for endpoint in ("/health/metrics", "/metrics"):
        resp = client.get(endpoint, headers=ext_headers)
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"]["code"] == "METRICS_ACCESS_FORBIDDEN"

    # 2. Authorized request with X-Metrics-Key header succeeds
    key_headers = {"X-Metrics-Key": "prod-metrics-secret-key-12345", **ext_headers}
    for endpoint in ("/health/metrics", "/metrics"):
        resp = client.get(endpoint, headers=key_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    # 3. Authorized request with Authorization: Bearer succeeds
    bearer_headers = {"Authorization": "Bearer prod-metrics-secret-key-12345", **ext_headers}
    for endpoint in ("/health/metrics", "/metrics"):
        resp = client.get(endpoint, headers=bearer_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    # 4. Invalid key rejected with 403
    bad_headers = {"X-Metrics-Key": "invalid-token", **ext_headers}
    for endpoint in ("/health/metrics", "/metrics"):
        resp = client.get(endpoint, headers=bad_headers)
        assert resp.status_code == 403


def test_metrics_probe_internal_network_allowed_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that internal network CIDRs can scrape metrics without an explicit key."""
    from backend.app.core.config import get_settings
    from backend.app.core.constants import Environment

    settings = get_settings()
    monkeypatch.setattr(settings, "APP_ENV", Environment.PRODUCTION)
    monkeypatch.setattr(settings, "METRICS_ACCESS_KEY", None)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "127.0.0.1/32")
    monkeypatch.setattr(
        settings, "METRICS_ALLOWED_CIDRS", "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    )

    # Internal container on Docker bridge (172.18.0.5) succeeds
    internal_headers = {"X-Forwarded-For": "172.18.0.5"}
    for endpoint in ("/health/metrics", "/metrics"):
        resp = client.get(endpoint, headers=internal_headers)
        assert resp.status_code == 200

    # Public Internet client (198.51.100.22) rejected with 403
    external_headers = {"X-Forwarded-For": "198.51.100.22"}
    for endpoint in ("/health/metrics", "/metrics"):
        resp = client.get(endpoint, headers=external_headers)
        assert resp.status_code == 403
