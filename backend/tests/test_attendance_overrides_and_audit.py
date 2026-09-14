"""Test suite for Attendance manual overrides, versioning, audit trail, and invariants.

Enforces INV-06 (append-only ledger) and INV-08 (mandatory justification).
"""

import uuid

from fastapi.testclient import TestClient

from backend.app.core.constants import AttendanceStatus
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_attendance_sessions import create_enrolled_student
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


def test_inv_06_and_inv_08_manual_overrides_versioning_and_audit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify INV-06 (append-only history & versioning) and INV-08 (mandatory reason & actor ID)."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)
    student_id = create_enrolled_student(client, headers, offering_id, "ovr_01")

    # 1. Initialize and open session
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    # Close session immediately (student has 0 checkpoints -> ABSENT, version 1)
    close_res = client.post(f"/api/v1/attendance/sessions/{session_id}/close", headers=headers)
    assert close_res.status_code == 200

    rec_res = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=headers)
    record = next(r for r in rec_res.json()["data"] if r["student_id"] == student_id)
    record_id = record["id"]
    assert record["status"] == AttendanceStatus.ABSENT.value
    assert record["version_no"] == 1
    assert record["is_manual"] is False

    # 2. First Override: ABSENT -> PRESENT with valid reason
    reason_1 = "Student arrived before lecture end and signed paper sign-in sheet"
    ovr1_res = client.post(
        f"/api/v1/attendance/records/{record_id}/override",
        headers=headers,
        json={"status": "PRESENT", "reason": reason_1},
    )
    assert ovr1_res.status_code == 200
    ovr1_data = ovr1_res.json()["data"]
    assert ovr1_data["status"] == "PRESENT"
    assert ovr1_data["attendance_credit"] == 1.0
    assert ovr1_data["version_no"] == 2
    assert ovr1_data["is_manual"] is True
    assert ovr1_data["manual_reason"] == reason_1

    # 3. Second Override: PRESENT -> EXCUSED
    reason_2 = "Medical clinic note submitted for latter half of lecture"
    ovr2_res = client.post(
        f"/api/v1/attendance/records/{record_id}/override",
        headers=headers,
        json={"status": "EXCUSED", "reason": reason_2},
    )
    assert ovr2_res.status_code == 200
    ovr2_data = ovr2_res.json()["data"]
    assert ovr2_data["status"] == "EXCUSED"
    assert ovr2_data["version_no"] == 3
    assert ovr2_data["manual_reason"] == reason_2

    # 4. Verify Immutable Audit Ledger (INV-06 & INV-08)
    audit_res = client.get(f"/api/v1/attendance/audit?record_id={record_id}", headers=headers)
    assert audit_res.status_code == 200
    revisions = audit_res.json()["data"]

    # At least the 2 manual overrides must be in the ledger
    override_revs = [r for r in revisions if r["event_type"] == "MANUAL_RECORD_OVERRIDE"]
    assert len(override_revs) == 2

    # Latest revision: PRESENT -> EXCUSED
    assert override_revs[0]["previous_status"] == "PRESENT"
    assert override_revs[0]["new_status"] == "EXCUSED"
    assert override_revs[0]["reason"] == reason_2
    assert override_revs[0]["actor_user_id"] == str(test_admin_user.id)

    # First revision: ABSENT -> PRESENT
    assert override_revs[1]["previous_status"] == "ABSENT"
    assert override_revs[1]["new_status"] == "PRESENT"
    assert override_revs[1]["reason"] == reason_1
    assert override_revs[1]["actor_user_id"] == str(test_admin_user.id)


def test_inv_08_override_requires_non_empty_justification(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify INV-08: Manual overrides without justification are strictly rejected."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, headers)
    _ = create_enrolled_student(client, headers, offering_id, "ovr_no_rsn")

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    rec_res = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=headers)
    record_id = rec_res.json()["data"][0]["id"]

    # 1. Empty string reason -> 422 (validation min_length=3)
    res_empty = client.post(
        f"/api/v1/attendance/records/{record_id}/override",
        headers=headers,
        json={"status": "PRESENT", "reason": ""},
    )
    assert res_empty.status_code == 422

    # 2. Whitespace-only reason -> 400 REASON_REQUIRED or 422
    res_spaces = client.post(
        f"/api/v1/attendance/records/{record_id}/override",
        headers=headers,
        json={"status": "PRESENT", "reason": "   "},
    )
    assert res_spaces.status_code in (400, 422)

    # 3. Missing reason field -> 422
    res_missing = client.post(
        f"/api/v1/attendance/records/{record_id}/override",
        headers=headers,
        json={"status": "PRESENT"},
    )
    assert res_missing.status_code == 422


def test_session_level_audit_revisions(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify session lifecycle events are recorded in the audit ledger."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    _, _, occurrence_id = setup_class_occurrence(client, headers)

    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]

    # Pause and resume
    client.post(f"/api/v1/attendance/sessions/{session_id}/pause", headers=headers)
    client.post(f"/api/v1/attendance/sessions/{session_id}/resume", headers=headers)
    client.post(f"/api/v1/attendance/sessions/{session_id}/close", headers=headers)

    # Query session audit
    audit_res = client.get(f"/api/v1/attendance/audit?session_id={session_id}", headers=headers)
    assert audit_res.status_code == 200
    revs = audit_res.json()["data"]

    event_types = {r["event_type"] for r in revs}
    assert "SESSION_PAUSED" in event_types
    assert "SESSION_RESUMED" in event_types
    assert "SESSION_CLOSED" in event_types


def test_audit_access_restricted(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify audit log requires attendance_audit.read permission."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    user_id, email, password = create_test_user(
        client, admin_headers, prefix=f"std_aud_{uuid.uuid4().hex[:6]}"
    )
    student_headers = get_user_headers(client, email, password, str(test_university.id))

    # Student attempting to access audit logs -> 403 Forbidden
    res = client.get("/api/v1/attendance/audit", headers=student_headers)
    assert res.status_code == 403
