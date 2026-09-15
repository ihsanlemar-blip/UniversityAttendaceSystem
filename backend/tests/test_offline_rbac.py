"""RBAC authorization tests for Milestone 12 Offline Attendance Endpoints."""

import uuid

from fastapi.testclient import TestClient

from backend.app.attendance.offline_crypto import generate_ed25519_keypair
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


def test_offline_verification_keys_accessible_to_authenticated_users(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify any authenticated user can read server public verification keys."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    resp = client.get("/api/v1/attendance/offline/verification-keys", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["algorithm"] == "EdDSA"
    assert data["curve"] == "Ed25519"
    assert "public_key_pem" in data


def test_offline_permit_request_rbac(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify permit request requires attendance_sessions.manage; student is forbidden."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, admin_headers)

    # 1. Student attempts permit request -> 403 Forbidden
    s_user_id, s_uname, s_pw = create_test_user(client, admin_headers, prefix="stu_rbac")
    s_headers = get_user_headers(client, s_uname, s_pw, str(test_university.id))
    _, host_pub = generate_ed25519_keypair()

    resp_forbidden = client.post(
        "/api/v1/attendance/offline/permits/request",
        headers=s_headers,
        json={
            "attendance_session_id": str(uuid.uuid4()),
            "temporary_host_public_key": host_pub,
            "validity_hours": 12,
        },
    )
    assert resp_forbidden.status_code == 403


def test_offline_host_sync_rbac(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify host events sync requires attendance_sessions.manage; student is forbidden."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    s_user_id, s_uname, s_pw = create_test_user(client, admin_headers, prefix="stu_host_rbac")
    s_headers = get_user_headers(client, s_uname, s_pw, str(test_university.id))

    resp = client.post(
        "/api/v1/attendance/offline/sync/host-events",
        headers=s_headers,
        json={
            "client_batch_id": "b1",
            "idempotency_key": "i1",
            "permit_id": str(uuid.uuid4()),
            "host_session_id": str(uuid.uuid4()),
            "host_device_id": "dev1",
            "clock_anchor_server_utc": "2026-09-15T10:00:00Z",
            "clock_anchor_uptime_ms": 1000,
            "started_at_utc": "2026-09-15T10:00:00Z",
            "events": [],
        },
    )
    assert resp.status_code == 403


def test_offline_conflicts_review_rbac(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify conflicts endpoint requires attendance_records.override; student is forbidden."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    s_user_id, s_uname, s_pw = create_test_user(client, admin_headers, prefix="stu_conf_rbac")
    s_headers = get_user_headers(client, s_uname, s_pw, str(test_university.id))

    resp_forbidden = client.get(
        "/api/v1/attendance/offline/conflicts",
        headers=s_headers,
    )
    assert resp_forbidden.status_code == 403

    resp_admin = client.get(
        "/api/v1/attendance/offline/conflicts",
        headers=admin_headers,
    )
    assert resp_admin.status_code == 200
