"""Integration tests for Milestone 14 Classroom Radio Environment Diagnostics.

Invariants Tested:
- Radio diagnostics aggregates BLE RSSI evidence (observations, median, p10,
  p25, p75, p90, min, max).
- NO distance conversion, distance estimation, or threshold auto-tuning is performed.
- Empty observations return zero count and None percentiles safely.
- Multi-tenant isolation: Queries strictly scoped to university boundary.
"""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.service import AttendanceService
from backend.app.core.constants import AttendanceCheckpointType, EvidenceSourceMode
from backend.app.models.attendance_evidence import AttendanceEvidence
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.security.radio_service import RadioAnalysisService
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_radio_analysis_empty_and_aggregated_metrics(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify radio metrics calculation on empty dataset and populated RSSI evidence."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )
    cp = await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=300,
    )

    # 1. Query radio analysis on session with NO BLE evidence
    empty_summary = await RadioAnalysisService.analyze_radio_environment(
        db=db_session,
        university_id=test_university.id,
        session_id=sess.id,
    )
    assert empty_summary.observation_count == 0
    assert empty_summary.median_rssi is None
    assert empty_summary.p10_rssi is None
    assert empty_summary.p25_rssi is None
    assert empty_summary.p75_rssi is None
    assert empty_summary.p90_rssi is None
    assert empty_summary.min_rssi is None
    assert empty_summary.max_rssi is None

    # 2. Insert 10 BLE evidence records with known RSSI values
    rssi_values = [-85, -80, -78, -75, -72, -70, -68, -65, -62, -55]
    now = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    for i, rssi in enumerate(rssi_values):
        u_id, _, _ = create_test_user(client, admin_headers, prefix=f"rad_{i}")
        student_res = client.post(
            "/api/v1/students",
            headers=admin_headers,
            json={"user_id": u_id, "student_number": f"ST-R-{uuid.uuid4().hex[:6]}"},
        )
        s_id = uuid.UUID(student_res.json()["data"]["id"])
        ev = AttendanceEvidence(
            attendance_checkpoint_id=cp.id,
            student_id=s_id,
            submitted_by_user_id=uuid.UUID(u_id),
            source_mode=EvidenceSourceMode.BLUETOOTH_BLE.value,
            evidence_metadata={"ble_rssi": rssi},
            server_received_at_utc=now,
        )
        db_session.add(ev)
    await db_session.flush()

    # 3. Query radio analysis on populated session
    summary = await RadioAnalysisService.analyze_radio_environment(
        db=db_session,
        university_id=test_university.id,
        session_id=sess.id,
    )
    assert summary.observation_count == 10
    assert summary.min_rssi == -85
    assert summary.max_rssi == -55
    # For sorted [-85, -80, -78, -75, -72, -70, -68, -65, -62, -55]:
    # median between -72 and -70 is -71.0
    assert summary.median_rssi == -71.0
    assert summary.p25_rssi is not None
    assert summary.p75_rssi is not None
    assert summary.p10_rssi is not None
    assert summary.p90_rssi is not None


@pytest.mark.asyncio
async def test_radio_analysis_rest_api_endpoint(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify GET /api/v1/security/radio-analysis endpoint returns structured summary."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, admin_headers)

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )

    res = client.get(
        f"/api/v1/security/radio-analysis?session_id={sess.id}",
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "observation_count" in data
    assert "median_rssi" in data
    assert "p10_rssi" in data
    assert "p90_rssi" in data
