"""Integration tests for Milestone 13 Offline Attendance Device Trust Semantics."""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.offline_crypto import (
    EventChainEngine,
    OfflineChallengeEngine,
    generate_ed25519_keypair,
    load_ed25519_private_key,
)
from backend.app.attendance.offline_schemas import (
    OfflineHostEventPayload,
    OfflineHostSyncRequest,
    OfflinePermitRequest,
    OfflineStudentClaimItem,
    OfflineStudentSyncRequest,
)
from backend.app.attendance.offline_service import OfflineAttendanceService
from backend.app.attendance.service import AttendanceService
from backend.app.core.config import get_settings
from backend.app.core.constants import (
    AttendanceCheckpointType,
    OfflineClaimStatus,
)
from backend.app.devices.crypto import (
    build_offline_device_proof_payload,
    sign_payload_with_private_key,
)
from backend.app.devices.crypto import (
    generate_device_keypair as generate_trusted_device_keypair,
)
from backend.app.devices.schemas import (
    DeviceRegistrationChallengeRequest,
    DeviceRegistrationConfirmRequest,
)
from backend.app.devices.service import DeviceTrustService
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.student import Student
from backend.app.models.trusted_device import TrustedDevice
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


async def _create_enrolled_student_with_trusted_device(
    client: TestClient,
    admin_headers: dict[str, str],
    offering_id: str,
    university_id: uuid.UUID,
    db_session: AsyncSession,
    prefix: str,
) -> tuple[User, Student, TrustedDevice, tuple[str, str]]:
    """Helper to create student, enroll in offering, and register trusted device."""
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

    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=admin_headers,
        json={"student_id": str(s_id)},
    )

    priv_pem, pub_pem = generate_trusted_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 8, 0, 0, tzinfo=datetime.UTC)

    ch = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub_pem,
            installation_id=uuid.uuid4(),
            platform="android",
            device_label=f"Phone-{prefix}",
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
async def test_offline_claim_with_device_signature_credited(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify offline claim signed by active trusted device reconciles and gets credited."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ATTENDANCE_DEVICE_TRUST_ENABLED", True)

    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (dev_priv, dev_pub) = await _create_enrolled_student_with_trusted_device(
        client, admin_headers, offering_id, test_university.id, db_session, "off_dev_ok"
    )

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )
    await AttendanceService.open_checkpoint(
        db=db_session,
        session_id=sess.id,
        checkpoint_type=AttendanceCheckpointType.START.value,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        window_duration_seconds=600,
    )

    # Issue offline permit
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()
    host_priv = load_ed25519_private_key(host_priv_pem)
    permit_resp = await OfflineAttendanceService.issue_offline_permit(
        db=db_session,
        current_user=test_admin_user,
        request=OfflinePermitRequest(
            attendance_session_id=sess.id,
            temporary_host_public_key=host_pub_pem,
            validity_hours=12,
        ),
    )

    # Lecturer broadcasts dynamic offline challenge at t0
    host_session_id = uuid.uuid4()
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    qr_token, slot, _, _, ble_tag = OfflineChallengeEngine.generate_challenge(
        permit_id=permit_resp.permit_id,
        host_session_id=host_session_id,
        checkpoint_type="START",
        host_private_key=host_priv,
        current_time=t0,
        rotation_seconds=20,
    )

    # Student constructs offline claim signed by primary device
    claim_id = uuid.uuid4()
    claim_captured_at = t0 + datetime.timedelta(seconds=5)
    canonical_bytes = build_offline_device_proof_payload(
        user_id=user.id,
        university_id=test_university.id,
        device_id=device.id,
        claim_id=claim_id,
        permit_id=permit_resp.permit_id,
        authority_epoch=permit_resp.authority_epoch,
        host_session_id=host_session_id,
        checkpoint_type="START",
        qr_challenge_token=qr_token,
        ble_payload=None,
    )
    device_sig = sign_payload_with_private_key(dev_priv, canonical_bytes)

    claim_item = OfflineStudentClaimItem(
        claim_id=claim_id,
        permit_id=permit_resp.permit_id,
        host_session_id=host_session_id,
        checkpoint_type="START",
        rotation_slot=slot,
        qr_challenge_token=qr_token,
        client_captured_at_utc=claim_captured_at,
        trusted_device_id=device.id,
        device_proof_signature=device_sig,
    )

    # 1. Student submits claim
    stu_sync_resp = await OfflineAttendanceService.sync_student_claims(
        db=db_session,
        current_user=user,
        payload=OfflineStudentSyncRequest(
            client_batch_id=f"batch_{uuid.uuid4().hex[:8]}",
            idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
            claims=[claim_item],
        ),
        current_time=t0 + datetime.timedelta(seconds=10),
    )
    assert stu_sync_resp.status == "SUCCESS"
    assert stu_sync_resp.results[0].status == OfflineClaimStatus.PENDING_HOST_EVENTS.value

    # 2. Host uploads events triggering reconciliation
    events = []
    prev_hash = EventChainEngine.GENESIS_PREV_HASH
    for seq, ev_type in enumerate(["SESSION_START", "CHECKPOINT_OPEN", "SESSION_END"]):
        occ_iso = (t0 + datetime.timedelta(minutes=seq * 5)).isoformat()
        payload = {"cpt": "START" if ev_type == "CHECKPOINT_OPEN" else None}
        ev_hash = EventChainEngine.compute_event_hash(
            prev_event_hash=prev_hash,
            sequence_number=seq,
            event_type=ev_type,
            payload=payload,
            occurred_at_iso=occ_iso,
        )
        sig = EventChainEngine.sign_event_hash(ev_hash, host_priv)
        events.append(
            OfflineHostEventPayload(
                sequence_number=seq,
                event_type=ev_type,
                prev_event_hash=prev_hash,
                event_hash=ev_hash,
                signature=sig,
                occurred_at_utc=occ_iso,
                payload=payload,
            )
        )
        prev_hash = ev_hash

    host_sync_resp = await OfflineAttendanceService.sync_host_events(
        db=db_session,
        current_user=test_admin_user,
        payload=OfflineHostSyncRequest(
            client_batch_id=f"batch_host_{uuid.uuid4().hex[:8]}",
            idempotency_key=f"idem_host_{uuid.uuid4().hex[:8]}",
            permit_id=permit_resp.permit_id,
            host_session_id=host_session_id,
            host_device_id="lecturer_tablet",
            clock_anchor_server_utc=t0,
            clock_anchor_uptime_ms=50_000,
            started_at_utc=t0,
            ended_at_utc=t0 + datetime.timedelta(minutes=15),
            final_event_hash=prev_hash,
            events=events,
        ),
        current_time=t0 + datetime.timedelta(minutes=20),
    )
    assert host_sync_resp.claims_reconciled == 1

    # Verify student AttendanceRecord credited
    rec_stmt = select(AttendanceRecord).where(
        AttendanceRecord.attendance_session_id == sess.id,
        AttendanceRecord.student_id == student.id,
    )
    rec = (await db_session.execute(rec_stmt)).scalar_one()
    assert rec.start_credited is True


