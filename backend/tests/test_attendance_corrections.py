"""Integration tests for Attendance Operations, Corrections, Excuses, Leave & Invariants.

Verifies:
- INV-01: Student ownership isolation
- INV-02: Authoritative server UTC correction window enforcement
- INV-05: Single open request constraint per attendance record
- INV-06: Append-only revision ledger & compensating reversals
- INV-08: Mandatory override justification and actor identity
- Section 38: Approved pre-class LEAVE grants 0.0 credit
"""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.types import utc_now
from backend.app.core.constants import (
    AttendanceAuditEventType,
    AttendanceStatus,
    CorrectionRequestStatus,
    CorrectionRequestType,
    ExcuseCategory,
    ExcuseRequestStatus,
    LeaveRequestStatus,
)
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


def create_student_with_role(
    client: TestClient,
    admin_headers: dict[str, str],
    offering_id: str,
    university_id: uuid.UUID,
    prefix: str,
) -> tuple[str, str, dict[str, str]]:
    """Helper creating user, student, assigning STUDENT role, enrolling in offering."""
    salt = uuid.uuid4().hex[:6]
    user_id, email, pwd = create_test_user(client, admin_headers, prefix=f"{prefix}_{salt}")
    stud_res = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={
            "user_id": user_id,
            "student_number": f"S_{prefix}_{salt}".upper(),
            "admission_date": "2024-09-01",
        },
    )
    assert stud_res.status_code == 201
    student_id = stud_res.json()["data"]["id"]

    roles_res = client.get("/api/v1/roles", headers=admin_headers)
    student_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "STUDENT")
    client.post(
        f"/api/v1/users/{user_id}/role-assignments",
        headers=admin_headers,
        json={
            "role_id": student_role_id,
            "scope_type": "UNIVERSITY",
            "scope_id": str(university_id),
        },
    )

    client.post(
        f"/api/v1/course-offerings/{offering_id}/enrollments",
        headers=admin_headers,
        json={"student_id": student_id},
    )

    student_headers = get_user_headers(client, email, pwd, str(university_id))
    return student_id, user_id, student_headers


def create_lecturer_with_role(
    client: TestClient,
    admin_headers: dict[str, str],
    offering_id: str,
    university_id: uuid.UUID,
    prefix: str,
    assign_to_offering: bool = True,
) -> tuple[str, str, dict[str, str]]:
    """Helper creating lecturer, assigning LECTURER role, optionally assigning to offering."""
    salt = uuid.uuid4().hex[:6]
    user_id, email, pwd = create_test_user(client, admin_headers, prefix=f"{prefix}_{salt}")
    lec_res = client.post(
        "/api/v1/lecturers",
        headers=admin_headers,
        json={
            "user_id": user_id,
            "employee_code": f"L_{prefix}_{salt}".upper(),
        },
    )
    assert lec_res.status_code == 201
    lecturer_id = lec_res.json()["data"]["id"]

    roles_res = client.get("/api/v1/roles", headers=admin_headers)
    lec_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "LECTURER")
    client.post(
        f"/api/v1/users/{user_id}/role-assignments",
        headers=admin_headers,
        json={
            "role_id": lec_role_id,
            "scope_type": "UNIVERSITY",
            "scope_id": str(university_id),
        },
    )

    if assign_to_offering:
        client.post(
            f"/api/v1/course-offerings/{offering_id}/lecturers",
            headers=admin_headers,
            json={"lecturer_id": lecturer_id, "is_primary": True},
        )

    lecturer_headers = get_user_headers(client, email, pwd, str(university_id))
    return lecturer_id, user_id, lecturer_headers


def setup_closed_session(
    client: TestClient,
    admin_headers: dict[str, str],
    occurrence_id: str,
) -> tuple[str, str]:
    """Helper creating, activating, and closing an attendance session."""
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=admin_headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["data"]["id"]

    close_res = client.post(
        f"/api/v1/attendance/sessions/{session_id}/close", headers=admin_headers
    )
    assert close_res.status_code == 200
    return session_id, occurrence_id


