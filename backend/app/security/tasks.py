"""Celery background tasks for anti-cheat and security pattern analysis.

Enforces M14 Invariants:
- Asynchronous detection runs in the background and NEVER blocks critical path check-ins.
- Generated signals are recorded for human review; they never auto-punish students.
- PostgreSQL remains authoritative.
"""

from __future__ import annotations

import asyncio
import uuid

from backend.app.core.celery_app import celery_app
from backend.app.core.database import get_sessionmaker
from backend.app.security.risk_service import AntiCheatService


@celery_app.task(name="security.analyze_device_replacement_frequency")
def analyze_device_replacement_frequency_task(
    university_id_str: str,
    student_id_str: str,
    user_id_str: str,
) -> dict[str, str | None]:
    """Background task detecting rapid device replacement frequency."""
    university_id = uuid.UUID(university_id_str)
    student_id = uuid.UUID(student_id_str)
    user_id = uuid.UUID(user_id_str)

    async def _run() -> str | None:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            async with db.begin():
                signal = await AntiCheatService.analyze_device_replacement_frequency(
                    db=db,
                    university_id=university_id,
                    student_id=student_id,
                    user_id=user_id,
                )
                return str(signal.id) if signal else None

    signal_id = asyncio.run(_run())
    return {"signal_id": signal_id}


@celery_app.task(name="security.analyze_overlapping_attendance")
def analyze_overlapping_attendance_task(
    university_id_str: str,
    student_id_str: str,
    user_id_str: str,
) -> dict[str, str | None]:
    """Background task detecting student overlapping attendance across class occurrences."""
    university_id = uuid.UUID(university_id_str)
    student_id = uuid.UUID(student_id_str)
    user_id = uuid.UUID(user_id_str)

    async def _run() -> str | None:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            async with db.begin():
                signal = await AntiCheatService.analyze_overlapping_attendance(
                    db=db,
                    university_id=university_id,
                    student_id=student_id,
                    user_id=user_id,
                )
                return str(signal.id) if signal else None

    signal_id = asyncio.run(_run())
    return {"signal_id": signal_id}


@celery_app.task(name="security.analyze_session_manual_attendance_rate")
def analyze_session_manual_attendance_rate_task(
    university_id_str: str,
    session_id_str: str,
) -> dict[str, str | None]:
    """Background task evaluating session manual attendance rate."""
    university_id = uuid.UUID(university_id_str)
    session_id = uuid.UUID(session_id_str)

    async def _run() -> str | None:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            async with db.begin():
                signal = await AntiCheatService.analyze_session_manual_attendance_rate(
                    db=db,
                    university_id=university_id,
                    session_id=session_id,
                )
                return str(signal.id) if signal else None

    signal_id = asyncio.run(_run())
    return {"signal_id": signal_id}


@celery_app.task(name="security.analyze_session_correction_rate")
def analyze_session_correction_rate_task(
    university_id_str: str,
    session_id_str: str,
) -> dict[str, str | None]:
    """Background task evaluating session revision and correction rate."""
    university_id = uuid.UUID(university_id_str)
    session_id = uuid.UUID(session_id_str)

    async def _run() -> str | None:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            async with db.begin():
                signal = await AntiCheatService.analyze_session_correction_rate(
                    db=db,
                    university_id=university_id,
                    session_id=session_id,
                )
                return str(signal.id) if signal else None

    signal_id = asyncio.run(_run())
    return {"signal_id": signal_id}
