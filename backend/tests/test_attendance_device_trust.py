"""Integration tests for Milestone 13 Cryptographic Attendance Binding & Online Presence Proofs."""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.service import AttendanceService
from backend.app.core.config import get_settings
from backend.app.core.constants import AttendanceCheckpointType, DeviceStatus
from backend.app.core.exceptions import DomainException
from backend.app.devices.crypto import (
    build_online_device_proof_payload,
    generate_device_keypair,
    sign_payload_with_private_key,
)
from backend.app.devices.schemas import (
    DeviceProofSchema,
    DeviceRegistrationChallengeRequest,
    DeviceRegistrationConfirmRequest,
)
from backend.app.devices.service import DeviceTrustService
from backend.app.models.attendance_evidence import AttendanceEvidence
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.student import Student
from backend.app.models.trusted_device import TrustedDevice
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


async def _create_enrolled_student_with_device(
    client: TestClient,
    admin_headers: dict[str, str],
    offering_id: str,
    university_id: uuid.UUID,
    db_session: AsyncSession,
    prefix: str,
) -> tuple[User, Student, TrustedDevice, tuple[str, str]]:
    """Helper to create student, enroll in offering, and activate trusted device."""
    u_id, _, _ = create_test_user(client, admin_headers, prefix=prefix)
    user = await db_session.get(User, uuid.UUID(u_id))
    assert user is not None

    student_res = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={"user_id": u_id, "student_number": f"ST-{uuid.uuid4().hex[:8]}"},
    )
    s_id = uuid.UUID(student_res.json()["data"]["id"])
    student = await db_session.get(Student, s_id)
    assert student is not None

    # Enroll in course offering
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=admin_headers,
        json={"student_id": str(s_id)},
    )

    # Register active primary device
    priv_pem, pub_pem = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    ch = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub_pem,
            installation_id=uuid.uuid4(),
            platform="android",
            device_label=f"Pixel-Phone-{prefix}",
            app_version="1.0.0",
        ),
        current_time=t0,
    )
    sig = sign_payload_with_private_key(priv_pem, ch.canonical_challenge.encode("utf-8"))
    dev_dto = await DeviceTrustService.confirm_initial_registration(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationConfirmRequest(challenge_id=ch.challenge_id, signature=sig),
        current_time=t0 + datetime.timedelta(seconds=5),
    )
    device = await db_session.get(TrustedDevice, dev_dto.id)
    assert device is not None
    return user, student, device, (priv_pem, pub_pem)


@pytest.mark.asyncio
async def test_online_qr_checkin_with_device_trust_enabled(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify online QR attendance check-in enforces trusted device proof when enabled."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ATTENDANCE_DEVICE_TRUST_ENABLED", True)

    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    # Setup student with registered device
    user, student, device, (priv_pem, pub_pem) = await _create_enrolled_student_with_device(
        client, admin_headers, offering_id, test_university.id, db_session, "att_dev_ok"
    )

    # Initialize session and open START checkpoint
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

    # Lecturer generates QR token at t0
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    # 1. Check-in WITHOUT device proof must be REJECTED (403 DEVICE_PROOF_REQUIRED)
    t1 = t0 + datetime.timedelta(seconds=5)
    with pytest.raises(DomainException) as exc_missing:
        await AttendanceService.verify_qr_checkin(
            db=db_session,
            token=qr_data.token,
            current_user=user,
            device_proof=None,
            current_time=t1,
        )
    assert exc_missing.value.code == "DEVICE_PROOF_REQUIRED"
    assert exc_missing.value.status_code == 403

    # 2. Check-in with VALID device proof SUCCEEDS
    proof_id = uuid.uuid4()
    canonical_payload = build_online_device_proof_payload(
        user_id=user.id,
        university_id=test_university.id,
        device_id=device.id,
        proof_id=proof_id,
        qr_token=qr_data.token,
        ble_payload=None,
    )
    proof_sig = sign_payload_with_private_key(priv_pem, canonical_payload)
    valid_proof = DeviceProofSchema(
        device_id=device.id,
        proof_id=proof_id,
        signature=proof_sig,
    )

    result = await AttendanceService.verify_qr_checkin(
        db=db_session,
        token=qr_data.token,
        current_user=user,
        device_proof=valid_proof,
        current_time=t1,
    )
    assert result.accepted is True
    assert result.already_credited is False

    # Verify AttendanceRecord credited
    rec_stmt = select(AttendanceRecord).where(
        AttendanceRecord.attendance_session_id == sess.id,
        AttendanceRecord.student_id == student.id,
    )
    rec = (await db_session.execute(rec_stmt)).scalar_one()
    assert rec.start_credited is True

    # Verify AttendanceEvidence metadata contains device trust details
    ev_stmt = select(AttendanceEvidence).where(
        AttendanceEvidence.attendance_checkpoint_id == cp_start.id,
        AttendanceEvidence.student_id == student.id,
    )
    ev = (await db_session.execute(ev_stmt)).scalar_one()
    assert ev.evidence_metadata is not None
    assert ev.evidence_metadata["trusted_device_id"] == str(device.id)
    assert ev.evidence_metadata["device_label"] == device.device_label
    assert ev.evidence_metadata["public_key_fingerprint"] == device.public_key_fingerprint