@pytest.mark.asyncio
async def test_offline_claim_invalid_signature_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify offline claim with invalid cryptographic device signature is rejected."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ATTENDANCE_DEVICE_TRUST_ENABLED", True)

    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (dev_priv, dev_pub) = await _create_enrolled_student_with_trusted_device(
        client, admin_headers, offering_id, test_university.id, db_session, "off_dev_bad_sig"
    )

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()
    host_priv = load_ed25519_private_key(host_priv_pem)
    permit_resp = await OfflineAttendanceService.issue_offline_permit(
        db=db_session,
        current_user=test_admin_user,
        request=OfflinePermitRequest(
            attendance_session_id=sess.id,
            temporary_host_public_key=host_pub_pem,
        ),
    )

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    host_session_id = uuid.uuid4()
    qr_token, slot, _, _, _ = OfflineChallengeEngine.generate_challenge(
        permit_id=permit_resp.permit_id,
        host_session_id=host_session_id,
        checkpoint_type="START",
        host_private_key=host_priv,
        current_time=t0,
        rotation_seconds=20,
    )

    # Sign claim with wrong/foreign private key
    foreign_priv, _ = generate_trusted_device_keypair()
    claim_id = uuid.uuid4()
    canonical_bytes = build_offline_device_proof_payload(
        user_id=user.id,
        university_id=test_university.id,
        device_id=device.id,
        claim_id=claim_id,
        permit_id=permit_resp.permit_id,
        authority_epoch=permit_resp.authority_epoch,
        host_session_id=host_session_id,
        checkpoint_type="START",
        qr_challenge_token=qr_token,
    )
    bad_sig = sign_payload_with_private_key(foreign_priv, canonical_bytes)

    claim_item = OfflineStudentClaimItem(
        claim_id=claim_id,
        permit_id=permit_resp.permit_id,
        host_session_id=host_session_id,
        checkpoint_type="START",
        rotation_slot=slot,
        qr_challenge_token=qr_token,
        client_captured_at_utc=t0,
        trusted_device_id=device.id,
        device_proof_signature=bad_sig,
    )

    stu_sync_resp = await OfflineAttendanceService.sync_student_claims(
        db=db_session,
        current_user=user,
        payload=OfflineStudentSyncRequest(
            client_batch_id=f"batch_{uuid.uuid4().hex[:8]}",
            idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
            claims=[claim_item],
        ),
        current_time=t0 + datetime.timedelta(seconds=10),
    )

    assert stu_sync_resp.results[0].status == OfflineClaimStatus.REJECTED.value
    assert (
        stu_sync_resp.results[0].rejection_reason == "Invalid device cryptographic proof signature."
    )


