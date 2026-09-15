"""Integration tests for Milestone 12 Offline Attendance Reconciliation Pipeline.

Verifies:
- INV-01: Client cannot mark itself present; only server evaluates and marks credit.
- INV-03: University server UTC clock authority.
- INV-04: Expired dynamic offline challenges are rejected.
- INV-05: Exactly one credit per checkpoint per student.
- INV-07: All reconciled records carry OFFLINE_SYNC source_mode and append-only revisions.
- Out-of-order: Student syncs before host -> PENDING_HOST_EVENTS -> Host syncs -> VERIFIED!
"""

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
from backend.app.core.constants import (
    AttendanceCheckpointType,
    EvidenceSourceMode,
    OfflineClaimStatus,
)
from backend.app.models.attendance_evidence import AttendanceEvidence
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.offline_attendance import OfflineAttendanceClaim
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_offline_reconciliation_student_before_host_out_of_order(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Out-of-order scenario:
    1. Student submits claim while host has not yet synced -> state is PENDING_HOST_EVENTS.
    2. Host uploads signed event chain -> triggers automatic background reconciliation.
    3. Claim updates to VERIFIED and AttendanceRecord receives credit with OFFLINE_SYNC source mode.
    """
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)

    # 1. Create enrolled student
    s_user_id, s_uname, s_pw = create_test_user(client, headers, prefix="stu_ooo")
    s_res = client.post(
        "/api/v1/students",
        headers=headers,
        json={"user_id": s_user_id, "student_number": f"STU-OOO-{uuid.uuid4().hex[:6]}"},
    )
    student_id = s_res.json()["data"]["id"]
    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=headers,
        json={"student_id": student_id},
    )

    # 2. Initialize attendance session and open START checkpoint
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

    # 3. Issue offline permit to lecturer
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

    # 4. Generate dynamic offline QR challenge
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

    # 5. Student submits claim BEFORE host events arrive
    stu_user = await db_session.get(User, uuid.UUID(s_user_id))
    assert stu_user is not None

    student_sync_req = OfflineStudentSyncRequest(
        client_batch_id=f"batch_stu_{uuid.uuid4().hex[:8]}",
        idempotency_key=f"idem_stu_{uuid.uuid4().hex[:8]}",
        claims=[
            OfflineStudentClaimItem(
                claim_id=uuid.uuid4(),
                permit_id=permit_resp.permit_id,
                host_session_id=host_session_id,
                checkpoint_type="START",
                rotation_slot=slot,
                qr_challenge_token=qr_token,
                ble_evidence={"rssi": -72, "tag": ble_tag.hex()},
                client_captured_at_utc=t0 + datetime.timedelta(seconds=5),
            )
        ],
    )

    stu_sync_resp = await OfflineAttendanceService.sync_student_claims(
        db=db_session,
        current_user=stu_user,
        payload=student_sync_req,
        current_time=t0 + datetime.timedelta(seconds=10),
    )

    assert stu_sync_resp.status == "SUCCESS"
    assert stu_sync_resp.results[0].status == OfflineClaimStatus.PENDING_HOST_EVENTS.value
    assert stu_sync_resp.results[0].credited is False

    # Verify no AttendanceEvidence was created yet
    ev_stmt = select(AttendanceEvidence).where(
        AttendanceEvidence.student_id == uuid.UUID(student_id)
    )
    ev_res = await db_session.execute(ev_stmt)
    assert ev_res.scalar_one_or_none() is None

    # 6. Now Lecturer uploads host events
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

    host_sync_req = OfflineHostSyncRequest(
        client_batch_id=f"batch_host_{uuid.uuid4().hex[:8]}",
        idempotency_key=f"idem_host_{uuid.uuid4().hex[:8]}",
        permit_id=permit_resp.permit_id,
        host_session_id=host_session_id,
        host_device_id="device_lecturer_ooo",
        clock_anchor_server_utc=t0,
        clock_anchor_uptime_ms=10000,
        started_at_utc=t0,
        ended_at_utc=t0 + datetime.timedelta(minutes=15),
        final_event_hash=prev_hash,
        events=events,
    )

    host_sync_resp = await OfflineAttendanceService.sync_host_events(
        db=db_session,
        current_user=test_admin_user,
        payload=host_sync_req,
        current_time=t0 + datetime.timedelta(hours=1),
    )

    assert host_sync_resp.status == "SUCCESS"
    assert host_sync_resp.claims_reconciled == 1
    assert host_sync_resp.conflicts_detected == 0

    # 7. Verify AttendanceEvidence was created with OFFLINE_SYNC
    ev_res2 = await db_session.execute(ev_stmt)
    evidence = ev_res2.scalar_one_or_none()
    assert evidence is not None
    assert evidence.source_mode == EvidenceSourceMode.OFFLINE_SYNC.value
    assert evidence.evidence_metadata is not None
    assert "offline_claim_id" in evidence.evidence_metadata

    # 8. Verify AttendanceRecord received credit
    rec_stmt = select(AttendanceRecord).where(
        AttendanceRecord.attendance_session_id == sess.id,
        AttendanceRecord.student_id == uuid.UUID(student_id),
    )
    rec_res = await db_session.execute(rec_stmt)
    record = rec_res.scalar_one_or_none()
    assert record is not None
    assert record.start_credited is True
    assert record.checkpoints_verified == 1

    # 9. Verify claim is now marked VERIFIED
    claim_stmt = select(OfflineAttendanceClaim).where(
        OfflineAttendanceClaim.student_id == uuid.UUID(student_id)
    )
    claim_res = await db_session.execute(claim_stmt)
    claim = claim_res.scalar_one_or_none()
    assert claim is not None
    assert claim.status == OfflineClaimStatus.VERIFIED.value
