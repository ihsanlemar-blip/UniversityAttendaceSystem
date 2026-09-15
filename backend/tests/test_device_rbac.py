"""RBAC & multi-tenant isolation tests for Milestone 13 Device Trust Endpoints."""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import ScopeType, SystemRole
from backend.app.devices.crypto import generate_device_keypair, sign_payload_with_private_key
from backend.app.devices.schemas import (
    DeviceRegistrationChallengeRequest,
    DeviceRegistrationConfirmRequest,
    DeviceReplacementCreateRequest,
)
from backend.app.devices.service import DeviceTrustService
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.student import Student
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


async def _setup_student_with_headers(
    client: TestClient,
    admin_headers: dict[str, str],
    university: University,
    db_session: AsyncSession,
    prefix: str,
) -> tuple[User, Student, dict[str, str]]:
    """Helper to create a student and retrieve their authenticated client headers."""
    u_id, username, password = create_test_user(client, admin_headers, prefix=prefix)
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

    # Assign STUDENT role so user receives devices.self_read & devices.self_register
    role_res = await db_session.execute(
        Role.__table__.select().where(Role.code == SystemRole.STUDENT.value)
    )
    student_role = role_res.first()
    assert student_role is not None

    db_session.add(
        RoleAssignment(
            user_id=user.id,
            role_id=student_role.id,
            university_id=university.id,
            scope_type=ScopeType.UNIVERSITY.value,
            scope_id=university.id,
        )
    )
    await db_session.commit()

    student_headers = get_user_headers(client, username, password, str(university.id))
    return user, student, student_headers


def test_device_endpoints_unauthenticated(client: TestClient) -> None:
    """Verify unauthenticated requests to device endpoints are rejected with 401."""
    resp1 = client.get("/api/v1/devices/me")
    assert resp1.status_code == 401

    resp2 = client.post(
        "/api/v1/devices/registration/challenge",
        json={"public_key": "some_key"},
    )
    assert resp2.status_code == 401

    resp3 = client.get("/api/v1/devices/replacement-requests")
    assert resp3.status_code == 401


@pytest.mark.asyncio
async def test_student_device_registration_rbac_flow(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify student can request challenge, confirm registration, and query device status."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student, student_headers = await _setup_student_with_headers(
        client, admin_headers, test_university, db_session, "rbac_stu_1"
    )

    # 1. Initially student has no active device
    resp_init = client.get("/api/v1/devices/me", headers=student_headers)
    assert resp_init.status_code == 200
    assert resp_init.json()["data"]["has_active_device"] is False

    # 2. Student requests registration challenge
    priv_pem, pub_pem = generate_device_keypair()
    resp_ch = client.post(
        "/api/v1/devices/registration/challenge",
        headers=student_headers,
        json={
            "public_key": pub_pem,
            "installation_id": str(uuid.uuid4()),
            "platform": "android",
            "device_label": "Student Phone",
            "app_version": "1.0.0",
        },
    )
    assert resp_ch.status_code == 201
    ch_data = resp_ch.json()["data"]
    challenge_id = ch_data["challenge_id"]
    canonical_challenge = ch_data["canonical_challenge"]

    # 3. Student signs and confirms registration
    sig = sign_payload_with_private_key(priv_pem, canonical_challenge.encode("utf-8"))
    resp_confirm = client.post(
        "/api/v1/devices/registration/confirm",
        headers=student_headers,
        json={
            "challenge_id": challenge_id,
            "signature": sig,
        },
    )
    assert resp_confirm.status_code == 201
    dev_data = resp_confirm.json()["data"]
    assert dev_data["status"] == "ACTIVE"

    # 4. Student queries me
    resp_status = client.get("/api/v1/devices/me", headers=student_headers)
    assert resp_status.status_code == 200
    assert resp_status.json()["data"]["has_active_device"] is True
    assert resp_status.json()["data"]["active_device"]["id"] == dev_data["id"]