@pytest.mark.asyncio
async def test_offline_claim_active_at_claim_time_semantics(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify active-at-claim-time semantics:
    - Claim captured while device was ACTIVE is accepted even if device is replaced later.
    - Claim captured AFTER device was revoked is rejected.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "ATTENDANCE_DEVICE_TRUST_ENABLED", True)

    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (dev_priv, dev_pub) = await _create_enrolled_student_with_trusted_device(
        client, admin_headers, offering_id, test_university.id, db_session, "off_active_time"
    )

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()
    host_priv = load_ed25519_private_key(host_priv_pem)
    permit_resp = await OfflineAttendanceService.issue_offline_permit(
        db=db_session,
        current_user=test_admin_user,
        request=OfflinePermitRequest(
            attendance_session_id=sess.id,
            temporary_host_public_key=host_pub_pem,
        ),
    )

    t_claim = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    host_session_id = uuid.uuid4()
    qr_token, slot, _, _, _ = OfflineChallengeEngine.generate_challenge(
        permit_id=permit_resp.permit_id,
        host_session_id=host_session_id,
        checkpoint_type="START",
        host_private_key=host_priv,
        current_time=t_claim,
        rotation_seconds=20,
    )

    # 1. Device is revoked BEFORE the claim was captured (e.g. revoked at 09:50)
    device.revoked_at = t_claim - datetime.timedelta(minutes=10)
    await db_session.commit()

    claim_id1 = uuid.uuid4()
    canonical_bytes1 = build_offline_device_proof_payload(
        user_id=user.id,
        university_id=test_university.id,
        device_id=device.id,
        claim_id=claim_id1,
        permit_id=permit_resp.permit_id,
        authority_epoch=permit_resp.authority_epoch,
        host_session_id=host_session_id,
        checkpoint_type="START",
        qr_challenge_token=qr_token,
    )
    sig1 = sign_payload_with_private_key(dev_priv, canonical_bytes1)

    claim_item_revoked = OfflineStudentClaimItem(
        claim_id=claim_id1,
        permit_id=permit_resp.permit_id,
        host_session_id=host_session_id,
        checkpoint_type="START",
        rotation_slot=slot,
        qr_challenge_token=qr_token,
        client_captured_at_utc=t_claim,
        trusted_device_id=device.id,
        device_proof_signature=sig1,
    )

    resp1 = await OfflineAttendanceService.sync_student_claims(
        db=db_session,
        current_user=user,
        payload=OfflineStudentSyncRequest(
            client_batch_id=f"batch_{uuid.uuid4().hex[:8]}",
            idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
            claims=[claim_item_revoked],
        ),
        current_time=t_claim + datetime.timedelta(minutes=5),
    )
    assert resp1.results[0].status == OfflineClaimStatus.REJECTED.value
    assert resp1.results[0].rejection_reason == "Device was revoked prior to offline claim capture."

    # 2. Device replaced AFTER claim was captured (captured 10:00, replaced 11:00)
    (
        user2,
        student2,
        device2,
        (dev_priv2, dev_pub2),
    ) = await _create_enrolled_student_with_trusted_device(
        client, admin_headers, offering_id, test_university.id, db_session, "off_repl_later"
    )
    device2.replaced_at = t_claim + datetime.timedelta(hours=1)
    await db_session.commit()

    claim_id2 = uuid.uuid4()
    canonical_bytes2 = build_offline_device_proof_payload(
        user_id=user2.id,
        university_id=test_university.id,
        device_id=device2.id,
        claim_id=claim_id2,
        permit_id=permit_resp.permit_id,
        authority_epoch=permit_resp.authority_epoch,
        host_session_id=host_session_id,
        checkpoint_type="START",
        qr_challenge_token=qr_token,
    )
    sig2 = sign_payload_with_private_key(dev_priv2, canonical_bytes2)

    claim_item_replaced_later = OfflineStudentClaimItem(
        claim_id=claim_id2,
        permit_id=permit_resp.permit_id,
        host_session_id=host_session_id,
        checkpoint_type="START",
        rotation_slot=slot,
        qr_challenge_token=qr_token,
        client_captured_at_utc=t_claim,
        trusted_device_id=device2.id,
        device_proof_signature=sig2,
    )

    resp2 = await OfflineAttendanceService.sync_student_claims(
        db=db_session,
        current_user=user2,
        payload=OfflineStudentSyncRequest(
            client_batch_id=f"batch_{uuid.uuid4().hex[:8]}",
            idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
            claims=[claim_item_replaced_later],
        ),
        current_time=t_claim + datetime.timedelta(hours=2),
    )
    # Claim is accepted into PENDING_HOST_EVENTS because device was active when captured
    assert resp2.results[0].status == OfflineClaimStatus.PENDING_HOST_EVENTS.value
