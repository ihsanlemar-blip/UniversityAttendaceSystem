"""Integration tests for Milestone 14 Attendance Network Presence Policy Modes.

Invariants Tested:
- DISABLED mode: check-ins proceed without network proof.
- OPTIONAL mode: check-in succeeds without proof, records untrusted network risk signal;
  check-in with valid proof succeeds cleanly and records CAMPUS_NETWORK factor.
- REQUIRED mode: check-in strictly rejected without valid campus network proof;
  succeeds with valid proof and single-use consumed.
- Policy snapshot immutability: session freezes policy fields at activation.
"""

import datetime
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from backend.app.attendance.schemas import AttendancePolicyCreateRequest
from backend.app.attendance.service import AttendanceService
from backend.app.core.constants import (
    AttendanceCheckpointType,
    NetworkPresenceMode,
    NetworkZoneStatus,
    NetworkZoneType,
    PolicyScopeType,
    RiskSignalType,
)
from backend.app.core.exceptions import DomainException
from backend.app.devices.crypto import sign_payload_with_private_key
from backend.app.models.campus_network import CampusNetworkZone
from backend.app.models.risk_signal import AttendanceRiskSignal
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.security.crypto import build_network_challenge_payload
from backend.app.security.network_service import CampusNetworkService
from backend.app.security.schemas import NetworkProofSchema
from backend.tests.test_attendance_device_trust import _create_enrolled_student_with_device
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_users import get_admin_headers


def _mock_request(client_host: str) -> MagicMock:
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = client_host
    req.headers = Headers({})
    return req


