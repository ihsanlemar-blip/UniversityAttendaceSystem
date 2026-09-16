"""Integration tests for Milestone 14 Campus Network Challenge & Cryptographic Proof Verification.

Invariants Tested:
- Short-lived network challenge (20s TTL) strictly enforced.
- Challenge bound to student, registered M13 device, session, checkpoint, and zone.
- Canonical payload signed with student's registered Ed25519 key.
- Single-use consumption: Replay attempts with different proof_id rejected.
- HTTP idempotent retry: Same proof_id retry allowed.
- Revalidation of source IP on final submission: Submitting from outside the zone rejected.
"""

import datetime
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from backend.app.attendance.service import AttendanceService
from backend.app.core.constants import AttendanceCheckpointType, NetworkZoneStatus, NetworkZoneType
from backend.app.core.exceptions import DomainException
from backend.app.devices.crypto import sign_payload_with_private_key
from backend.app.models.campus_network import CampusNetworkZone
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
async def test_network_challenge_issuance_and_single_use(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify challenge issuance (20s TTL), Ed25519 signing, single-use, and replay rejection."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    # 1. Create enrolled student with active M13 trusted device
    user, student, device, (priv_pem, pub_pem) = await _create_enrolled_student_with_device(
        client, admin_headers, offering_id, test_university.id, db_session, "net_p_1"
    )

    # 2. Configure campus network zone
    zone = CampusNetworkZone(
        university_id=test_university.id,
        name="Main Campus Wi-Fi",
        code=f"ZONE_MC_{uuid.uuid4().hex[:6]}".upper(),
        network_cidr="192.168.10.0/24",
        ip_version=4,
        zone_type=NetworkZoneType.CAMPUS_TRUSTED.value,
        status=NetworkZoneStatus.ACTIVE.value,
        priority=100,
        allow_student_presence=True,
    )
    db_session.add(zone)
    await db_session.flush()

    # 3. Initialize attendance session and open START checkpoint
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

    # 4. Issue network challenge at t0 from campus IP
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    req_campus = _mock_request("192.168.10.45")

    ch_dto = await CampusNetworkService.issue_network_challenge(
        db=db_session,
        current_user=user,
        checkpoint_id=cp.id,
        request=req_campus,
        current_time=t0,
    )

    assert ch_dto.challenge_id is not None
    assert ch_dto.nonce is not None
    assert ch_dto.network_zone_id == zone.id
    # Verify 20s TTL
    expected_expiry = t0 + datetime.timedelta(seconds=20)
    assert ch_dto.expires_at == expected_expiry

    # 5. Build canonical payload and sign with student's device private key
    payload_bytes = build_network_challenge_payload(
        challenge_id=ch_dto.challenge_id,
        nonce=ch_dto.nonce,
        user_id=user.id,
        university_id=test_university.id,
        trusted_device_id=device.id,
        attendance_session_id=sess.id,
        attendance_checkpoint_id=cp.id,
        network_zone_id=zone.id,
        issued_at=t0,
        expires_at=expected_expiry,
    )
    sig = sign_payload_with_private_key(priv_pem, payload_bytes)
    proof_1 = NetworkProofSchema(
        challenge_id=ch_dto.challenge_id,
        trusted_device_id=device.id,
        proof_id=uuid.uuid4(),
        signature=sig,
    )

    # 6. Verify and consume proof at t0 + 5s from same campus IP
    t1 = t0 + datetime.timedelta(seconds=5)
    consumed_ch = await CampusNetworkService.verify_and_consume_network_proof(
        db=db_session,
        current_user=user,
        network_proof=proof_1,
        expected_session_id=sess.id,
        expected_checkpoint_id=cp.id,
        request=req_campus,
        current_time=t1,
    )
    assert consumed_ch.status == "CONSUMED"
    assert consumed_ch.consumed_at is not None

    # 7. Idempotent retry: Same proof_id returns consumed challenge successfully
    retry_ch = await CampusNetworkService.verify_and_consume_network_proof(
        db=db_session,
        current_user=user,
        network_proof=proof_1,
        expected_session_id=sess.id,
        expected_checkpoint_id=cp.id,
        request=req_campus,
        current_time=t1 + datetime.timedelta(seconds=1),
    )
    assert retry_ch.id == consumed_ch.id

    # 8. Replay attempt: Different proof_id for already consumed challenge is rejected
    proof_replay = NetworkProofSchema(
        challenge_id=ch_dto.challenge_id,
        trusted_device_id=device.id,
        proof_id=uuid.uuid4(),  # Different proof_id
        signature=sig,
    )
    with pytest.raises(DomainException) as exc_replay:
        await CampusNetworkService.verify_and_consume_network_proof(
            db=db_session,
            current_user=user,
            network_proof=proof_replay,
            expected_session_id=sess.id,
            expected_checkpoint_id=cp.id,
            request=req_campus,
            current_time=t1 + datetime.timedelta(seconds=2),
        )
    assert exc_replay.value.code == "NETWORK_CHALLENGE_CONSUMED"


@pytest.mark.asyncio
async def test_network_challenge_expiration_enforced(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify challenge verification strictly fails after 20s TTL expiration."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (priv_pem, pub_pem) = await _create_enrolled_student_with_device(
        client, admin_headers, offering_id, test_university.id, db_session, "net_exp_1"
    )

    zone = CampusNetworkZone(
        university_id=test_university.id,
        name="Campus Wi-Fi Expiry",
        code=f"ZONE_EXP_{uuid.uuid4().hex[:6]}".upper(),
        network_cidr="192.168.20.0/24",
        ip_version=4,
        zone_type=NetworkZoneType.CAMPUS_TRUSTED.value,
        status=NetworkZoneStatus.ACTIVE.value,
        priority=100,
        allow_student_presence=True,
    )
    db_session.add(zone)
    await db_session.flush()

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

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    req_campus = _mock_request("192.168.20.10")

    ch_dto = await CampusNetworkService.issue_network_challenge(
        db=db_session,
        current_user=user,
        checkpoint_id=cp.id,
        request=req_campus,
        current_time=t0,
    )

    payload_bytes = build_network_challenge_payload(
        challenge_id=ch_dto.challenge_id,
        nonce=ch_dto.nonce,
        user_id=user.id,
        university_id=test_university.id,
        trusted_device_id=device.id,
        attendance_session_id=sess.id,
        attendance_checkpoint_id=cp.id,
        network_zone_id=zone.id,
        issued_at=t0,
        expires_at=t0 + datetime.timedelta(seconds=20),
    )
    sig = sign_payload_with_private_key(priv_pem, payload_bytes)
    proof = NetworkProofSchema(
        challenge_id=ch_dto.challenge_id,
        trusted_device_id=device.id,
        proof_id=uuid.uuid4(),
        signature=sig,
    )

    # Attempt to verify at t0 + 25s (5s past expiration)
    t_expired = t0 + datetime.timedelta(seconds=25)
    with pytest.raises(DomainException) as exc:
        await CampusNetworkService.verify_and_consume_network_proof(
            db=db_session,
            current_user=user,
            network_proof=proof,
            expected_session_id=sess.id,
            expected_checkpoint_id=cp.id,
            request=req_campus,
            current_time=t_expired,
        )
    assert exc.value.code == "NETWORK_CHALLENGE_EXPIRED"


@pytest.mark.asyncio
async def test_network_submission_source_ip_mismatch_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify challenge issued on campus zone is rejected if submitted from external IP."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    user, student, device, (priv_pem, pub_pem) = await _create_enrolled_student_with_device(
        client, admin_headers, offering_id, test_university.id, db_session, "net_mis_1"
    )

    zone = CampusNetworkZone(
        university_id=test_university.id,
        name="Campus Wi-Fi Mismatch",
        code=f"ZONE_MIS_{uuid.uuid4().hex[:6]}".upper(),
        network_cidr="192.168.30.0/24",
        ip_version=4,
        zone_type=NetworkZoneType.CAMPUS_TRUSTED.value,
        status=NetworkZoneStatus.ACTIVE.value,
        priority=100,
        allow_student_presence=True,
    )
    db_session.add(zone)
    await db_session.flush()

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

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    req_campus = _mock_request("192.168.30.15")

    ch_dto = await CampusNetworkService.issue_network_challenge(
        db=db_session,
        current_user=user,
        checkpoint_id=cp.id,
        request=req_campus,
        current_time=t0,
    )

    payload_bytes = build_network_challenge_payload(
        challenge_id=ch_dto.challenge_id,
        nonce=ch_dto.nonce,
        user_id=user.id,
        university_id=test_university.id,
        trusted_device_id=device.id,
        attendance_session_id=sess.id,
        attendance_checkpoint_id=cp.id,
        network_zone_id=zone.id,
        issued_at=t0,
        expires_at=t0 + datetime.timedelta(seconds=20),
    )
    sig = sign_payload_with_private_key(priv_pem, payload_bytes)
    proof = NetworkProofSchema(
        challenge_id=ch_dto.challenge_id,
        trusted_device_id=device.id,
        proof_id=uuid.uuid4(),
        signature=sig,
    )

    # Submit from external / untrusted IP (198.51.100.99)
    req_external = _mock_request("198.51.100.99")
    t1 = t0 + datetime.timedelta(seconds=5)
    with pytest.raises(DomainException) as exc:
        await CampusNetworkService.verify_and_consume_network_proof(
            db=db_session,
            current_user=user,
            network_proof=proof,
            expected_session_id=sess.id,
            expected_checkpoint_id=cp.id,
            request=req_external,
            current_time=t1,
        )
    assert exc.value.code == "NETWORK_NOT_TRUSTED"
