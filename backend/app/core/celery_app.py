"""Celery asynchronous task queue foundation and diagnostic tasks."""

from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from celery import Celery  # type: ignore[import-untyped]

settings = get_settings()

celery_app = Celery(
    "attendance_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Standard Celery operational configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.UNIVERSITY_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
)


@celery_app.task(name="system.ping")
def ping_task() -> dict:
    """Harmless diagnostic infrastructure test task."""
    return {
        "pong": True,
        "service": "attendance-worker",
        "timestamp": utc_now().isoformat(),
    }