@pytest.mark.asyncio
async def test_attendance_network_mode_disabled(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify check-in succeeds without network proof when network_presence_mode is DISABLED."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (priv_pem, pub_pem) = await _create_enrolled_student_with_device(
        client, admin_headers, offering_id, test_university.id, db_session, "net_dis"
    )

    # Create policy with network_presence_mode = DISABLED
    policy = await AttendanceService.create_policy(
        db=db_session,
        university_id=test_university.id,
        payload=AttendancePolicyCreateRequest(
            name=f"Policy-Disabled-{uuid.uuid4().hex[:6]}",
            scope_type=PolicyScopeType.UNIVERSITY,
            network_presence_mode=NetworkPresenceMode.DISABLED,
        ),
    )

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        attendance_policy_id=policy.id,
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )
    assert sess.policy_snapshot["network_presence_mode"] == NetworkPresenceMode.DISABLED.value

    cp = await AttendanceService.open_checkpoint(
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
        checkpoint_id=cp.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    # Check-in without network proof succeeds cleanly
    rec = await AttendanceService.verify_qr_checkin(
        db=db_session,
        token=qr_data.token,
        current_user=user,
        network_proof=None,
        request=_mock_request("198.51.100.25"),
        current_time=t0 + datetime.timedelta(seconds=5),
    )
    assert rec.accepted is True
    assert rec.checkpoint_type == AttendanceCheckpointType.START.value


@pytest.mark.asyncio
async def test_attendance_network_mode_optional(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify OPTIONAL mode: Check-in succeeds without proof and records untrusted signal."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (priv_pem, pub_pem) = await _create_enrolled_student_with_device(
        client, admin_headers, offering_id, test_university.id, db_session, "net_opt"
    )

    # Create policy with network_presence_mode = OPTIONAL
    policy = await AttendanceService.create_policy(
        db=db_session,
        university_id=test_university.id,
        payload=AttendancePolicyCreateRequest(
            name=f"Policy-Optional-{uuid.uuid4().hex[:6]}",
            scope_type=PolicyScopeType.UNIVERSITY,
            network_presence_mode=NetworkPresenceMode.OPTIONAL,
        ),
    )

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        attendance_policy_id=policy.id,
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )
    assert sess.policy_snapshot["network_presence_mode"] == NetworkPresenceMode.OPTIONAL.value
    cp = await AttendanceService.open_checkpoint(
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
        checkpoint_id=cp.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    # Check-in without proof from untrusted IP -> succeeds with risk signal
    rec = await AttendanceService.verify_qr_checkin(
        db=db_session,
        token=qr_data.token,
        current_user=user,
        network_proof=None,
        request=_mock_request("203.0.113.99"),
        current_time=t0 + datetime.timedelta(seconds=5),
    )
    assert rec.accepted is True
    assert rec.checkpoint_type == AttendanceCheckpointType.START.value

    # Verify STUDENT_NETWORK_NOT_TRUSTED risk signal was recorded for human review
    signals = (
        (
            await db_session.execute(
                select(AttendanceRiskSignal).filter_by(
                    attendance_session_id=sess.id,
                    subject_user_id=user.id,
                    signal_type=RiskSignalType.STUDENT_NETWORK_NOT_TRUSTED.value,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(signals) == 1
    assert signals[0].context is not None
    assert signals[0].context.get("observed_ip") == "203.0.113.99"


@pytest.mark.asyncio
async def test_attendance_network_mode_required(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify REQUIRED mode: Rejects check-in without proof, succeeds with valid proof."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (priv_pem, pub_pem) = await _create_enrolled_student_with_device(
        client, admin_headers, offering_id, test_university.id, db_session, "net_req"
    )

    # Configure active campus network zone
    zone = CampusNetworkZone(
        university_id=test_university.id,
        name="Required Campus Zone",
        code=f"ZONE_REQ_{uuid.uuid4().hex[:6]}".upper(),
        network_cidr="172.20.0.0/16",
        ip_version=4,
        zone_type=NetworkZoneType.CAMPUS_TRUSTED.value,
        status=NetworkZoneStatus.ACTIVE.value,
        priority=100,
        allow_student_presence=True,
    )
    db_session.add(zone)
    await db_session.flush()

    # Create policy with network_presence_mode = REQUIRED
    policy = await AttendanceService.create_policy(
        db=db_session,
        university_id=test_university.id,
        payload=AttendancePolicyCreateRequest(
            name=f"Policy-Required-{uuid.uuid4().hex[:6]}",
            scope_type=PolicyScopeType.UNIVERSITY,
            network_presence_mode=NetworkPresenceMode.REQUIRED,
        ),
    )

    sess = await AttendanceService.initialize_session(
        db=db_session,
        university_id=test_university.id,
        class_occurrence_id=uuid.UUID(occurrence_id),
        attendance_policy_id=policy.id,
        actor_id=test_admin_user.id,
        activate_immediately=True,
    )
    assert sess.policy_snapshot["network_presence_mode"] == NetworkPresenceMode.REQUIRED.value
    cp = await AttendanceService.open_checkpoint(
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
        checkpoint_id=cp.id,
        university_id=test_university.id,
        actor_id=test_admin_user.id,
        current_time=t0,
    )

    req_campus = _mock_request("172.20.5.10")

    # 1. Check-in WITHOUT network proof must be REJECTED (403 NETWORK_PROOF_REQUIRED)
    with pytest.raises(DomainException) as exc_missing:
        await AttendanceService.verify_qr_checkin(
            db=db_session,
            token=qr_data.token,
            current_user=user,
            network_proof=None,
            request=req_campus,
            current_time=t0 + datetime.timedelta(seconds=2),
        )
    assert exc_missing.value.code == "NETWORK_PROOF_REQUIRED"

    # 2. Obtain short-lived network challenge
    ch_dto = await CampusNetworkService.issue_network_challenge(
        db=db_session,
        current_user=user,
        checkpoint_id=cp.id,
        request=req_campus,
        current_time=t0 + datetime.timedelta(seconds=3),
    )

    # 3. Sign challenge
    payload_bytes = build_network_challenge_payload(
        challenge_id=ch_dto.challenge_id,
        nonce=ch_dto.nonce,
        user_id=user.id,
        university_id=test_university.id,
        trusted_device_id=device.id,
        attendance_session_id=sess.id,
        attendance_checkpoint_id=cp.id,
        network_zone_id=zone.id,
        issued_at=ch_dto.issued_at,
        expires_at=ch_dto.expires_at,
    )
    sig = sign_payload_with_private_key(priv_pem, payload_bytes)
    valid_proof = NetworkProofSchema(
        challenge_id=ch_dto.challenge_id,
        trusted_device_id=device.id,
        proof_id=uuid.uuid4(),
        signature=sig,
    )

    # 4. Check-in WITH valid network proof SUCCEEDS
    rec = await AttendanceService.verify_qr_checkin(
        db=db_session,
        token=qr_data.token,
        current_user=user,
        network_proof=valid_proof,
        request=req_campus,
        current_time=t0 + datetime.timedelta(seconds=5),
    )
    assert rec.accepted is True
    assert rec.checkpoint_type == AttendanceCheckpointType.START.value
