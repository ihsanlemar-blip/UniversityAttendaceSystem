"""Unit tests for Celery worker configuration and diagnostic ping task."""

from backend.app.core.celery_app import celery_app, ping_task


def test_celery_configuration() -> None:
    """Verify Celery app is properly configured with Redis broker and backend."""
    assert celery_app.conf.broker_url.startswith("redis://")
    assert celery_app.conf.result_backend.startswith("redis://")
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.enable_utc is True


def test_celery_ping_task_execution() -> None:
    """Verify diagnostic system.ping task executes directly and returns valid payload."""
    result = ping_task.apply()
    assert result.successful()
    data = result.result
    assert data["pong"] is True
    assert data["service"] == "attendance-worker"
    assert "timestamp" in data
