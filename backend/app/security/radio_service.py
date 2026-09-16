"""Radio Environment Analysis Service for classroom BLE diagnostics.

Computes aggregated BLE RSSI metrics (count, median, p10, p25, p75, p90, min, max)
from AttendanceEvidence across campus rooms, buildings, and sessions.

Enforces M14 Invariants:
- Zero distance conversion (RSSI is not converted to physical meters).
- No auto-tuning (never automatically mutates ATTENDANCE_BLE_MIN_RSSI).
- Strict multi-tenant isolation via university_id.
- Privacy-preserving classroom aggregation without exposing student identity.
"""

from __future__ import annotations

import datetime
import math
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.attendance_checkpoint import AttendanceCheckpoint
from backend.app.models.attendance_evidence import AttendanceEvidence
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.room import Room
from backend.app.security.schemas import RadioAnalysisSummary


def calculate_percentile(sorted_values: Sequence[int], percentile: float) -> float:
    """Calculate percentile (0-100) from a sorted list of numbers using linear interpolation."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    if n == 1:
        return float(sorted_values[0])
    k = (n - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_values[int(k)])
    d0 = sorted_values[int(f)] * (c - k)
    d1 = sorted_values[int(c)] * (k - f)
    return round(float(d0 + d1), 2)


class RadioAnalysisService:
    """Aggregates and computes classroom BLE radio environment statistics."""

    @classmethod
    async def analyze_radio_environment(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        building_id: uuid.UUID | None = None,
        room_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        time_window_start: datetime.datetime | None = None,
        time_window_end: datetime.datetime | None = None,
    ) -> RadioAnalysisSummary:
        """Query BLE RSSI evidence and compute aggregate metrics."""
        # Base query joining through Checkpoint -> Session -> ClassOccurrence -> Room
        query = (
            sa.select(
                AttendanceEvidence.evidence_metadata,
            )
            .select_from(AttendanceEvidence)
            .join(
                AttendanceCheckpoint,
                AttendanceEvidence.attendance_checkpoint_id == AttendanceCheckpoint.id,
            )
            .join(
                AttendanceSession,
                AttendanceCheckpoint.attendance_session_id == AttendanceSession.id,
            )
            .join(
                ClassOccurrence,
                AttendanceSession.class_occurrence_id == ClassOccurrence.id,
            )
            .outerjoin(
                Room,
                ClassOccurrence.room_id == Room.id,
            )
            .where(
                AttendanceSession.university_id == university_id,
                AttendanceEvidence.evidence_metadata.is_not(None),
            )
        )

        if session_id is not None:
            query = query.where(AttendanceSession.id == session_id)
        if room_id is not None:
            query = query.where(ClassOccurrence.room_id == room_id)
        if building_id is not None:
            query = query.where(Room.building_id == building_id)
        if time_window_start is not None:
            query = query.where(AttendanceEvidence.server_received_at_utc >= time_window_start)
        if time_window_end is not None:
            query = query.where(AttendanceEvidence.server_received_at_utc <= time_window_end)

        result = await db.execute(query)
        rows = result.scalars().all()

        # Extract and parse ble_rssi values
        rssi_values: list[int] = []
        for metadata in rows:
            if isinstance(metadata, dict):
                val = metadata.get("ble_rssi") if "ble_rssi" in metadata else metadata.get("rssi")
                if val is not None:
                    try:
                        rssi_values.append(int(val))
                    except ValueError, TypeError:
                        continue

        if not rssi_values:
            return RadioAnalysisSummary(
                observation_count=0,
                median_rssi=None,
                p10_rssi=None,
                p25_rssi=None,
                p75_rssi=None,
                p90_rssi=None,
                min_rssi=None,
                max_rssi=None,
                building_id=building_id,
                room_id=room_id,
                attendance_session_id=session_id,
                time_window_start=time_window_start,
                time_window_end=time_window_end,
            )

        sorted_values = sorted(rssi_values)
        count = len(sorted_values)
        median_val = calculate_percentile(sorted_values, 50.0)
        p10_val = calculate_percentile(sorted_values, 10.0)
        p25_val = calculate_percentile(sorted_values, 25.0)
        p75_val = calculate_percentile(sorted_values, 75.0)
        p90_val = calculate_percentile(sorted_values, 90.0)
        min_val = sorted_values[0]
        max_val = sorted_values[-1]

        return RadioAnalysisSummary(
            observation_count=count,
            median_rssi=median_val,
            p10_rssi=p10_val,
            p25_rssi=p25_val,
            p75_rssi=p75_val,
            p90_rssi=p90_val,
            min_rssi=min_val,
            max_rssi=max_val,
            building_id=building_id,
            room_id=room_id,
            attendance_session_id=session_id,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
        )
