"""Targeted integration test suite for institutional attendance reporting engine.

Verifies:
- Student self-summary (/reports/attendance/student/me)
- Specific student report for Admin/Auditor (/reports/attendance/student/{id})
- Course offering roster report (/reports/attendance/course-offerings/{id})
- Session operational report (/reports/attendance/sessions/{id})
- Department aggregate report (/reports/attendance/department/{id})
- Faculty aggregate report (/reports/attendance/faculty/{id})
- Lecturer operational report (/reports/attendance/lecturers/{id})
- Revision awareness (has_revision flag when version_no > 1)
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.core.constants import AttendanceStatus, ThresholdStatus
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_attendance_corrections import (
    create_lecturer_with_role,
    create_student_with_role,
    setup_closed_session,
)
from backend.tests.test_attendance_policy import setup_class_occurrence
from backend.tests.test_users import get_admin_headers


@pytest.mark.asyncio
async def test_course_roster_and_student_summary_reports(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify course roster report and student self-summary calculation."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)

    # Create 2 students
    s1_id, _, s1_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "rep_s1"
    )
    s2_id, _, s2_headers = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "rep_s2"
    )

    # Setup closed session
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    # Fetch records and update s1 to PRESENT (credit 1.0) and s2 remains ABSENT (credit 0.0)
    rec_res = client.get(f"/api/v1/attendance/sessions/{session_id}/records", headers=admin_headers)
    assert rec_res.status_code == 200
    records = rec_res.json()["data"]

    # Use lecturer or admin override to mark s1 PRESENT
    s1_record = next(r for r in records if r["student_id"] == s1_id)
    override_res = client.post(
        f"/api/v1/attendance/records/{s1_record['id']}/override",
        headers=admin_headers,
        json={
            "status": AttendanceStatus.PRESENT.value,
            "reason": "Verified student attendance physically in class",
        },
    )
    assert override_res.status_code == 200

    # 1. Test Course Roster Report
    roster_res = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}",
        headers=admin_headers,
    )
    assert roster_res.status_code == 200
    roster_data = roster_res.json()["data"]
    assert roster_data["total_enrolled"] == 2
    assert roster_data["total_sessions_conducted"] == 1
    assert roster_data["threshold_percentage"] == 75.0

    roster_items = roster_data["roster"]
    assert len(roster_items) == 2

    s1_item = next(i for i in roster_items if i["student_id"] == s1_id)
    assert s1_item["eligible_sessions"] == 1
    assert s1_item["attendance_credit"] == 1.0
    assert s1_item["attendance_percentage"] == 100.0
    assert s1_item["threshold_status"] == ThresholdStatus.ABOVE_THRESHOLD.value
    assert s1_item["has_revision"] is True  # Due to override version > 1

    s2_item = next(i for i in roster_items if i["student_id"] == s2_id)
    assert s2_item["eligible_sessions"] == 1
    assert s2_item["attendance_credit"] == 0.0
    assert s2_item["attendance_percentage"] == 0.0
    assert s2_item["threshold_status"] == ThresholdStatus.BELOW_THRESHOLD.value

    # 2. Test Student Self-Summary (/reports/attendance/student/me)
    s1_sum_res = client.get("/api/v1/reports/attendance/student/me", headers=s1_headers)
    assert s1_sum_res.status_code == 200
    s1_courses = s1_sum_res.json()["data"]["courses"]
    assert len(s1_courses) >= 1
    my_off = next(c for c in s1_courses if c["course_offering_id"] == offering_id)
    assert my_off["attendance_percentage"] == 100.0
    assert my_off["threshold_status"] == ThresholdStatus.ABOVE_THRESHOLD.value

    # 3. Test Specific Student Report for Admin (/reports/attendance/student/{id})
    s2_sum_res = client.get(f"/api/v1/reports/attendance/student/{s2_id}", headers=admin_headers)
    assert s2_sum_res.status_code == 200
    s2_courses = s2_sum_res.json()["data"]["courses"]
    s2_off = next(c for c in s2_courses if c["course_offering_id"] == offering_id)
    assert s2_off["attendance_percentage"] == 0.0
    assert s2_off["threshold_status"] == ThresholdStatus.BELOW_THRESHOLD.value


@pytest.mark.asyncio
async def test_session_operational_report(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify session operational checkpoint report metrics."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    create_student_with_role(client, admin_headers, offering_id, test_university.id, "sess_rep_s1")
    session_id, _ = setup_closed_session(client, admin_headers, occurrence_id)

    res = client.get(
        f"/api/v1/reports/attendance/sessions/{session_id}",
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["session_id"] == session_id
    assert data["status"] == "CLOSED"
    assert data["roster_count"] >= 1
    assert "start_credited_count" in data
    assert "middle_credited_count" in data
    assert "end_credited_count" in data


@pytest.mark.asyncio
async def test_department_and_faculty_aggregate_reports(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify department and faculty hierarchical aggregate roll-ups."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)

    # 1. Create Faculty
    fac_res = client.post(
        "/api/v1/academic-units",
        headers=admin_headers,
        json={
            "name": f"Faculty of Science {uuid.uuid4().hex[:4]}",
            "code": f"FS_{uuid.uuid4().hex[:4]}".upper(),
            "unit_type": "FACULTY",
        },
    )
    assert fac_res.status_code == 201
    fac_id = fac_res.json()["data"]["id"]

    # 2. Create Department under Faculty
    dept_res = client.post(
        "/api/v1/academic-units",
        headers=admin_headers,
        json={
            "name": f"Department of CS {uuid.uuid4().hex[:4]}",
            "code": f"CS_{uuid.uuid4().hex[:4]}".upper(),
            "unit_type": "DEPARTMENT",
            "parent_id": fac_id,
        },
    )
    assert dept_res.status_code == 201
    dept_id = dept_res.json()["data"]["id"]

    # Query Department Report (empty offerings initially)
    dept_rep = client.get(
        f"/api/v1/reports/attendance/department/{dept_id}",
        headers=admin_headers,
    )
    assert dept_rep.status_code == 200
    d_data = dept_rep.json()["data"]
    assert d_data["academic_unit_id"] == dept_id
    assert d_data["total_offerings"] == 0

    # Query Faculty Report
    fac_rep = client.get(
        f"/api/v1/reports/attendance/faculty/{fac_id}",
        headers=admin_headers,
    )
    assert fac_rep.status_code == 200
    f_data = fac_rep.json()["data"]
    assert f_data["academic_unit_id"] == fac_id
    assert len(f_data["departments"]) >= 1


@pytest.mark.asyncio
async def test_lecturer_operational_report(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify neutral operational metrics on scheduled vs conducted sessions."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    _, offering_id, occurrence_id = setup_class_occurrence(client, admin_headers)
    lec_id, _, _ = create_lecturer_with_role(
        client, admin_headers, offering_id, test_university.id, "lec_rep"
    )
    setup_closed_session(client, admin_headers, occurrence_id)

    res = client.get(
        f"/api/v1/reports/attendance/lecturers/{lec_id}",
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["lecturer_id"] == lec_id
    assert "sessions_scheduled" in data
    assert "sessions_conducted" in data
    assert data["sessions_scheduled"] >= 0
    assert data["sessions_conducted"] >= 0


@pytest.mark.asyncio
async def test_dashboard_summary_endpoint(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Test that GET dashboard summary returns authoritative aggregated counts."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)

    res = client.get(
        "/api/v1/reports/attendance/dashboard/summary",
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]

    assert "total_students" in data
    assert "total_lecturers" in data
    assert "total_course_offerings" in data
    assert "today_occurrences_count" in data
    assert "active_attendance_sessions_count" in data
    assert "pending_corrections_count" in data
    assert "pending_excuses_count" in data
    assert "pending_leaves_count" in data
    assert "open_risk_signals_count" in data
    assert "pending_devices_count" in data
    assert "generated_at_utc" in data

    assert isinstance(data["total_students"], int)
    assert isinstance(data["total_lecturers"], int)
    assert isinstance(data["total_course_offerings"], int)
    assert data["total_students"] >= 0
