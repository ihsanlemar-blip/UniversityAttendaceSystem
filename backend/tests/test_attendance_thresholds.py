"""Test suite for configurable attendance thresholds, boundary calculations, and neutral states."""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.constants import PolicyScopeType, ThresholdStatus
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.reports.service import ReportingService
from backend.tests.test_offerings import setup_academic_prerequisites
from backend.tests.test_users import get_admin_headers


def test_threshold_evaluation_boundaries() -> None:
    """Verify threshold evaluation correctly assigns neutral states across boundaries."""
    min_pct = 75.0
    margin = 5.0

    # Above threshold
    assert (
        ReportingService.evaluate_threshold(100.0, min_pct, margin)
        == ThresholdStatus.ABOVE_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(75.0, min_pct, margin)
        == ThresholdStatus.ABOVE_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(75.1, min_pct, margin)
        == ThresholdStatus.ABOVE_THRESHOLD.value
    )

    # Near threshold (within 5% margin: [70.0, 75.0))
    assert (
        ReportingService.evaluate_threshold(74.9, min_pct, margin)
        == ThresholdStatus.NEAR_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(70.0, min_pct, margin)
        == ThresholdStatus.NEAR_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(72.5, min_pct, margin)
        == ThresholdStatus.NEAR_THRESHOLD.value
    )

    # Below threshold (< 70.0)
    assert (
        ReportingService.evaluate_threshold(69.9, min_pct, margin)
        == ThresholdStatus.BELOW_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(50.0, min_pct, margin)
        == ThresholdStatus.BELOW_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(0.0, min_pct, margin)
        == ThresholdStatus.BELOW_THRESHOLD.value
    )

    # Custom threshold (80.0%, margin 10.0%)
    assert (
        ReportingService.evaluate_threshold(82.0, 80.0, 10.0)
        == ThresholdStatus.ABOVE_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(75.0, 80.0, 10.0)
        == ThresholdStatus.NEAR_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(69.0, 80.0, 10.0)
        == ThresholdStatus.BELOW_THRESHOLD.value
    )

    # Extreme boundaries: 0% threshold
    assert (
        ReportingService.evaluate_threshold(0.0, 0.0, 5.0) == ThresholdStatus.ABOVE_THRESHOLD.value
    )

    # Strict boundary check (Section 12 requirement: 74.99 -> BELOW, 75.00 -> meets, 75.01 -> meets)
    assert (
        ReportingService.evaluate_threshold(74.99, 75.0, margin=0.0)
        == ThresholdStatus.BELOW_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(75.00, 75.0, margin=0.0)
        == ThresholdStatus.ABOVE_THRESHOLD.value
    )
    assert (
        ReportingService.evaluate_threshold(75.01, 75.0, margin=0.0)
        == ThresholdStatus.ABOVE_THRESHOLD.value
    )


@pytest.mark.asyncio
async def test_policy_threshold_override_hierarchy(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify hierarchical policy resolution: Course policy overrides University default."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, admin_headers)

    # 1. Create Course Offering
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off_res.status_code == 201
    offering_id = off_res.json()["data"]["id"]

    # 2. Before any policy, threshold defaults to 75.0%
    rep_res1 = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}",
        headers=admin_headers,
    )
    assert rep_res1.status_code == 200
    assert rep_res1.json()["data"]["threshold_percentage"] == 75.0

    # 3. Create Course-level Attendance Policy with 80.0% threshold
    pol_res = client.post(
        "/api/v1/attendance/policies",
        headers=admin_headers,
        json={
            "name": "Course Specific 80 Policy",
            "scope_type": PolicyScopeType.COURSE.value,
            "course_id": course_id,
            "min_attendance_percentage": 80.0,
            "required_checkpoint_count": 2,
            "late_threshold_minutes": 15,
        },
    )
    assert pol_res.status_code == 201

    # 4. Offering now resolves to 80.0%
    rep_res2 = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}",
        headers=admin_headers,
    )
    assert rep_res2.status_code == 200
    assert rep_res2.json()["data"]["threshold_percentage"] == 80.0


@pytest.mark.asyncio
async def test_zero_denominator_report_safety(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """INVARIANT: Student with zero eligible sessions must not produce division by zero or NaN."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)
    course_id, semester_id, section_id, _ = setup_academic_prerequisites(client, admin_headers)

    # 1. Create Course Offering with no sessions conducted
    off_res = client.post(
        "/api/v1/course-offerings",
        headers=admin_headers,
        json={"course_id": course_id, "semester_id": semester_id, "section_id": section_id},
    )
    assert off_res.status_code == 201
    offering_id = off_res.json()["data"]["id"]

    # 2. Roster report on empty offering with no sessions conducted
    roster_res = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}",
        headers=admin_headers,
    )
    assert roster_res.status_code == 200
    data = roster_res.json()["data"]
    assert data["total_enrolled"] == 0
    assert data["total_sessions_conducted"] == 0
    assert data["average_attendance_percentage"] is None
    assert data["not_applicable_count"] == 0

    # 3. Enroll a student in this offering (0 sessions conducted)
    from backend.tests.test_attendance_corrections import create_student_with_role

    student_id, _, _ = create_student_with_role(
        client, admin_headers, offering_id, test_university.id, "zero"
    )

    # 4. Invariant: Student with 0 eligible sessions must be NOT_APPLICABLE with null percentage
    roster_res2 = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}",
        headers=admin_headers,
    )
    assert roster_res2.status_code == 200
    data2 = roster_res2.json()["data"]
    assert data2["total_enrolled"] == 1
    assert data2["average_attendance_percentage"] is None
    assert data2["above_threshold_count"] == 0
    assert data2["not_applicable_count"] == 1

    item = data2["roster"][0]
    assert item["eligible_sessions"] == 0
    assert item["attendance_percentage"] is None
    assert item["threshold_status"] == ThresholdStatus.NOT_APPLICABLE.value

    # 5. Multi-course Student Summary also evaluates to null overall average and NOT_APPLICABLE
    student_rep = client.get(
        f"/api/v1/reports/attendance/student/{student_id}",
        headers=admin_headers,
    )
    assert student_rep.status_code == 200
    s_data = student_rep.json()["data"]
    assert s_data["overall_average_percentage"] is None
    assert s_data["courses"][0]["eligible_sessions"] == 0
    assert s_data["courses"][0]["attendance_percentage"] is None
    assert s_data["courses"][0]["threshold_status"] == ThresholdStatus.NOT_APPLICABLE.value
