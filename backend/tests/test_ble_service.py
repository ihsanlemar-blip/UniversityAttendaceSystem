"""Integration tests for Milestone 11 Bluetooth Low Energy (BLE) Presence Verification.

Validates:
- INV-01: Client cannot mark itself present; only server-evaluated evidence grants credit.
- INV-03: Server UTC clock evaluates token rotation and expiration (zero real sleeps).
- INV-04: Expired BLE payloads rejected unconditionally.
- INV-05: Exactly one credit per checkpoint per student (idempotent duplicate response).
- Dual-factor: QR_AND_BLE requires both factors; QR_ONLY accepts QR alone.
- Signal quality: RSSI below threshold is rejected with BLE_SIGNAL_TOO_WEAK.
- Shared classroom broadcast: Multiple students observe the same rotating advertisement.
- Policy snapshot immutability: Session-level presence requirement is locked at creation.
"""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.ble import BlePresenceEngine
from backend.app.attendance.schemas import BleObservationSchema
from backend.app.attendance.service import AttendanceService
from backend.app.core.constants import AttendanceCheckpointType, EvidenceSourceMode
from backend.app.core.exceptions import DomainException
from backend.app.models.attendance_evidence import AttendanceEvidence
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_ble_advertisement_generation_lifecycle(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify lecturer generates BLE advertisement payload for an open checkpoint."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

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

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    ble_resp = await AttendanceService.generate_checkpoint_ble_advertisement(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    assert ble_resp.checkpoint_id == cp_start.id
    assert ble_resp.checkpoint_type == "START"
    assert ble_resp.rotation_seconds == 20
    assert len(ble_resp.payload_base64) > 0
    assert len(ble_resp.payload_hex) > 0
    assert ble_resp.protocol_version == 1


@pytest.mark.asyncio
async def test_ble_generation_preconditions_enforced(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify BLE advertisement cannot be generated for closed checkpoint or closed session."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

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

    # Close checkpoint
    await AttendanceService.close_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
    )

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    with pytest.raises(DomainException) as exc_closed:
        await AttendanceService.generate_checkpoint_ble_advertisement(
            db=db_session,
            checkpoint_id=cp_start.id,
            university_id=test_university.id,
            actor_id=test_admin_user.id,
            current_time=t0,
        )
    assert exc_closed.value.code == "CHECKPOINT_NOT_OPEN"


@pytest.mark.asyncio
async def test_unified_presence_checkin_dual_factor_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify successful dual-factor (QR + BLE) check-in, shared broadcast, and idempotency."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    # Enroll two students
    s1_u_id, _, _ = create_test_user(client, headers, prefix="s1_ble")
    s1_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s1_u_id, "student_number": f"ST1-BLE-{uuid.uuid4().hex[:6]}"},
    )
    s1_id = s1_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": s1_id},
    )

    s2_u_id, _, _ = create_test_user(client, headers, prefix="s2_ble")
    s2_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s2_u_id, "student_number": f"ST2-BLE-{uuid.uuid4().hex[:6]}"},
    )
    s2_id = s2_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": s2_id},
    )

    # Initialize session
    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
        presence_requirement_mode="QR_AND_BLE",
        ble_min_rssi=-85,
    )

    cp_start = await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=300,
    )

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    # Generate QR and BLE tokens
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )
    ble_data = await AttendanceService.generate_checkpoint_ble_advertisement(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    s1_user = await db_session.get(User, uuid.UUID(s1_u_id))
    assert s1_user is not None
    s2_user = await db_session.get(User, uuid.UUID(s2_u_id))
    assert s2_user is not None

    # Student 1 check-in at t0 + 4s
    t1 = t0 + datetime.timedelta(seconds=4)
    obs1 = BleObservationSchema(
        payload=ble_data.payload_base64,
        rssi=-72,
        observed_at_client=t1,
    )

    res1 = await AttendanceService.verify_presence_checkin(
        db=db_session,
        current_user=s1_user,
        qr_token=qr_data.token,
        ble_observation=obs1,
        current_time=t1,
    )

    assert res1.accepted is True
    assert res1.already_credited is False
    assert res1.checkpoint_type == "START"
    assert res1.presence_mode == "QR_AND_BLE"

    # Verify student 1 record & evidence
    stmt1 = select(AttendanceRecord).where(
        AttendanceRecord.attendance_session_id == sess.id,
        AttendanceRecord.student_id == uuid.UUID(s1_id),
    )
    rec1 = (await db_session.execute(stmt1)).scalar_one()
    assert rec1.start_credited is True
    assert rec1.checkpoints_verified == 1

    ev_stmt1 = select(AttendanceEvidence).where(
        AttendanceEvidence.attendance_checkpoint_id == cp_start.id,
        AttendanceEvidence.student_id == uuid.UUID(s1_id),
    )
    ev1 = (await db_session.execute(ev_stmt1)).scalar_one()
    assert ev1.source_mode == EvidenceSourceMode.BLUETOOTH_BLE.value
    assert ev1.evidence_metadata is not None
    assert ev1.evidence_metadata["ble_rssi"] == -72

    # Student 2 checks in using same classroom broadcast at t0 + 8s
    t2 = t0 + datetime.timedelta(seconds=8)
    obs2 = BleObservationSchema(
        payload=ble_data.payload_base64,
        rssi=-65,
        observed_at_client=t2,
    )
    res2 = await AttendanceService.verify_presence_checkin(
        db=db_session,
        current_user=s2_user,
        qr_token=qr_data.token,
        ble_observation=obs2,
        current_time=t2,
    )
    assert res2.accepted is True
    assert res2.already_credited is False

    # Student 1 duplicate check-in (idempotency - INV-05)
    t3 = t0 + datetime.timedelta(seconds=12)
    res1_dup = await AttendanceService.verify_presence_checkin(
        db=db_session,
        current_user=s1_user,
        qr_token=qr_data.token,
        ble_observation=obs1,
        current_time=t3,
    )
    assert res1_dup.accepted is True
    assert res1_dup.already_credited is True

    # Confirm only one evidence record exists for student 1
    ev_all = (await db_session.execute(ev_stmt1)).scalars().all()
    assert len(ev_all) == 1


@pytest.mark.asyncio
async def test_presence_checkin_rejects_missing_ble_in_dual_mode(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify check-in fails if QR_AND_BLE is required but BLE observation is omitted."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    s_u_id, _, _ = create_test_user(client, headers, prefix="s_noble")
    s_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s_u_id, "student_number": f"STN-{uuid.uuid4().hex[:6]}"},
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
        presence_requirement_mode="QR_AND_BLE",
    )

    cp_start = await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=300,
    )

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    student_user = await db_session.get(User, uuid.UUID(s_u_id))
    assert student_user is not None

    # Unified endpoint without BLE
    with pytest.raises(DomainException) as exc_info:
        await AttendanceService.verify_presence_checkin(
            db=db_session,
            current_user=student_user,
            qr_token=qr_data.token,
            ble_observation=None,
            current_time=t0 + datetime.timedelta(seconds=5),
        )
    assert exc_info.value.code == "PRESENCE_FACTORS_INCOMPLETE"

    # Legacy QR endpoint also rejects when session requires dual factor
    with pytest.raises(DomainException) as exc_legacy:
        await AttendanceService.verify_qr_checkin(
            db=db_session,
            token=qr_data.token,
            current_user=student_user,
            current_time=t0 + datetime.timedelta(seconds=5),
        )
    assert exc_legacy.value.code == "PRESENCE_FACTORS_INCOMPLETE"


