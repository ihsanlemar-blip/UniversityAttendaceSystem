"""End-to-End integration test suite for Attendance Operations, Review Queues & Workflows.

Verifies:
- Correction approve/reject lifecycle with immutable revision ledger and timeline.
- Absence excuse lifecycle and queue integration.
- Pre-class leave lifecycle and Section 38 0-credit invariant.
- Manual review queue and confirmation endpoint.
- Atomic, per-item safe bulk review operations.
- Stale review conflict handling (REQUEST_ALREADY_RESOLVED / DUPLICATE_OPEN_REQUEST).
- Operational dashboard counts and student record eligibility checks.
- Cross-tenant isolation and security boundaries.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.core.constants import (
    AttendanceStatus,
    CorrectionRequestStatus,
    CorrectionRequestType,
    ExcuseCategory,
    ExcuseRequestStatus,
    LeaveRequestStatus,
    SystemRole,
)
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_corrections import (
    create_lecturer_with_role,
    create_student_with_role,
    setup_closed_session,
)
from backend.tests.test_attendance_operations_rbac import create_user_with_role
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_correction_full_lifecycle_and_timeline(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify correction request submission, reviewer approval, and immutable timeline retrieval."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    _, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_c1"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_lec1"
    )
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    # Fetch student's record
    records_res = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers
    )
    assert records_res.status_code == 200
    record = records_res.json()["data"][0]
    record_id = record["id"]

    # Check eligibility endpoint
    elig_res = client.get(
        f"/api/v1/attendance/operations/records/{record_id}/eligibility",
        headers=s_headers,
    )
    assert elig_res.status_code == 200
    elig_data = elig_res.json()["data"]
    assert elig_data["eligible_for_correction"] is True
    assert elig_data["has_open_correction"] is False

    # Student submits correction request
    submit_res = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "request_type": CorrectionRequestType.TECHNICAL_FAILURE.value,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Scanner camera malfunction during middle checkpoint window",
            "supporting_note": "Lecturer verified student seated in front row",
        },
    )
    assert submit_res.status_code == 201
    req_id = submit_res.json()["data"]["id"]

    # Check eligibility updated (duplicate open request prevented)
    elig_res2 = client.get(
        f"/api/v1/attendance/operations/records/{record_id}/eligibility",
        headers=s_headers,
    )
    assert elig_res2.status_code == 200
    assert elig_res2.json()["data"]["eligible_for_correction"] is False
    assert elig_res2.json()["data"]["has_open_correction"] is True

    # Reviewer inspects correction queue
    queue_res = client.get(
        "/api/v1/attendance/operations/corrections/queue",
        headers=lec_headers,
        params={"status_filter": CorrectionRequestStatus.PENDING.value},
    )
    assert queue_res.status_code == 200
    queue_items = queue_res.json()["data"]
    assert any(q["id"] == req_id for q in queue_items)

    # Reviewer approves correction
    review_res = client.post(
        f"/api/v1/attendance/operations/corrections/{req_id}/review",
        headers=lec_headers,
        json={
            "status": CorrectionRequestStatus.APPROVED.value,
            "approved_status": AttendanceStatus.PRESENT.value,
            "review_note": "Verified physical presence via laboratory workstation log",
        },
    )
    assert review_res.status_code == 200
    assert review_res.json()["data"]["status"] == CorrectionRequestStatus.APPROVED.value

    # Check record state
    rec_check = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers
    )
    updated_rec = next(r for r in rec_check.json()["data"] if r["id"] == record_id)
    assert updated_rec["status"] == AttendanceStatus.PRESENT.value
    assert float(updated_rec["attendance_credit"]) == 1.0
    assert updated_rec["is_manual"] is True

    # Check complete immutable revision timeline
    timeline_res = client.get(
        f"/api/v1/attendance/operations/records/{record_id}/timeline",
        headers=admin_headers,
    )
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()["data"]
    assert timeline["current_status"] == AttendanceStatus.PRESENT.value
    assert len(timeline["revisions"]) >= 2
    event_types = [r["event_type"] for r in timeline["revisions"]]
    assert "CORRECTION_REQUESTED" in event_types
    assert "CORRECTION_APPROVED" in event_types


@pytest.mark.asyncio
async def test_excuse_request_lifecycle_and_queues(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify absence excuse submission, queue visibility, and approval."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    _, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_exc"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_lecexc"
    )
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    # Student submits absence excuse
    exc_res = client.post(
        "/api/v1/attendance/operations/excuses",
        headers=s_headers,
        json={
            "attendance_session_id": session_id,
            "category": ExcuseCategory.MEDICAL.value,
            "description": "Medical clinic certificate prescribed strict isolation",
            "document_reference": "CLINIC-REF-2026-0081",
        },
    )
    assert exc_res.status_code == 201
    exc_id = exc_res.json()["data"]["id"]

    # Student views their excuses
    my_exc = client.get("/api/v1/attendance/operations/excuses/my", headers=s_headers)
    assert my_exc.status_code == 200
    assert any(e["id"] == exc_id for e in my_exc.json()["data"])

    # Reviewer inspects excuse queue
    q_res = client.get(
        "/api/v1/attendance/operations/excuses/queue",
        headers=lec_headers,
        params={"status_filter": ExcuseRequestStatus.PENDING.value},
    )
    assert q_res.status_code == 200
    assert any(e["id"] == exc_id for e in q_res.json()["data"])

    # Reviewer approves excuse
    rev_res = client.post(
        f"/api/v1/attendance/operations/excuses/{exc_id}/review",
        headers=lec_headers,
        json={
            "status": ExcuseRequestStatus.APPROVED.value,
            "review_note": "Doctor note validated with health center",
        },
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["status"] == ExcuseRequestStatus.APPROVED.value

    # Verify student's record transitioned to EXCUSED
    records = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers
    ).json()["data"]
    student_rec = records[0]
    assert student_rec["status"] == AttendanceStatus.EXCUSED.value


@pytest.mark.asyncio
async def test_pre_class_leave_lifecycle_zero_credit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify pre-class leave submission, approval, and Section 38 zero-credit invariant."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    _, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_leave"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_lecleave"
    )

    # Student submits pre-class leave for scheduled class occurrence
    leave_res = client.post(
        "/api/v1/attendance/operations/leave",
        headers=s_headers,
        json={
            "class_occurrence_id": occurrence_id,
            "reason": "Authorized delegation for collegiate competition",
        },
    )
    assert leave_res.status_code == 201
    leave_id = leave_res.json()["data"]["id"]

    # Student views their leaves
    my_leaves = client.get("/api/v1/attendance/operations/leave/my", headers=s_headers)
    assert my_leaves.status_code == 200
    assert any(item["id"] == leave_id for item in my_leaves.json()["data"])

    # Reviewer inspects leave queue
    l_queue = client.get("/api/v1/attendance/operations/leave/queue", headers=lec_headers)
    assert l_queue.status_code == 200
    assert any(item["id"] == leave_id for item in l_queue.json()["data"])

    # Activate and close attendance session
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    # Reviewer approves leave
    rev_res = client.post(
        f"/api/v1/attendance/operations/leave/{leave_id}/review",
        headers=lec_headers,
        json={
            "status": LeaveRequestStatus.APPROVED.value,
            "review_note": "Department head signed competition pass",
        },
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["status"] == LeaveRequestStatus.APPROVED.value

    # Invariant check: Status is LEAVE and credit is exactly 0.00
    records = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers
    ).json()["data"]
    assert records[0]["status"] == AttendanceStatus.LEAVE.value
    assert float(records[0]["attendance_credit"]) == 0.0


@pytest.mark.asyncio
async def test_manual_review_queue_and_confirm(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify manual review queue listing and deliberate confirmation."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    _, _, _ = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_man"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_lecman"
    )
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    rec_res = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers)
    record = rec_res.json()["data"][0]
    record_id = record["id"]

    # Put record into manual state via admin override
    ov_res = client.post(
        "/api/v1/attendance/operations/overrides",
        headers=admin_headers,
        json={
            "attendance_record_id": record_id,
            "target_status": AttendanceStatus.LATE.value,
            "reason": "BLE anomaly flagged during active session",
        },
    )
    assert ov_res.status_code == 200

    # Query manual reviews queue
    man_queue = client.get("/api/v1/attendance/operations/manual-reviews", headers=lec_headers)
    assert man_queue.status_code == 200
    items = man_queue.json()["data"]
    assert any(m["record_id"] == record_id for m in items)

    # Confirm manual review with reason
    confirm_res = client.post(
        f"/api/v1/attendance/operations/manual-reviews/{record_id}/confirm",
        headers=lec_headers,
        json={
            "target_status": AttendanceStatus.PRESENT.value,
            "reason": "Manual sign-in sheet corroborated with student signature",
        },
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["data"]["status"] == AttendanceStatus.PRESENT.value
    assert float(confirm_res.json()["data"]["attendance_credit"]) == 1.0


@pytest.mark.asyncio
async def test_bulk_review_atomicity_and_per_item_safety(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify bulk review isolates per-item outcomes safely without cascading aborts."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    _, _, s1_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_bk1"
    )
    _, _, s2_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_bk2"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_lecbk"
    )
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    records = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers
    ).json()["data"]
    r1_id = records[0]["id"]
    r2_id = records[1]["id"]

    # Submit 2 valid requests
    c1 = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s1_headers,
        json={
            "attendance_record_id": r1_id,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Battery died right before QR scan checkpoint",
        },
    ).json()["data"]["id"]

    c2 = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s2_headers,
        json={
            "attendance_record_id": r2_id,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Network timeout during attendance token submission",
        },
    ).json()["data"]["id"]

    fake_id = str(uuid.uuid4())

    # Bulk review: 2 valid + 1 non-existent item
    bulk_res = client.post(
        "/api/v1/attendance/operations/bulk-review",
        headers=lec_headers,
        json={
            "request_type": "correction",
            "request_ids": [c1, fake_id, c2],
            "status": CorrectionRequestStatus.APPROVED.value,
            "approved_status": AttendanceStatus.PRESENT.value,
            "review_note": "Batch approved verified physical attendance",
        },
    )
    assert bulk_res.status_code == 200
    summary = bulk_res.json()["data"]
    assert summary["total"] == 3
    assert summary["succeeded"] == 2
    assert summary["failed"] == 1

    # Verify the 2 valid requests committed successfully
    res1 = client.get(
        f"/api/v1/attendance/operations/records/{r1_id}/timeline", headers=admin_headers
    ).json()["data"]
    assert res1["current_status"] == AttendanceStatus.PRESENT.value

    res2 = client.get(
        f"/api/v1/attendance/operations/records/{r2_id}/timeline", headers=admin_headers
    ).json()["data"]
    assert res2["current_status"] == AttendanceStatus.PRESENT.value


@pytest.mark.asyncio
async def test_stale_review_conflict_handling(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify attempting to review an already-resolved request raises conflict/domain error."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    _, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_stale"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_lecstale"
    )
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    record_id = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers
    ).json()["data"][0]["id"]

    req_id = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Submitted prior to window close",
        },
    ).json()["data"]["id"]

    # First review: succeeds
    res1 = client.post(
        f"/api/v1/attendance/operations/corrections/{req_id}/review",
        headers=lec_headers,
        json={
            "status": CorrectionRequestStatus.APPROVED.value,
            "review_note": "Initial resolution",
        },
    )
    assert res1.status_code == 200

    # Second review on already resolved request: fails with 400 REQUEST_ALREADY_RESOLVED
    res2 = client.post(
        f"/api/v1/attendance/operations/corrections/{req_id}/review",
        headers=lec_headers,
        json={
            "status": CorrectionRequestStatus.REJECTED.value,
            "review_note": "Conflicting second resolution",
        },
    )
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "REQUEST_ALREADY_RESOLVED"


@pytest.mark.asyncio
async def test_operations_dashboard_counts(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify operational counts endpoint returns correct pending numbers."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    _, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_counts"
    )
    _, _, lec_headers = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_leccounts"
    )
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    record_id = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers
    ).json()["data"][0]["id"]

    # Submit 1 correction
    client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Reason for count check",
        },
    )

    counts_res = client.get("/api/v1/attendance/operations/counts", headers=lec_headers)
    assert counts_res.status_code == 200
    counts = counts_res.json()["data"]
    assert counts["pending_corrections"] >= 1
    assert "pending_excuses" in counts
    assert "pending_leaves" in counts
    assert "manual_reviews" in counts


@pytest.mark.asyncio
async def test_cross_tenant_isolation_and_auditor_permissions(
    client: TestClient,
    test_university: University,
    second_university: University,
    test_admin_user: User,
    second_admin_user: User,
) -> None:
    """Verify tenant isolation: University B user cannot access University A requests."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    _, _, s_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "e2e_uniA"
    )
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    record_id = client.get(
        f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers
    ).json()["data"][0]["id"]

    c_id = client.post(
        "/api/v1/attendance/operations/corrections",
        headers=s_headers,
        json={
            "attendance_record_id": record_id,
            "requested_status": AttendanceStatus.PRESENT.value,
            "reason": "Cross-tenant check",
        },
    ).json()["data"]["id"]

    # Create lecturer in University B (second_university) using second_admin_user
    admin_headers_b = get_admin_headers(client, second_admin_user, second_university)
    _, uni_b_lec_headers = create_user_with_role(
        client, admin_headers_b, second_university.id, SystemRole.LECTURER, "uniB_lec"
    )

    # University B lecturer attempts to review University A request -> 403 Forbidden
    res = client.post(
        f"/api/v1/attendance/operations/corrections/{c_id}/review",
        headers=uni_b_lec_headers,
        json={
            "status": CorrectionRequestStatus.APPROVED.value,
            "review_note": "Cross tenant attempt",
        },
    )
    assert res.status_code == 403

    # Auditor in University A can read timeline but cannot review
    _, auditor_headers = create_user_with_role(
        client, admin_headers, test_university.id, SystemRole.AUDITOR, "uniA_audit"
    )
    aud_timeline = client.get(
        f"/api/v1/attendance/operations/records/{record_id}/timeline",
        headers=auditor_headers,
    )
    assert aud_timeline.status_code == 200

    aud_review = client.post(
        f"/api/v1/attendance/operations/corrections/{c_id}/review",
        headers=auditor_headers,
        json={
            "status": CorrectionRequestStatus.APPROVED.value,
            "review_note": "Auditor review attempt",
        },
    )
    assert aud_review.status_code == 403
