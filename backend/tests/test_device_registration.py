"""Integration tests for Milestone 13 Device Registration, Proof of Possession & Invariants."""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.types import utc_now
from backend.app.core.constants import DeviceRole, DeviceStatus
from backend.app.core.exceptions import ConflictException, DomainException
from backend.app.devices.crypto import (
    compute_public_key_fingerprint,
    generate_device_keypair,
    sign_payload_with_private_key,
)
from backend.app.devices.schemas import (
    DeviceRegistrationChallengeRequest,
    DeviceRegistrationConfirmRequest,
)
from backend.app.devices.service import DeviceTrustService
from backend.app.models.student import Student
from backend.app.models.trusted_device import TrustedDevice
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_people import create_test_user
from backend.tests.test_users import get_admin_headers


async def _create_student_user(
    client: TestClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
    prefix: str,
) -> tuple[User, Student]:
    """Helper to create a user with a linked student profile."""
    u_id, _, _ = create_test_user(client, admin_headers, prefix=prefix)
    user = await db_session.get(User, uuid.UUID(u_id))
    assert user is not None

    student_res = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={"user_id": u_id, "student_number": f"ST-{uuid.uuid4().hex[:8]}"},
    )
    assert student_res.status_code == 201
    s_id = uuid.UUID(student_res.json()["data"]["id"])
    student = await db_session.get(Student, s_id)
    assert student is not None
    return user, student


@pytest.mark.asyncio
async def test_registration_challenge_student_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify enrolled student can request a short-lived registration challenge."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student = await _create_student_user(client, admin_headers, db_session, "reg_ch1")

    _, pub_pem = generate_device_keypair()
    req = DeviceRegistrationChallengeRequest(
        public_key=pub_pem,
        installation_id=uuid.uuid4(),
        platform="android",
        device_label="Pixel 8 Pro",
        app_version="1.0.0",
    )

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    resp = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=req,
        current_time=t0,
    )

    assert resp.challenge_id is not None
    assert resp.candidate_fingerprint == compute_public_key_fingerprint(pub_pem)
    assert resp.expires_at == t0 + datetime.timedelta(seconds=300)
    assert "DEVICE_REGISTRATION_V1" in resp.canonical_challenge


