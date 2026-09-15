"""Celery background tasks for attendance reconciliation."""

import asyncio
import uuid

from backend.app.attendance.offline_service import OfflineAttendanceService
from backend.app.core.celery_app import celery_app
from backend.app.core.database import get_sessionmaker


@celery_app.task(name="attendance.reconcile_offline_session")
def reconcile_offline_session_task(host_session_id_str: str) -> dict[str, int]:
    """Asynchronous background worker task reconciling pending offline claims."""
    host_session_id = uuid.UUID(host_session_id_str)

    async def _run() -> tuple[int, int]:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            return await OfflineAttendanceService.reconcile_claims_for_host_session(
                db=db,
                host_session_id=host_session_id,
            )

    reconciled, conflicts = asyncio.run(_run())
    return {
        "reconciled_count": reconciled,
        "conflict_count": conflicts,
    }