@pytest.mark.asyncio
async def test_online_qr_checkin_tampered_proof_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify check-in with invalid cryptographic signature or wrong device is rejected."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ATTENDANCE_DEVICE_TRUST_ENABLED", True)

    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (priv_pem, pub_pem) = await _create_enrolled_student_with_device(
        client, admin_headers, offering_id, test_university.id, db_session, "att_dev_tamper"
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
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    # 1. Proof signed by an unauthorized third-party private key
    rogue_priv, _ = generate_device_keypair()
    proof_id = uuid.uuid4()
    canonical_payload = build_online_device_proof_payload(
        user_id=user.id,
        university_id=test_university.id,
        device_id=device.id,
        proof_id=proof_id,
        qr_token=qr_data.token,
    )
    rogue_sig = sign_payload_with_private_key(rogue_priv, canonical_payload)
    bad_sig_proof = DeviceProofSchema(
        device_id=device.id,
        proof_id=proof_id,
        signature=rogue_sig,
    )

    with pytest.raises(DomainException) as exc_bad_sig:
        await AttendanceService.verify_qr_checkin(
            db=db_session,
            token=qr_data.token,
            current_user=user,
            device_proof=bad_sig_proof,
            current_time=t0 + datetime.timedelta(seconds=5),
        )
    assert exc_bad_sig.value.status_code == 403

    # 2. Proof with mismatched device_id
    mismatched_proof = DeviceProofSchema(
        device_id=uuid.uuid4(),  # Different random UUID
        proof_id=proof_id,
        signature=rogue_sig,
    )
    with pytest.raises(DomainException) as exc_mismatch:
        await AttendanceService.verify_qr_checkin(
            db=db_session,
            token=qr_data.token,
            current_user=user,
            device_proof=mismatched_proof,
            current_time=t0 + datetime.timedelta(seconds=5),
        )
    assert exc_mismatch.value.code == "DEVICE_PROOF_INVALID"


@pytest.mark.asyncio
async def test_online_qr_checkin_suspended_device_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify student with suspended device cannot check in."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ATTENDANCE_DEVICE_TRUST_ENABLED", True)

    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (priv_pem, pub_pem) = await _create_enrolled_student_with_device(
        client, admin_headers, offering_id, test_university.id, db_session, "att_dev_susp"
    )

    # Suspend student device
    device.status = DeviceStatus.SUSPENDED.value
    await db_session.commit()

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
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    # Attempt check-in with suspended device
    with pytest.raises(DomainException) as exc_susp:
        await AttendanceService.verify_qr_checkin(
            db=db_session,
            token=qr_data.token,
            current_user=user,
            device_proof=None,
            current_time=t0 + datetime.timedelta(seconds=5),
        )
    # Even looking up the device or requiring proof raises
    assert exc_susp.value.status_code == 403


@pytest.mark.asyncio
async def test_legacy_checkin_allowed_when_device_trust_disabled(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify legacy check-in succeeds when ATTENDANCE_DEVICE_TRUST_ENABLED=False."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ATTENDANCE_DEVICE_TRUST_ENABLED", False)

    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    # Student without any registered device
    u_id, _, _ = create_test_user(client, admin_headers, prefix="legacy_no_dev")
    user = await db_session.get(User, uuid.UUID(u_id))
    assert user is not None

    student_res = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={"user_id": u_id, "student_number": f"ST-{uuid.uuid4().hex[:8]}"},
    )
    s_id = uuid.UUID(student_res.json()["data"]["id"])
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=admin_headers,
        json={"student_id": str(s_id)},
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
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    qr_data = await AttendanceService.generate_checkpoint_qr_token(
        db=db_session,
        checkpoint_id=cp_start.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    # When disabled, no device proof is needed
    res = await AttendanceService.verify_qr_checkin(
        db=db_session,
        token=qr_data.token,
        current_user=user,
        device_proof=None,
        current_time=t0 + datetime.timedelta(seconds=5),
    )
    assert res.accepted is True
