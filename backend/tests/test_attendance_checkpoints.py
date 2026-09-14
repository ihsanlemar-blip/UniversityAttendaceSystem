"""Test suite for AttendanceCheckpoint lifecycle, discrete types, sequential rules, and windows."""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.service import AttendanceService
from backend.app.core.exceptions import DomainException
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_attendance_sessions import create_enrolled_student
from backend.tests.test_users import get_admin_headers


def test_approved_three_checkpoints_created_with_session(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify that every attendance session initializes with exactly START, MIDDLE, END
    checkpoints.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["data"]["id"]

    # Retrieve session details
    detail_res = client.get(f"/api/v1/attendance/sessions/{session_id}", headers=headers)
    assert detail_res.status_code == 200
    checkpoints = detail_res.json()["data"]["checkpoints"]

    assert len(checkpoints) == 3
    cp_types = [cp["checkpoint_type"] for cp in checkpoints]
    assert cp_types == ["START", "MIDDLE", "END"]

    for cp in checkpoints:
        assert cp["status"] == "SCHEDULED"
        assert cp["sequence_no"] in (1, 2, 3)
        assert cp["window_duration_seconds"] > 0


def test_reject_non_approved_checkpoint_types(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify non-approved checkpoint types like FIRST_HALF or RANDOM_POP are rejected."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    for invalid_type in ["FIRST_HALF", "SECOND_HALF", "RANDOM_POP", "POPUP_CHECK"]:
        res = client.post(
            f"/api/v1/attendance/sessions/{session_id}/checkpoints/{invalid_type}/open",
            headers=headers,
            json={"window_duration_seconds": 180},
        )
        assert res.status_code == 400
        assert "INVALID_CHECKPOINT_TYPE" in res.text


def test_checkpoint_sequential_opening_and_concurrency_rejection(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify sequential checkpoint lifecycle and rejection of concurrent open checkpoints."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    # 1. Open START checkpoint
    open_start = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/open",
        headers=headers,
        json={"window_duration_seconds": 240},
    )
    assert open_start.status_code == 200
    start_data = open_start.json()["data"]
    assert start_data["status"] == "OPEN"
    assert start_data["opened_at_utc"] is not None
    assert start_data["window_duration_seconds"] == 240

    # 2. Attempt to open MIDDLE while START is still OPEN -> 400 CHECKPOINT_ALREADY_OPEN
    open_middle_fail = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/MIDDLE/open",
        headers=headers,
        json={"window_duration_seconds": 180},
    )
    assert open_middle_fail.status_code == 400
    assert "CHECKPOINT_ALREADY_OPEN" in open_middle_fail.text

    # 3. Close START
    close_start = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/close",
        headers=headers,
    )
    assert close_start.status_code == 200
    assert close_start.json()["data"]["status"] == "CLOSED"
    assert close_start.json()["data"]["closed_at_utc"] is not None

    # 4. Attempt to re-open closed START -> 400 CHECKPOINT_ALREADY_CLOSED
    reopen_start = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/open",
        headers=headers,
        json={},
    )
    assert reopen_start.status_code == 400
    assert "CHECKPOINT_ALREADY_CLOSED" in reopen_start.text

    # 5. Now MIDDLE can be opened successfully
    open_middle = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/MIDDLE/open",
        headers=headers,
        json={},
    )
    assert open_middle.status_code == 200
    assert open_middle.json()["data"]["status"] == "OPEN"


def test_checkpoint_auto_closure_on_session_pause_and_close(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify open checkpoints are auto-closed when session is paused or closed."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    # Open START
    client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/open",
        headers=headers,
        json={},
    )

    # Pause session -> START must be auto-closed
    pause_res = client.post(f"/api/v1/attendance/sessions/{session_id}/pause", headers=headers)
    assert pause_res.status_code == 200

    detail = client.get(f"/api/v1/attendance/sessions/{session_id}", headers=headers).json()["data"]
    start_cp = next(cp for cp in detail["checkpoints"] if cp["checkpoint_type"] == "START")
    assert start_cp["status"] == "CLOSED"
    assert start_cp["closed_at_utc"] is not None

    # Resume session and open MIDDLE
    client.post(f"/api/v1/attendance/sessions/{session_id}/resume", headers=headers)
    open_mid = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/MIDDLE/open",
        headers=headers,
        json={},
    )
    assert open_mid.status_code == 200

    # Close session -> MIDDLE must be auto-closed
    client.post(f"/api/v1/attendance/sessions/{session_id}/close", headers=headers)
    detail2 = client.get(f"/api/v1/attendance/sessions/{session_id}", headers=headers).json()[
        "data"
    ]
    mid_cp = next(cp for cp in detail2["checkpoints"] if cp["checkpoint_type"] == "MIDDLE")
    assert mid_cp["status"] == "CLOSED"
    assert mid_cp["closed_at_utc"] is not None


@pytest.mark.asyncio
async def test_simulated_utc_window_expiration(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify window duration expiration using simulated UTC clock without sleep delays."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)
    student_id = create_enrolled_student(client, headers, offering_id, uuid.uuid4().hex[:6])

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = uuid.UUID(sess_res.json()["data"]["id"])

    # Open START checkpoint with 180s window
    open_res = client.post(
        f"/api/v1/attendance/sessions/{session_id}/checkpoints/START/open",
        headers=headers,
        json={"window_duration_seconds": 180},
    )
    assert open_res.status_code == 200
    opened_at = datetime.datetime.fromisoformat(open_res.json()["data"]["opened_at_utc"])

    # 1. Verification at opened_at + 60s (within window) -> Succeeds
    within_window_time = opened_at + datetime.timedelta(seconds=60)
    evidence = await AttendanceService.record_verified_checkpoint_credit(
        db=db_session,
        session_id=session_id,
        checkpoint_type="START",
        student_id=uuid.UUID(student_id),
        actor_id=test_admin_user.id,
        reason="On-time attendance verified",
        override_now=within_window_time,
    )
    assert evidence is not None

    # Reset record for Student 2 to test expired window
    _, offering2_id, occ2_id = setup_class_occurrence(client, headers)
    s2_id = create_enrolled_student(client, headers, offering2_id, uuid.uuid4().hex[:6])
    sess2_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occ2_id, "activate_immediately": True},
    )
    session2_id = uuid.UUID(sess2_res.json()["data"]["id"])

    open_res2 = client.post(
        f"/api/v1/attendance/sessions/{session2_id}/checkpoints/START/open",
        headers=headers,
        json={"window_duration_seconds": 180},
    )
    opened_at2 = datetime.datetime.fromisoformat(open_res2.json()["data"]["opened_at_utc"])

    # 2. Verification at opened_at + 195s (window expired by 15s)
    # -> Fails with CHECKPOINT_WINDOW_EXPIRED
    expired_time = opened_at2 + datetime.timedelta(seconds=195)
    with pytest.raises(DomainException) as exc_info:
        await AttendanceService.record_verified_checkpoint_credit(
            db=db_session,
            session_id=session2_id,
            checkpoint_type="START",
            student_id=uuid.UUID(s2_id),
            actor_id=test_admin_user.id,
            reason="Late submission after window expired",
            override_now=expired_time,
        )
    assert exc_info.value.code == "CHECKPOINT_WINDOW_EXPIRED"
    assert "expired" in str(exc_info.value)