@pytest.mark.asyncio
async def test_registration_challenge_non_student_forbidden(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify non-student user is forbidden from requesting device registration challenge."""
    _, pub_pem = generate_device_keypair()
    req = DeviceRegistrationChallengeRequest(
        public_key=pub_pem,
        installation_id=uuid.uuid4(),
        platform="ios",
        device_label="iPhone 15",
        app_version="1.0.0",
    )

    with pytest.raises(DomainException) as exc_info:
        await DeviceTrustService.request_registration_challenge(
            db=db_session,
            current_user=test_admin_user,  # admin is not a student
            payload=req,
        )
    assert exc_info.value.code == "NOT_A_STUDENT"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_confirm_initial_registration_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify student successfully proves possession of Ed25519 key and registers primary device."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student = await _create_student_user(client, admin_headers, db_session, "reg_ok")

    priv_pem, pub_pem = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    # 1. Request challenge
    ch_req = DeviceRegistrationChallengeRequest(
        public_key=pub_pem,
        installation_id=uuid.uuid4(),
        platform="android",
        device_label="Samsung Galaxy S24",
        app_version="1.0.0",
    )
    ch_resp = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=ch_req,
        current_time=t0,
    )

    # 2. Sign canonical challenge
    sig = sign_payload_with_private_key(priv_pem, ch_resp.canonical_challenge.encode("utf-8"))

    # 3. Confirm registration at t0 + 10 seconds
    t1 = t0 + datetime.timedelta(seconds=10)
    confirm_req = DeviceRegistrationConfirmRequest(
        challenge_id=ch_resp.challenge_id,
        signature=sig,
    )
    dev_resp = await DeviceTrustService.confirm_initial_registration(
        db=db_session,
        current_user=user,
        payload=confirm_req,
        current_time=t1,
    )

    assert dev_resp.id is not None
    assert dev_resp.status == DeviceStatus.ACTIVE.value
    assert dev_resp.device_role == DeviceRole.PRIMARY.value
    assert dev_resp.public_key_fingerprint == compute_public_key_fingerprint(pub_pem)
    assert dev_resp.device_label == "Samsung Galaxy S24"

    # Verify student device status
    status_resp = await DeviceTrustService.get_student_device_status(
        db=db_session,
        current_user=user,
    )
    assert status_resp.has_active_device is True
    assert status_resp.active_device is not None
    assert status_resp.active_device.id == dev_resp.id


@pytest.mark.asyncio
async def test_confirm_initial_registration_replay_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify single-use challenge cannot be replayed."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student = await _create_student_user(client, admin_headers, db_session, "reg_replay")

    priv_pem, pub_pem = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    ch_resp = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub_pem,
            installation_id=uuid.uuid4(),
            platform="ios",
            device_label="iPhone 14",
            app_version="1.0.0",
        ),
        current_time=t0,
    )

    sig = sign_payload_with_private_key(priv_pem, ch_resp.canonical_challenge.encode("utf-8"))
    confirm_req = DeviceRegistrationConfirmRequest(
        challenge_id=ch_resp.challenge_id,
        signature=sig,
    )

    # First consumption succeeds
    await DeviceTrustService.confirm_initial_registration(
        db=db_session,
        current_user=user,
        payload=confirm_req,
        current_time=t0 + datetime.timedelta(seconds=5),
    )

    # Second consumption must fail
    with pytest.raises(DomainException) as exc_info:
        await DeviceTrustService.confirm_initial_registration(
            db=db_session,
            current_user=user,
            payload=confirm_req,
            current_time=t0 + datetime.timedelta(seconds=6),
        )
    assert exc_info.value.code == "DEVICE_REGISTRATION_CHALLENGE_USED"


@pytest.mark.asyncio
async def test_confirm_initial_registration_expired_rejected(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify expired challenge cannot be confirmed."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student = await _create_student_user(client, admin_headers, db_session, "reg_expired")

    priv_pem, pub_pem = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    ch_resp = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub_pem,
            installation_id=uuid.uuid4(),
            platform="ios",
            device_label="iPhone 14",
            app_version="1.0.0",
        ),
        current_time=t0,
    )

    sig = sign_payload_with_private_key(priv_pem, ch_resp.canonical_challenge.encode("utf-8"))
    confirm_req = DeviceRegistrationConfirmRequest(
        challenge_id=ch_resp.challenge_id,
        signature=sig,
    )

    # Attempting to confirm after 301 seconds (TTL is 300 seconds)
    t_expired = t0 + datetime.timedelta(seconds=301)
    with pytest.raises(DomainException) as exc_info:
        await DeviceTrustService.confirm_initial_registration(
            db=db_session,
            current_user=user,
            payload=confirm_req,
            current_time=t_expired,
        )
    assert exc_info.value.code == "DEVICE_REGISTRATION_CHALLENGE_EXPIRED"


@pytest.mark.asyncio
async def test_initial_registration_fails_if_active_device_already_exists(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """INV-13-03: Student with active primary device cannot register a second device directly."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student = await _create_student_user(client, admin_headers, db_session, "reg_second")

    priv1, pub1 = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    # 1. Register first device
    ch1 = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub1,
            installation_id=uuid.uuid4(),
            platform="android",
            device_label="Primary Phone",
            app_version="1.0.0",
        ),
        current_time=t0,
    )
    sig1 = sign_payload_with_private_key(priv1, ch1.canonical_challenge.encode("utf-8"))
    await DeviceTrustService.confirm_initial_registration(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationConfirmRequest(challenge_id=ch1.challenge_id, signature=sig1),
        current_time=t0 + datetime.timedelta(seconds=5),
    )

    # 2. Attempt to register a second device via initial registration
    priv2, pub2 = generate_device_keypair()
    ch2 = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub2,
            installation_id=uuid.uuid4(),
            platform="ios",
            device_label="Second Phone",
            app_version="1.0.0",
        ),
        current_time=t0 + datetime.timedelta(seconds=10),
    )
    sig2 = sign_payload_with_private_key(priv2, ch2.canonical_challenge.encode("utf-8"))

    with pytest.raises(DomainException) as exc_info:
        await DeviceTrustService.confirm_initial_registration(
            db=db_session,
            current_user=user,
            payload=DeviceRegistrationConfirmRequest(challenge_id=ch2.challenge_id, signature=sig2),
            current_time=t0 + datetime.timedelta(seconds=15),
        )
    assert exc_info.value.code == "DEVICE_REPLACEMENT_REQUIRED"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_public_key_cannot_be_bound_to_multiple_students(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify Section 25 requirement: Same device key cannot be bound to two different students."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user_a, student_a = await _create_student_user(client, admin_headers, db_session, "stu_a")
    user_b, student_b = await _create_student_user(client, admin_headers, db_session, "stu_b")

    priv_shared, pub_shared = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    # Student A registers device
    ch_a = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user_a,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub_shared,
            installation_id=uuid.uuid4(),
            platform="android",
            device_label="Shared Device",
            app_version="1.0.0",
        ),
        current_time=t0,
    )
    sig_a = sign_payload_with_private_key(priv_shared, ch_a.canonical_challenge.encode("utf-8"))
    await DeviceTrustService.confirm_initial_registration(
        db=db_session,
        current_user=user_a,
        payload=DeviceRegistrationConfirmRequest(challenge_id=ch_a.challenge_id, signature=sig_a),
        current_time=t0 + datetime.timedelta(seconds=5),
    )

    # Student B attempts to request challenge for the same public key
    with pytest.raises(ConflictException) as exc_info:
        await DeviceTrustService.request_registration_challenge(
            db=db_session,
            current_user=user_b,
            payload=DeviceRegistrationChallengeRequest(
                public_key=pub_shared,
                installation_id=uuid.uuid4(),
                platform="android",
                device_label="Shared Device Attempt",
                app_version="1.0.0",
            ),
            current_time=t0 + datetime.timedelta(seconds=10),
        )
    assert exc_info.value.code == "DEVICE_ALREADY_BOUND_TO_ANOTHER_ACCOUNT"


