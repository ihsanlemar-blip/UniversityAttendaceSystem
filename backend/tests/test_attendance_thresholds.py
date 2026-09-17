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

    # 2. Roster report on empty offering
    roster_res = client.get(
        f"/api/v1/reports/attendance/course-offerings/{offering_id}",
        headers=admin_headers,
    )
    assert roster_res.status_code == 200
    data = roster_res.json()["data"]
    assert data["total_enrolled"] == 0
    assert data["total_sessions_conducted"] == 0
    assert data["average_attendance_percentage"] == 100.0