@pytest.mark.asyncio
async def test_student_forbidden_from_admin_device_routes(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify student role cannot access administrative replacement review routes."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user, student, student_headers = await _setup_student_with_headers(
        client, admin_headers, test_university, db_session, "rbac_stu_no_adm"
    )

    # 1. Student cannot list university-wide replacement requests
    resp1 = client.get("/api/v1/devices/replacement-requests", headers=student_headers)
    assert resp1.status_code == 403

    # 2. Student cannot list another student's device history
    resp2 = client.get(f"/api/v1/devices/student/{uuid.uuid4()}", headers=student_headers)
    assert resp2.status_code == 403

    # 3. Student cannot list audit ledger
    resp3 = client.get("/api/v1/devices/events", headers=student_headers)
    assert resp3.status_code == 403

    # 4. Student cannot approve or reject replacements
    dummy_req_id = str(uuid.uuid4())
    resp4 = client.post(
        f"/api/v1/devices/replacement-requests/{dummy_req_id}/approve",
        headers=student_headers,
        json={"review_note": "Sneaky approval attempt"},
    )
    assert resp4.status_code == 403

    resp5 = client.post(
        f"/api/v1/devices/replacement-requests/{dummy_req_id}/reject",
        headers=student_headers,
        json={"review_note": "Sneaky rejection attempt"},
    )
    assert resp5.status_code == 403


@pytest.mark.asyncio
async def test_tenant_isolation_in_device_replacement_review(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    second_university: University,
    second_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify administrator of University A cannot approve replacement request from University B."""
    admin_headers_a = get_admin_headers(client, test_admin_user, test_university)
    admin_headers_b = get_admin_headers(client, second_admin_user, second_university)

    # Create student in University A
    user_a, student_a, student_a_headers = await _setup_student_with_headers(
        client, admin_headers_a, test_university, db_session, "stu_tenant_a"
    )

    # Register initial device for Student A
    priv_a1, pub_a1 = generate_device_keypair()
    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    ch1 = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user_a,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub_a1,
            installation_id=uuid.uuid4(),
            platform="android",
            device_label="Phone A1",
            app_version="1.0.0",
        ),
        current_time=t0,
    )
    sig1 = sign_payload_with_private_key(priv_a1, ch1.canonical_challenge.encode("utf-8"))
    await DeviceTrustService.confirm_initial_registration(
        db=db_session,
        current_user=user_a,
        payload=DeviceRegistrationConfirmRequest(challenge_id=ch1.challenge_id, signature=sig1),
        current_time=t0 + datetime.timedelta(seconds=5),
    )

    # Student A requests replacement
    priv_a2, pub_a2 = generate_device_keypair()
    ch2 = await DeviceTrustService.request_registration_challenge(
        db=db_session,
        current_user=user_a,
        payload=DeviceRegistrationChallengeRequest(
            public_key=pub_a2,
            installation_id=uuid.uuid4(),
            platform="ios",
            device_label="Phone A2",
            app_version="1.0.0",
        ),
        current_time=t0 + datetime.timedelta(seconds=10),
    )
    sig2 = sign_payload_with_private_key(priv_a2, ch2.canonical_challenge.encode("utf-8"))
    repl_resp = await DeviceTrustService.request_device_replacement(
        db=db_session,
        current_user=user_a,
        payload=DeviceReplacementCreateRequest(
            candidate_challenge_id=ch2.challenge_id,
            candidate_signature=sig2,
            reason="Phone broken",
        ),
        current_time=t0 + datetime.timedelta(seconds=15),
    )
    repl_id = str(repl_resp.id)

    # Admin B (from University B) attempts to approve replacement for University A -> 404
    resp_cross = client.post(
        f"/api/v1/devices/replacement-requests/{repl_id}/approve",
        headers=admin_headers_b,
        json={"review_note": "Cross-tenant approval attempt"},
    )
    assert resp_cross.status_code == 404

    # Admin A approves replacement -> 200 OK
    resp_valid = client.post(
        f"/api/v1/devices/replacement-requests/{repl_id}/approve",
        headers=admin_headers_a,
        json={"review_note": "Valid approval by University A admin"},
    )
    assert resp_valid.status_code == 200
    assert resp_valid.json()["data"]["status"] == "APPROVED"