@pytest.mark.asyncio
async def test_db_partial_unique_index_enforces_single_active_device(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify PostgreSQL partial unique index uq_trusted_devices_active_student."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student = await _create_student_user(client, admin_headers, db_session, "db_idx_stu")

    _, pub1 = generate_device_keypair()
    _, pub2 = generate_device_keypair()
    now = utc_now()

    d1 = TrustedDevice(
        id=uuid.uuid4(),
        university_id=test_university.id,
        user_id=user.id,
        student_id=student.id,
        device_role=DeviceRole.PRIMARY.value,
        public_key=pub1,
        public_key_fingerprint=compute_public_key_fingerprint(pub1),
        installation_id=uuid.uuid4(),
        platform="android",
        device_label="Device 1",
        app_version="1.0.0",
        status=DeviceStatus.ACTIVE.value,
        activated_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(d1)
    await db_session.commit()

    # Attempt to insert a second ACTIVE device for the exact same student directly in the DB
    d2 = TrustedDevice(
        id=uuid.uuid4(),
        university_id=test_university.id,
        user_id=user.id,
        student_id=student.id,
        device_role=DeviceRole.PRIMARY.value,
        public_key=pub2,
        public_key_fingerprint=compute_public_key_fingerprint(pub2),
        installation_id=uuid.uuid4(),
        platform="android",
        device_label="Device 2",
        app_version="1.0.0",
        status=DeviceStatus.ACTIVE.value,
        activated_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(d2)
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.commit()

    assert "uq_trusted_devices_active_student" in str(exc_info.value).lower()
    await db_session.rollback()