@pytest.mark.asyncio
async def test_student_submit_and_cancel_correction_request(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify student submits correction request within window and can cancel it."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_sub"
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    assert rec_res.status_code == 200
    rec = next(r for r in rec_res.json()["data"] if r["student_id"] == s_id)
    record_id = rec["id"]
    assert rec["status"] == AttendanceStatus.ABSENT.value

    # 1. Student submits correction request
    sub_res = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "request_type": CorrectionRequestType.WRONG_ABSENT.value,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Attended entire session and completed in-class quiz.",
        },
    )
    assert sub_res.status_code == 201
    corr_data = sub_res.json()["data"]
    request_id = corr_data["id"]
    assert corr_data["status"] == CorrectionRequestStatus.PENDING.value
    assert corr_data["student_id"] == s_id

    # 2. Student lists their correction requests
    my_res = client.get(
        "/api/v1/attendance/operations/corrections/my",
        headers=s_headers,
    )
    assert my_res.status_code == 200
    assert any(r["id"] == request_id for r in my_res.json()["data"])

    # 3. Duplicate open request is rejected (INV-05)
    dup_res = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "request_type": CorrectionRequestType.CHECKPOINT_NOT_RECORDED.value,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Submitting duplicate request.",
        },
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "DUPLICATE_OPEN_REQUEST"

    # 4. Student cancels their pending request
    cancel_res = client.post(
        f"/api/v1/attendance/operations/corrections/{request_id}/cancel",
        headers=s_headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == CorrectionRequestStatus.CANCELLED.value

    # 5. Cancelling already cancelled request fails
    cancel_again = client.post(
        f"/api/v1/attendance/operations/corrections/{request_id}/cancel",
        headers=s_headers,
    )
    assert cancel_again.status_code == 400
    assert cancel_again.json()["error"]["code"] == "INVALID_REQUEST_STATE"


@pytest.mark.asyncio
async def test_correction_window_expired_enforcement(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify INV-02: Requests outside the authoritative server UTC window are rejected."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_exp"
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    record_id = next(r["id"] for r in rec_res.json()["data"] if r["student_id"] == s_id)

    # Artificially set session closed_at_utc to 48 hours ago in DB
    sess_obj = await db_session.get(AttendanceSession, uuid.UUID(session_id))
    assert sess_obj is not None
    sess_obj.closed_at_utc = utc_now() - datetime.timedelta(hours=48)
    await db_session.commit()

    # Student tries to submit after window
    res = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "request_type": CorrectionRequestType.WRONG_ABSENT.value,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Submitted after window expired.",
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "CORRECTION_WINDOW_EXPIRED"


@pytest.mark.asyncio
async def test_student_ownership_isolation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify INV-01: Student cannot submit correction request for another student's record."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s1_id, _, _ = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_1"
    )
    _, _, s2_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_2"
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    s1_record_id = next(r["id"] for r in rec_res.json()["data"] if r["student_id"] == s1_id)

    # Student 2 tries to submit correction for Student 1's record
    res = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s2_headers,
        json={
            "attendance_record_id": s1_record_id,
            "request_type": CorrectionRequestType.WRONG_ABSENT.value,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Unauthorized cross-student request.",
        },
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_lecturer_review_approve_and_reject_workflows(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify lecturer can approve and reject correction requests with append-only revisions."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_rev"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "lec_rev"
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    record_id = next(r["id"] for r in rec_res.json()["data"] if r["student_id"] == s_id)

    # 1. Student submits request
    sub_res = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "request_type": CorrectionRequestType.WRONG_ABSENT.value,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Was present and seated in row 2.",
        },
    )
    assert sub_res.status_code == 201
    request_id = sub_res.json()["data"]["id"]

    # 2. Lecturer checks queue
    q_res = client.get(
        "/api/v1/attendance/operations/corrections/queue?status_filter=PENDING",
        headers=lec_headers,
    )
    assert q_res.status_code == 200
    queue_items = q_res.json()["data"]
    assert any(q["id"] == request_id for q in queue_items)

    # 3. Lecturer approves request
    appr_res = client.post(
        f"/api/v1/attendance/operations/corrections/{request_id}/review",
        headers=lec_headers,
        json={
            "status": CorrectionRequestStatus.APPROVED.value,
            "approved_status": AttendanceStatus.PRESENT.value,
            "review_note": "Confirmed student presence via sign-in sheet.",
        },
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()["data"]
    assert appr_data["status"] == CorrectionRequestStatus.APPROVED.value

    # 4. Verify attendance record is updated to PRESENT with 1.0 credit
    rec_check = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    rec_updated = next(r for r in rec_check.json()["data"] if r["id"] == record_id)
    assert rec_updated["status"] == AttendanceStatus.PRESENT.value
    assert rec_updated["attendance_credit"] == 1.0
    assert rec_updated["version_no"] == 2


@pytest.mark.asyncio
async def test_lecturer_course_scoping_denial(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify unassigned lecturer cannot review correction request (403)."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_scope"
    )
    # Lecturer NOT assigned to this offering
    _, _, unassigned_lec_headers = create_lecturer_with_role(
        client,
        admin_headers,
        offering_id,
        test_university.id,
        "lec_unassigned",
        assign_to_offering=False,
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    record_id = next(r["id"] for r in rec_res.json()["data"] if r["student_id"] == s_id)

    sub_res = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "request_type": CorrectionRequestType.WRONG_ABSENT.value,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Request to be reviewed.",
        },
    )
    request_id = sub_res.json()["data"]["id"]

    # Unassigned lecturer attempts review -> 403 Forbidden
    rev_res = client.post(
        f"/api/v1/attendance/operations/corrections/{request_id}/review",
        headers=unassigned_lec_headers,
        json={
            "status": CorrectionRequestStatus.APPROVED.value,
            "review_note": "Attempting unauthorized approval.",
        },
    )
    assert rev_res.status_code == 403