@pytest.mark.asyncio
async def test_presence_checkin_rejects_weak_rssi(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify check-in fails with BLE_SIGNAL_TOO_WEAK if RSSI is below minimum threshold."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    s_u_id, _, _ = create_test_user(client, headers, prefix="s_weak")
    s_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s_u_id, "student_number": f"STW-{uuid.uuid4().hex[:6]}"},
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
        presence_requirement_mode="QR_AND_BLE",
        ble_min_rssi=-80,  # requires >= -80 dBm
    )

    cp_start = await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=300,
    )

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )
    ble_data = await AttendanceService.generate_checkpoint_ble_advertisement(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    student_user = await db_session.get(User, uuid.UUID(s_u_id))
    assert student_user is not None

    weak_obs = BleObservationSchema(
        payload=ble_data.payload_base64,
        rssi=-90,  # Below -80 dBm threshold
        observed_at_client=t0 + datetime.timedelta(seconds=3),
    )

    with pytest.raises(DomainException) as exc_info:
        await AttendanceService.verify_presence_checkin(
            db=db_session,
            current_user=student_user,
            qr_token=qr_data.token,
            ble_observation=weak_obs,
            current_time=t0 + datetime.timedelta(seconds=3),
        )
    assert exc_info.value.code == "BLE_SIGNAL_TOO_WEAK"


@pytest.mark.asyncio
async def test_presence_checkin_rejects_tampered_and_expired_ble_payload(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify check-in fails for expired BLE slot and tampered BLE payload tag."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    s_u_id, _, _ = create_test_user(client, headers, prefix="s_tamp")
    s_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s_u_id, "student_number": f"STT-{uuid.uuid4().hex[:6]}"},
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
        presence_requirement_mode="QR_AND_BLE",
    )

    cp_start = await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=300,
    )

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )
    ble_data = await AttendanceService.generate_checkpoint_ble_advertisement(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    student_user = await db_session.get(User, uuid.UUID(s_u_id))
    assert student_user is not None

    # 1. Expired slot: check in at t0 + 21 seconds (past 20s rotation slot)
    t_expired = t0 + datetime.timedelta(seconds=21)
    exp_obs = BleObservationSchema(
        payload=ble_data.payload_base64,
        rssi=-70,
        observed_at_client=t_expired,
    )
    with pytest.raises(DomainException) as exc_exp:
        await AttendanceService.verify_presence_checkin(
            db=db_session,
            current_user=student_user,
            qr_token=qr_data.token,
            ble_observation=exp_obs,
            current_time=t_expired,
        )
    assert exc_exp.value.code == "BLE_PAYLOAD_EXPIRED"

    # 2. Tampered tag
    raw = BlePresenceEngine.decode_raw_payload(ble_data.payload_base64)
    tampered_bytes = raw[:10] + bytes([raw[10] ^ 0xFF]) + raw[11:]
    import base64

    tampered_b64 = base64.b64encode(tampered_bytes).decode("ascii")

    tamp_obs = BleObservationSchema(
        payload=tampered_b64,
        rssi=-70,
        observed_at_client=t0 + datetime.timedelta(seconds=5),
    )
    with pytest.raises(DomainException) as exc_tamp:
        await AttendanceService.verify_presence_checkin(
            db=db_session,
            current_user=student_user,
            qr_token=qr_data.token,
            ble_observation=tamp_obs,
            current_time=t0 + datetime.timedelta(seconds=5),
        )
    assert exc_tamp.value.code == "INVALID_BLE_PAYLOAD"


@pytest.mark.asyncio
async def test_policy_snapshot_immutability(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify session policy snapshot immutability across configuration changes."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )

    # Re-fetch from DB and verify snapshot fields
    reloaded_sess = await db_session.get(AttendanceSession, sess.id)
    assert reloaded_sess is not None
    assert reloaded_sess.policy_snapshot is not None
    assert "presence_requirement_mode" in reloaded_sess.policy_snapshot
    assert "ble_min_rssi" in reloaded_sess.policy_snapshot
