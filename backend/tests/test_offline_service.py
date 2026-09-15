"""Targeted unit and service tests for Milestone 12 Offline Attendance."""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.attendance.offline_crypto import (
    EventChainEngine,
    generate_ed25519_keypair,
    load_ed25519_private_key,
)
from backend.app.attendance.offline_schemas import (
    OfflineHostEventPayload,
    OfflineHostSyncRequest,
    OfflinePermitRequest,
)
from backend.app.attendance.offline_service import OfflineAttendanceService
from backend.app.attendance.service import AttendanceService
from backend.app.core.constants import (
    OfflinePermitStatus,
)
from backend.app.core.exceptions import DomainException
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_offline_verification_keys() -> None:
    """Verify retrieval of backend public verification keys."""
    keys = OfflineAttendanceService.get_verification_keys()
    assert keys.algorithm == "EdDSA"
    assert keys.curve == "Ed25519"
    assert keys.kid == "att-off-k1"
    assert "-----BEGIN PUBLIC KEY-----" in keys.public_key_pem


@pytest.mark.asyncio
async def test_offline_permit_issuance(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify permit issuance creates signed permit with roster and policy digests."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    # Enroll a student
    s1_u_id, _, _ = create_test_user(client, headers, prefix="off_s1")
    s1_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s1_u_id, "student_number": f"ST-OFF-{uuid.uuid4().hex[:6]}"},
    )
    s1_id = s1_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": s1_id},
    )

    # Initialize session
    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )

    _, host_pub_pem = generate_ed25519_keypair()
    req = OfflinePermitRequest(
        attendance_session_id=sess.id,
        temporary_host_public_key=host_pub_pem,
        validity_hours=12,
    )

    permit_resp = await OfflineAttendanceService.issue_offline_permit(
        db=db_session,
        current_user=test_admin_user,
        request=req,
    )

    assert permit_resp.attendance_session_id == sess.id
    assert permit_resp.class_occurrence_id == uuid.UUID(occurrence_id)
    assert permit_resp.status == OfflinePermitStatus.ISSUED.value
    assert len(permit_resp.roster_snapshot_digest) == 64
    assert len(permit_resp.policy_snapshot_digest) == 64
    assert len(permit_resp.signed_permit_token) > 50


@pytest.mark.asyncio
async def test_offline_host_events_sync_and_tamper_rejection(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify host events sync accepts valid hash chain and rejects tampered chain."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

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

    host_session_id = uuid.uuid4()
    t0 = datetime.datetime(2026, 9, 15, 9, 0, 0, tzinfo=datetime.UTC)

    # Construct event chain
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
                payload=payload,
                signature=sig,
                occurred_at_utc=occ_iso,
            )
        )
        prev_hash = ev_hash

    # 1. Valid sync
    batch_id_1 = f"batch_host_{uuid.uuid4().hex[:8]}"
    idem_key_1 = f"idem_host_{uuid.uuid4().hex[:8]}"
    sync_req = OfflineHostSyncRequest(
        client_batch_id=batch_id_1,
        idempotency_key=idem_key_1,
        permit_id=permit_resp.permit_id,
        host_session_id=host_session_id,
        host_device_id="device_lecturer_1",
        clock_anchor_server_utc=t0,
        clock_anchor_uptime_ms=10000,
        started_at_utc=t0,
        ended_at_utc=t0 + datetime.timedelta(minutes=15),
        final_event_hash=prev_hash,
        events=events,
    )

    resp = await OfflineAttendanceService.sync_host_events(
        db=db_session,
        current_user=test_admin_user,
        payload=sync_req,
        current_time=t0 + datetime.timedelta(hours=1),
    )
    assert resp.status == "SUCCESS"
    assert resp.events_ingested == 3

    # 2. Idempotent re-sync
    resp2 = await OfflineAttendanceService.sync_host_events(
        db=db_session,
        current_user=test_admin_user,
        payload=sync_req,
    )
    assert resp2.status == "ALREADY_PROCESSED"

    # 3. Tampered sync rejection
    tampered_events = [OfflineHostEventPayload(**ev.model_dump()) for ev in events]
    tampered_events[1].payload = {"cpt": "TAMPERED"}
    tampered_req = OfflineHostSyncRequest(
        client_batch_id=f"batch_host_{uuid.uuid4().hex[:8]}",
        idempotency_key=f"idem_host_{uuid.uuid4().hex[:8]}",
        permit_id=permit_resp.permit_id,
        host_session_id=uuid.uuid4(),
        host_device_id="device_lecturer_1",
        clock_anchor_server_utc=t0,
        clock_anchor_uptime_ms=10000,
        started_at_utc=t0,
        events=tampered_events,
    )

    with pytest.raises(DomainException, match="Event chain validation failed"):
        await OfflineAttendanceService.sync_host_events(
            db=db_session,
            current_user=test_admin_user,
            payload=tampered_req,
        )