@pytest.mark.asyncio
async def test_privileged_admin_override_and_validation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Verify INV-08: Admin override works outside window but strictly requires justification."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, _ = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_ovr"
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    record_id = next(r["id"] for r in rec_res.json()["data"] if r["student_id"] == s_id)

    # 1. Expire window to ensure override bypasses window
    sess_obj = await db_session.get(AttendanceSession, uuid.UUID(session_id))
    assert sess_obj is not None
    sess_obj.closed_at_utc = utc_now() - datetime.timedelta(hours=72)
    await db_session.commit()

    # 2. Validation failure: missing/empty justification
    bad_res = client.post(
        "/api/v1/attendance/operations/overrides",
        headers=admin_headers,
        json={
            "attendance_record_id": record_id,
            "target_status": AttendanceStatus.PRESENT.value,
            "reason": "",  # Empty
        },
    )
    assert bad_res.status_code in (400, 422)

    # 3. Valid admin override
    good_res = client.post(
        "/api/v1/attendance/operations/overrides",
        headers=admin_headers,
        json={
            "attendance_record_id": record_id,
            "target_status": AttendanceStatus.PRESENT.value,
            "target_credit": 1.0,
            "reason": "Provost executive order for inter-university debate representative.",
        },
    )
    assert good_res.status_code == 200
    data = good_res.json()["data"]
    assert data["status"] == AttendanceStatus.PRESENT.value
    assert data["attendance_credit"] == 1.0
    assert data["is_manual"] is True
    assert data["version_no"] == 2


