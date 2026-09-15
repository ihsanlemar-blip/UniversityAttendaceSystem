"""Integration tests for Milestone 13 Device Replacement, Transitions & Review."""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import (
    DeviceReplacementStatus,
    DeviceRole,
    DeviceStatus,
)
from backend.app.core.exceptions import ConflictException
from backend.app.devices.crypto import (
    compute_public_key_fingerprint,
    generate_device_keypair,
    sign_payload_with_private_key,
)
from backend.app.devices.schemas import (
    DeviceRegistrationChallengeRequest,
    DeviceRegistrationConfirmRequest,
    DeviceReplacementCreateRequest,
    DeviceReplacementReviewRequest,
    DeviceStatusUpdateRequest,
)
from backend.app.devices.service import DeviceTrustService
from backend.app.models.student import Student
from backend.app.models.trusted_device import TrustedDevice
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


async def _create_student_with_active_device(
    client: TestClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
    prefix: str,
) -> tuple[User, Student, TrustedDevice, tuple[str, str]]:
    """Helper to create a student and complete initial registration of an active device."""
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

    priv_pem, pub_pem = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

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
    active_dev = await db_session.get(TrustedDevice, dev_dto.id)
    assert active_dev is not None
    return user, student, active_dev, (priv_pem, pub_pem)


@pytest.mark.asyncio
async def test_request_device_replacement_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify student with active device can request replacement with candidate device."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student, old_device, _ = await _create_student_with_active_device(
        client, admin_headers, db_session, "repl_req"
    )

    priv2, pub2 = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 11, 0, 0, tzinfo=datetime.UTC)

    # 1. Candidate device requests challenge
    ch2 = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub2,
            installation_id=uuid.uuid4(),
            platform="ios",
            device_label="iPhone 16 Pro",
            app_version="1.1.0",
        ),
        current_time=t0,
    )

    # 2. Candidate device signs challenge
    sig2 = sign_payload_with_private_key(priv2, ch2.canonical_challenge.encode("utf-8"))

    # 3. Submit replacement request
    repl_req = DeviceReplacementCreateRequest(
        candidate_challenge_id=ch2.challenge_id,
        candidate_signature=sig2,
        reason="Upgraded phone to iPhone 16 Pro.",
    )
    repl_resp = await DeviceTrustService.request_device_replacement(
        db=db_session,
        current_user=user,
        payload=repl_req,
        current_time=t0 + datetime.timedelta(seconds=5),
    )

    assert repl_resp.id is not None
    assert repl_resp.status == DeviceReplacementStatus.PENDING.value
    assert repl_resp.old_device_id == old_device.id
    assert repl_resp.candidate_fingerprint == compute_public_key_fingerprint(pub2)

    # Old device remains ACTIVE while replacement is pending
    await db_session.refresh(old_device)
    assert old_device.status == DeviceStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_request_device_replacement_fails_if_already_pending(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify student cannot submit multiple concurrent replacement requests."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student, old_device, _ = await _create_student_with_active_device(
        client, admin_headers, db_session, "repl_dup"
    )

    priv2, pub2 = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 11, 0, 0, tzinfo=datetime.UTC)

    ch2 = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub2,
            installation_id=uuid.uuid4(),
            platform="android",
            device_label="Phone 2",
            app_version="1.0.0",
        ),
        current_time=t0,
    )
    sig2 = sign_payload_with_private_key(priv2, ch2.canonical_challenge.encode("utf-8"))
    await DeviceTrustService.request_device_replacement(
        db=db_session,
        current_user=user,
        payload=DeviceReplacementCreateRequest(
            candidate_challenge_id=ch2.challenge_id,
            candidate_signature=sig2,
            reason="First replacement request",
        ),
        current_time=t0 + datetime.timedelta(seconds=5),
    )

    # Attempt second replacement request
    priv3, pub3 = generate_device_keypair()
    ch3 = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub3,
            installation_id=uuid.uuid4(),
            platform="android",
            device_label="Phone 3",
            app_version="1.0.0",
        ),
        current_time=t0 + datetime.timedelta(seconds=10),
    )
    sig3 = sign_payload_with_private_key(priv3, ch3.canonical_challenge.encode("utf-8"))

    with pytest.raises(ConflictException) as exc_info:
        await DeviceTrustService.request_device_replacement(
            db=db_session,
            current_user=user,
            payload=DeviceReplacementCreateRequest(
                candidate_challenge_id=ch3.challenge_id,
                candidate_signature=sig3,
                reason="Second replacement attempt",
            ),
            current_time=t0 + datetime.timedelta(seconds=15),
        )
    assert exc_info.value.code == "DEVICE_REPLACEMENT_PENDING"


