"""Integration tests for Milestone 10 Dynamic QR Attendance Engine & Service.

Validates:
- INV-01: Client cannot mark itself present; only server-verified tokens grant credit.
- INV-03: University server UTC clock evaluates token rotation and expiration.
- INV-04: Expired tokens rejected unconditionally.
- INV-05: Exactly one credit per checkpoint per student (idempotent duplicate response).
- Classroom shared token: Multiple distinct students can scan the same rotating classroom QR.
- Audit trail & evidence metadata: SHA-256 token hash and ONLINE_DYNAMIC_QR modality.
"""

import datetime
import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.service import AttendanceService
from backend.app.core.constants import AttendanceCheckpointType, EvidenceSourceMode
from backend.app.core.exceptions import DomainException
from backend.app.models.attendance_evidence import AttendanceEvidence
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_qr_token_generation_and_student_checkin_full_lifecycle(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify lecturer generates visual QR token, multiple students check in, and
    duplicates are idempotent.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    # 1. Create two enrolled students
    s1_u_id, _, _ = create_test_user(client, headers, prefix="s1_qr")
    s1_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s1_u_id, "student_number": f"ST1-{uuid.uuid4().hex[:6]}"},
    )
    s1_id = s1_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": s1_id},
    )

    s2_u_id, _, _ = create_test_user(client, headers, prefix="s2_qr")
    s2_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s2_u_id, "student_number": f"ST2-{uuid.uuid4().hex[:6]}"},
    )
    s2_id = s2_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": s2_id},
    )

    # 2. Initialize active attendance session and open START checkpoint
    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )

    cp_start = await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=300,
    )

    # 3. Lecturer generates classroom QR token at authoritative server time t0
    t0 = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    assert qr_data.token is not None
    assert qr_data.checkpoint_id == cp_start.id
    assert qr_data.checkpoint_type == "START"
    assert qr_data.rotation_seconds == 30
    assert qr_data.refresh_after_seconds <= 30

    # 4. Student 1 scans and checks in at t0 + 5 seconds
    s1_user = await db_session.get(User, uuid.UUID(s1_u_id))
    assert s1_user is not None
    t1 = t0 + datetime.timedelta(seconds=5)

    res1 = await AttendanceService.verify_qr_checkin(
        db=db_session,
        token=qr_data.token,
        current_user=s1_user,
        current_time=t1,
    )
    assert res1.accepted is True
    assert res1.already_credited is False
    assert res1.checkpoint_type == "START"

    # Verify Student 1 AttendanceRecord
    stmt1 = select(AttendanceRecord).where(
        AttendanceRecord.attendance_session_id == sess.id,
        AttendanceRecord.student_id == uuid.UUID(s1_id),
    )
    rec1 = (await db_session.execute(stmt1)).scalar_one()
    assert rec1.start_credited is True
    assert rec1.checkpoints_verified == 1

    # 5. Student 2 scans the EXACT SAME classroom QR token at t0 + 10 seconds
    s2_user = await db_session.get(User, uuid.UUID(s2_u_id))
    assert s2_user is not None
    t2 = t0 + datetime.timedelta(seconds=10)

    res2 = await AttendanceService.verify_qr_checkin(
        db=db_session,
        token=qr_data.token,
        current_user=s2_user,
        current_time=t2,
    )
    assert res2.accepted is True
    assert res2.already_credited is False
    assert res2.checkpoint_type == "START"

    stmt2 = select(AttendanceRecord).where(
        AttendanceRecord.attendance_session_id == sess.id,
        AttendanceRecord.student_id == uuid.UUID(s2_id),
    )
    rec2 = (await db_session.execute(stmt2)).scalar_one()
    assert rec2.start_credited is True
    assert rec2.checkpoints_verified == 1

    # 6. Student 1 scans AGAIN (idempotency check / duplicate scan - INV-05)
    t3 = t0 + datetime.timedelta(seconds=15)
    res1_dup = await AttendanceService.verify_qr_checkin(
        db=db_session,
        token=qr_data.token,
        current_user=s1_user,
        current_time=t3,
    )
    assert res1_dup.accepted is True
    assert res1_dup.already_credited is True
    assert res1_dup.checkpoint_type == "START"

    # Verify exactly one evidence record exists for Student 1
    ev_stmt = select(AttendanceEvidence).where(
        AttendanceEvidence.attendance_checkpoint_id == cp_start.id,
        AttendanceEvidence.student_id == uuid.UUID(s1_id),
    )
    ev_records = (await db_session.execute(ev_stmt)).scalars().all()
    assert len(ev_records) == 1
    evidence = ev_records[0]
    assert evidence.source_mode == EvidenceSourceMode.ONLINE_DYNAMIC_QR.value
    expected_hash = hashlib.sha256(qr_data.token.encode("utf-8")).hexdigest()
    assert evidence.evidence_metadata is not None
    assert evidence.evidence_metadata["token_hash"] == expected_hash