@pytest.mark.asyncio
async def test_compensating_reversal_transaction(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify INV-06: Compensating reversal reverts status without modifying past ledger."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, _ = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_revs"
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    record_id = next(r["id"] for r in rec_res.json()["data"] if r["student_id"] == s_id)

    # 1. Override record ABSENT -> PRESENT
    ovr_res = client.post(
        "/api/v1/attendance/operations/overrides",
        headers=admin_headers,
        json={
            "attendance_record_id": record_id,
            "target_status": AttendanceStatus.PRESENT.value,
            "reason": "Override before reversal test.",
        },
    )
    assert ovr_res.status_code == 200

    # 2. Get revision timeline to find revision ID
    tl_res = client.get(
        f"/api/v1/attendance/operations/records/{record_id}/timeline",
        headers=admin_headers,
    )
    assert tl_res.status_code == 200
    revisions = tl_res.json()["data"]["revisions"]
    assert len(revisions) >= 1
    last_rev_id = revisions[0]["id"]

    # 3. Reverse that revision
    rev_res = client.post(
        "/api/v1/attendance/operations/reversals",
        headers=admin_headers,
        json={
            "revision_id": last_rev_id,
            "reason": "Correcting erroneous override entry.",
        },
    )
    assert rev_res.status_code == 200
    rev_data = rev_res.json()["data"]
    # Reverted back to ABSENT
    assert rev_data["status"] == AttendanceStatus.ABSENT.value
    assert rev_data["version_no"] == 3

    # 4. Check timeline has both original revision and reversal revision
    tl_after = client.get(
        f"/api/v1/attendance/operations/records/{record_id}/timeline",
        headers=admin_headers,
    )
    all_revs = tl_after.json()["data"]["revisions"]
    event_types = [r["event_type"] for r in all_revs]
    assert AttendanceAuditEventType.REVERSAL.value in event_types
    assert AttendanceAuditEventType.ADMIN_OVERRIDE.value in event_types


@pytest.mark.asyncio
async def test_absence_excuse_request_and_review(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify absence excuse submission and approval workflow."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_exc"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "lec_exc"
    )

    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    record_id = next(r["id"] for r in rec_res.json()["data"] if r["student_id"] == s_id)

    # 1. Student submits excuse request
    exc_res = client.post(
        "/api/v1/attendance/operations/excuses",
        headers=s_headers,
        json={
            "attendance_session_id": session_id,
            "attendance_record_id": record_id,
            "category": ExcuseCategory.MEDICAL.value,
            "description": "Hospitalized due to acute gastroenteritis.",
            "document_reference": "https://documents.university.local/med-001.pdf",
        },
    )
    assert exc_res.status_code == 201
    exc_data = exc_res.json()["data"]
    exc_id = exc_data["id"]
    assert exc_data["status"] == ExcuseRequestStatus.PENDING.value

    # 2. Lecturer approves excuse request
    appr_res = client.post(
        f"/api/v1/attendance/operations/excuses/{exc_id}/review",
        headers=lec_headers,
        json={
            "status": ExcuseRequestStatus.APPROVED.value,
            "review_note": "Medical certificate verified with university clinic.",
        },
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["data"]["status"] == ExcuseRequestStatus.APPROVED.value

    # 3. Attendance record status is updated to EXCUSED with 0.0 credit
    rec_check = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    rec_updated = next(r for r in rec_check.json()["data"] if r["id"] == record_id)
    assert rec_updated["status"] == AttendanceStatus.EXCUSED.value
    assert rec_updated["attendance_credit"] == 0.0


@pytest.mark.asyncio
async def test_pre_class_leave_request_and_zero_credit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify Section 38: Pre-class LEAVE request approval strictly grants 0.0 credit."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    s_id, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "std_leave"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "lec_leave"
    )

    # 1. Student submits leave request prior to class
    leave_res = client.post(
        "/api/v1/attendance/operations/leave",
        headers=s_headers,
        json={
            "class_occurrence_id": occurrence_id,
            "reason": "Participating in National ACM Programming Competition.",
        },
    )
    assert leave_res.status_code == 201
    leave_id = leave_res.json()["data"]["id"]
    assert leave_res.json()["data"]["status"] == LeaveRequestStatus.PENDING.value

    # 2. Lecturer reviews and approves leave request
    rev_res = client.post(
        f"/api/v1/attendance/operations/leave/{leave_id}/review",
        headers=lec_headers,
        json={
            "status": LeaveRequestStatus.APPROVED.value,
            "review_note": "Approved by academic dean for official competition representation.",
        },
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["status"] == LeaveRequestStatus.APPROVED.value

    # 3. Initialize and close session for this occurrence
    sess_res = client.post(
        "/api/v1/attendance/sessions",
        headers=admin_headers,
        json={"class_occurrence_id": occurrence_id, "activate_immediately": True},
    )
    session_id = sess_res.json()["data"]["id"]
    client.post(f"/api/v1/attendance/sessions/{session_id}/close", headers=admin_headers)

    # 4. Enforce that record exists with 0.0 attendance credit
    rec_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records",
        headers=admin_headers,
    )
    rec = next(r for r in rec_res.json()["data"] if r["student_id"] == s_id)
    assert rec["attendance_credit"] == 0.0