@pytest.mark.asyncio
async def test_approve_device_replacement_atomic_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """INV-13-03: Staff approves replacement: old -> REPLACED, new -> ACTIVE atomically."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student, old_device, _ = await _create_student_with_active_device(
        client, admin_headers, db_session, "repl_appr"
    )

    priv2, pub2 = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 11, 0, 0, tzinfo=datetime.UTC)

    ch2 = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub2,
            installation_id=uuid.uuid4(),
            platform="ios",
            device_label="New Phone",
            app_version="1.0.0",
        ),
        current_time=t0,
    )
    sig2 = sign_payload_with_private_key(priv2, ch2.canonical_challenge.encode("utf-8"))
    repl_resp = await DeviceTrustService.request_device_replacement(
        db=db_session,
        current_user=user,
        payload=DeviceReplacementCreateRequest(
            candidate_challenge_id=ch2.challenge_id,
            candidate_signature=sig2,
            reason="Old phone screen broken.",
        ),
        current_time=t0 + datetime.timedelta(seconds=5),
    )

    # Admin approves replacement
    t_appr = t0 + datetime.timedelta(minutes=10)
    approved_resp = await DeviceTrustService.approve_device_replacement(
        db=db_session,
        request_id=repl_resp.id,
        reviewer_user=test_admin_user,
        payload=DeviceReplacementReviewRequest(review_note="Verified in student affairs office."),
        current_time=t_appr,
    )

    assert approved_resp.status == DeviceReplacementStatus.APPROVED.value
    assert approved_resp.approved_device_id is not None

    # Check that old device is now REPLACED
    await db_session.refresh(old_device)
    assert old_device.status == DeviceStatus.REPLACED.value
    assert old_device.replaced_at == t_appr
    assert old_device.replaced_by_device_id == approved_resp.approved_device_id

    # Check that new device is now ACTIVE
    new_device = await db_session.get(TrustedDevice, approved_resp.approved_device_id)
    assert new_device is not None
    assert new_device.status == DeviceStatus.ACTIVE.value
    assert new_device.device_role == DeviceRole.PRIMARY.value
    assert new_device.public_key_fingerprint == compute_public_key_fingerprint(pub2)

    # Student active device query returns new device
    active_now = await DeviceTrustService.get_student_active_device(
        db=db_session,
        student_id=student.id,
        university_id=test_university.id,
    )
    assert active_now is not None
    assert active_now.id == new_device.id


@pytest.mark.asyncio
async def test_reject_device_replacement_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify admin rejection leaves old device ACTIVE and transitions request to REJECTED."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student, old_device, _ = await _create_student_with_active_device(
        client, admin_headers, db_session, "repl_rej"
    )

    priv2, pub2 = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 11, 0, 0, tzinfo=datetime.UTC)

    ch2 = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub2,
            installation_id=uuid.uuid4(),
            platform="ios",
            device_label="Suspicious Phone",
            app_version="1.0.0",
        ),
        current_time=t0,
    )
    sig2 = sign_payload_with_private_key(priv2, ch2.canonical_challenge.encode("utf-8"))
    repl_resp = await DeviceTrustService.request_device_replacement(
        db=db_session,
        current_user=user,
        payload=DeviceReplacementCreateRequest(
            candidate_challenge_id=ch2.challenge_id,
            candidate_signature=sig2,
            reason="Want to test new phone",
        ),
        current_time=t0 + datetime.timedelta(seconds=5),
    )

    # Admin rejects replacement
    rejected_resp = await DeviceTrustService.reject_device_replacement(
        db=db_session,
        request_id=repl_resp.id,
        reviewer_user=test_admin_user,
        payload=DeviceReplacementReviewRequest(
            review_note="Student identity could not be verified."
        ),
        current_time=t0 + datetime.timedelta(minutes=15),
    )

    assert rejected_resp.status == DeviceReplacementStatus.REJECTED.value

    # Old device remains ACTIVE
    await db_session.refresh(old_device)
    assert old_device.status == DeviceStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_report_device_lost_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify student reporting device lost suspends the device immediately."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student, old_device, _ = await _create_student_with_active_device(
        client, admin_headers, db_session, "dev_lost"
    )

    t0 = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)
    lost_resp = await DeviceTrustService.report_device_lost(
        db=db_session,
        current_user=user,
        current_time=t0,
    )

    assert lost_resp.status == DeviceStatus.SUSPENDED.value
    await db_session.refresh(old_device)
    assert old_device.status == DeviceStatus.SUSPENDED.value
    assert old_device.suspended_at == t0

    # No active device exists now
    active_now = await DeviceTrustService.get_student_active_device(
        db=db_session,
        student_id=student.id,
        university_id=test_university.id,
    )
    assert active_now is None


@pytest.mark.asyncio
async def test_admin_suspend_and_revoke_device(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify staff can administratively suspend and revoke student devices."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student, old_device, _ = await _create_student_with_active_device(
        client, admin_headers, db_session, "dev_admin_op"
    )

    # 1. Suspend
    t_sus = datetime.datetime(2026, 9, 15, 13, 0, 0, tzinfo=datetime.UTC)
    sus_resp = await DeviceTrustService.suspend_device(
        db=db_session,
        device_id=old_device.id,
        actor_user=test_admin_user,
        payload=DeviceStatusUpdateRequest(reason="Suspicious attendance patterns under review."),
        current_time=t_sus,
    )
    assert sus_resp.status == DeviceStatus.SUSPENDED.value

    # 2. Revoke
    t_rev = datetime.datetime(2026, 9, 15, 14, 0, 0, tzinfo=datetime.UTC)
    rev_resp = await DeviceTrustService.revoke_device(
        db=db_session,
        device_id=old_device.id,
        actor_user=test_admin_user,
        payload=DeviceStatusUpdateRequest(reason="Device permanently decommissioned."),
        current_time=t_rev,
    )
    assert rev_resp.status == DeviceStatus.REVOKED.value