@pytest.mark.asyncio
async def test_qr_checkin_expired_token_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify that scanning an expired dynamic token is rejected with QR_TOKEN_EXPIRED."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    s_u_id, _, _ = create_test_user(client, headers, prefix="s_exp")
    s_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s_u_id, "student_number": f"STE-{uuid.uuid4().hex[:6]}"},
    )
    s_id = s_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": s_id},
    )

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )

    cp_start = await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=300,
    )

    # Generate token for 30-second slot [10:00:00 - 10:00:30]
    t0 = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    # Attempt check-in at 10:00:31 (1 second past slot expiration)
    t_expired = t0 + datetime.timedelta(seconds=31)
    student_user = await db_session.get(User, uuid.UUID(s_u_id))
    assert student_user is not None

    with pytest.raises(DomainException) as exc_info:
        await AttendanceService.verify_qr_checkin(
            db=db_session,
            token=qr_data.token,
            current_user=student_user,
            current_time=t_expired,
        )
    assert exc_info.value.code == "QR_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_qr_checkin_unrostered_student_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify that a student not in the session's frozen roster cannot check in."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    # Create unrostered student
    unrostered_u_id, _, _ = create_test_user(client, headers, prefix="unrost")
    client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": unrostered_u_id, "student_number": f"UNR-{uuid.uuid4().hex[:6]}"},
    )

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )

    cp_start = await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=300,
    )

    t0 = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    unrostered_user = await db_session.get(User, uuid.UUID(unrostered_u_id))
    assert unrostered_user is not None

    with pytest.raises(DomainException) as exc_info:
        await AttendanceService.verify_qr_checkin(
            db=db_session,
            token=qr_data.token,
            current_user=unrostered_user,
            current_time=t0 + datetime.timedelta(seconds=5),
        )
    assert exc_info.value.code == "STUDENT_NOT_ROSTERED"


@pytest.mark.asyncio
async def test_qr_checkin_closed_checkpoint_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify check-in against closed checkpoint raises CHECKPOINT_NOT_OPEN."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    s_u_id, _, _ = create_test_user(client, headers, prefix="s_cp_closed")
    s_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s_u_id, "student_number": f"STC-{uuid.uuid4().hex[:6]}"},
    )
    s_id = s_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": s_id},
    )

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )

    cp_start = await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=300,
    )

    t0 = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    # Checkpoint is closed by lecturer
    await AttendanceService.close_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
    )

    student_user = await db_session.get(User, uuid.UUID(s_u_id))
    assert student_user is not None

    with pytest.raises(DomainException) as exc_info:
        await AttendanceService.verify_qr_checkin(
            db=db_session,
            token=qr_data.token,
            current_user=student_user,
            current_time=t0 + datetime.timedelta(seconds=5),
        )
    assert exc_info.value.code == "CHECKPOINT_NOT_OPEN"
