"""API router for attendance reports, analytics, and safe spreadsheet exports."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import ExportFormat, PermissionCode, SystemRole
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import ForbiddenException, NotFoundException
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.course_offering import CourseOffering
from backend.app.models.lecturer import Lecturer
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission
from backend.app.reports.exports import ExportService
from backend.app.reports.schemas import (
    CourseRosterReportResponse,
    DashboardSummaryResponse,
    DepartmentAggregateReportResponse,
    FacultyAggregateReportResponse,
    LecturerOperationalReportResponse,
    SessionReportResponse,
    StudentAttendanceSummaryResponse,
)
from backend.app.reports.service import ReportingService

router = APIRouter(prefix="/reports/attendance", tags=["Attendance Reports & Analytics"])


async def _verify_offering_access(
    db: AsyncSession,
    user: User,
    offering_id: uuid.UUID,
) -> None:
    """Ensure caller has permission to view course offering report."""
    off_stmt = select(CourseOffering).where(
        CourseOffering.id == offering_id,
        CourseOffering.university_id == user.university_id,
    )
    offering = (await db.execute(off_stmt)).scalar_one_or_none()
    if not offering:
        raise NotFoundException("CourseOffering", offering_id)

    # If caller has role LECTURER, check assignment to this offering
    l_stmt = select(Lecturer).where(
        Lecturer.user_id == user.id,
        Lecturer.university_id == user.university_id,
    )
    lecturer = (await db.execute(l_stmt)).scalar_one_or_none()
    if lecturer:
        # Check lecturer assignment
        from backend.app.models.lecturer_assignment import LecturerAssignment

        la_stmt = select(LecturerAssignment).where(
            LecturerAssignment.course_offering_id == offering_id,
            LecturerAssignment.lecturer_id == lecturer.id,
        )
        assigned = (await db.execute(la_stmt)).scalar_one_or_none()
        if not assigned:
            # Check if assigned via class occurrence
            from backend.app.models.class_occurrence import ClassOccurrence

            occ_stmt = select(ClassOccurrence).where(
                ClassOccurrence.course_offering_id == offering_id,
                ClassOccurrence.lecturer_id == lecturer.id,
            )
            occ_assigned = (await db.execute(occ_stmt)).scalar_one_or_none()
            if not occ_assigned:
                raise ForbiddenException("You are not assigned to instruct this course offering.")


async def _verify_unit_subtree_access(
    db: AsyncSession,
    user: User,
    unit_id: uuid.UUID,
) -> None:
    """Verify Department/Faculty Admin caller does not exceed subtree authority."""
    unit = await db.get(AcademicUnit, unit_id)
    if not unit or unit.university_id != user.university_id:
        raise NotFoundException("AcademicUnit", unit_id)

    # Check caller's role assignments if not SUPER_ADMIN or UNIVERSITY_ADMIN
    from backend.app.models.role import Role
    from backend.app.models.role_assignment import RoleAssignment

    ra_stmt = (
        select(RoleAssignment)
        .join(Role, RoleAssignment.role_id == Role.id)
        .where(
            RoleAssignment.user_id == user.id,
            RoleAssignment.revoked_at.is_(None),
        )
    )
    assignments = list((await db.execute(ra_stmt)).scalars().all())

    # If user has University Admin or Auditor or Super Admin, access is granted
    high_roles = {
        SystemRole.SUPER_ADMIN.value,
        SystemRole.UNIVERSITY_ADMIN.value,
        SystemRole.AUDITOR.value,
    }
    roles = [await db.get(Role, a.role_id) for a in assignments]
    role_codes = {r.code for r in roles if r}
    if high_roles.intersection(role_codes):
        return

    # Check academic unit scope
    scoped_unit_ids = {a.scope_id for a in assignments if a.scope_type == "ACADEMIC_UNIT"}
    if not scoped_unit_ids:
        raise ForbiddenException("User lacks authorization for this academic unit.")

    if unit_id in scoped_unit_ids:
        return

    # Check parent unit hierarchy
    curr_id = unit.parent_id
    while curr_id:
        if curr_id in scoped_unit_ids:
            return
        parent_unit = await db.get(AcademicUnit, curr_id)
        curr_id = parent_unit.parent_id if parent_unit else None

    raise ForbiddenException("Academic unit is outside of your authorized subtree.")


# =============================================================================
# 1. Student Attendance Reports
# =============================================================================


@router.get(
    "/student/me",
    response_model=StandardResponse[StudentAttendanceSummaryResponse],
    summary="Get authenticated student's attendance summary across all courses",
)
async def get_my_attendance_summary(
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.ATTENDANCE_SELF_READ)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    semester_id: Annotated[uuid.UUID | None, Query(description="Optional semester filter")] = None,
) -> StandardResponse[StudentAttendanceSummaryResponse]:
    """Derive caller identity and return multi-course attendance summary.

    Enforces IDOR prevention: students cannot specify or view another student's report.
    """
    s_stmt = select(Student).where(
        Student.user_id == current_user.id,
        Student.university_id == current_user.university_id,
    )
    student = (await db.execute(s_stmt)).scalar_one_or_none()
    if not student:
        raise NotFoundException(
            "Student", current_user.id, "Student profile for current user not found."
        )

    report = await ReportingService.get_student_attendance_summary(
        db=db,
        university_id=current_user.university_id,
        student_id=student.id,
        semester_id=semester_id,
    )
    return StandardResponse(data=StudentAttendanceSummaryResponse(**report))


@router.get(
    "/student/{student_id}",
    response_model=StandardResponse[StudentAttendanceSummaryResponse],
    summary="Get attendance report for a specific student (Admin / Auditor)",
)
async def get_student_attendance_report(
    student_id: uuid.UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_READ, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    semester_id: Annotated[uuid.UUID | None, Query(description="Optional semester filter")] = None,
) -> StandardResponse[StudentAttendanceSummaryResponse]:
    """Return attendance summary for a student with tenant isolation."""
    report = await ReportingService.get_student_attendance_summary(
        db=db,
        university_id=current_user.university_id,
        student_id=student_id,
        semester_id=semester_id,
    )
    return StandardResponse(data=StudentAttendanceSummaryResponse(**report))


# =============================================================================
# 2. Course Offering Roster Reports
# =============================================================================


@router.get(
    "/course-offerings/{offering_id}",
    response_model=StandardResponse[CourseRosterReportResponse],
    summary="Get course offering roster attendance report",
)
async def get_course_roster_report(
    offering_id: uuid.UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_READ, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    threshold_status: Annotated[
        str | None,
        Query(
            description=(
                "Filter by threshold status: ABOVE_THRESHOLD, NEAR_THRESHOLD, BELOW_THRESHOLD"
            )
        ),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
) -> StandardResponse[CourseRosterReportResponse]:
    """Return paginated course roster report with attendance percentages and threshold status."""
    await _verify_offering_access(db, current_user, offering_id)

    report = await ReportingService.get_course_roster_report(
        db=db,
        university_id=current_user.university_id,
        course_offering_id=offering_id,
        threshold_filter=threshold_status,
        page=page,
        page_size=page_size,
    )
    return StandardResponse(data=CourseRosterReportResponse(**report))


@router.get(
    "/course-offerings/{offering_id}/export",
    summary="Export course offering roster report to CSV or XLSX",
)
async def export_course_roster_report(
    offering_id: uuid.UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_EXPORT, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    threshold_status: Annotated[str | None, Query()] = None,
    format: Annotated[str, Query(description="Export format: CSV or XLSX")] = "CSV",
) -> Response:
    """Generate and stream secure spreadsheet export of course roster report."""
    await _verify_offering_access(db, current_user, offering_id)

    report = await ReportingService.get_course_roster_report(
        db=db,
        university_id=current_user.university_id,
        course_offering_id=offering_id,
        threshold_filter=threshold_status,
        page=1,
        page_size=5000,
    )

    fmt = format.upper().strip()
    c_code = report.get("course_code", "course")
    if fmt == ExportFormat.XLSX.value:
        content = ExportService.export_course_roster_xlsx(report)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"attendance_roster_{c_code}.xlsx"
    else:
        content = ExportService.export_course_roster_csv(report)
        media_type = "text/csv; charset=utf-8"
        filename = f"attendance_roster_{c_code}.csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# 3. Session Operational Reports
# =============================================================================


@router.get(
    "/sessions/{session_id}",
    response_model=StandardResponse[SessionReportResponse],
    summary="Get single session operational attendance report",
)
async def get_session_report(
    session_id: uuid.UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_READ, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[SessionReportResponse]:
    """Return operational checkpoint statistics, status breakdown, and manual/offline metrics."""
    report = await ReportingService.get_session_report(
        db=db,
        university_id=current_user.university_id,
        session_id=session_id,
    )
    return StandardResponse(data=SessionReportResponse(**report))


@router.get(
    "/sessions/{session_id}/export",
    summary="Export session report to CSV or XLSX",
)
async def export_session_report(
    session_id: uuid.UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_EXPORT, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    format: Annotated[str, Query(description="Export format: CSV or XLSX")] = "CSV",
) -> Response:
    """Download session operational report in CSV or XLSX format."""
    report = await ReportingService.get_session_report(
        db=db,
        university_id=current_user.university_id,
        session_id=session_id,
    )

    fmt = format.upper().strip()
    if fmt == ExportFormat.XLSX.value:
        content = ExportService.export_session_report_xlsx(report)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"session_report_{session_id}.xlsx"
    else:
        content = ExportService.export_session_report_csv(report)
        media_type = "text/csv; charset=utf-8"
        filename = f"session_report_{session_id}.csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# 4. Department & Faculty Aggregate Reports
# =============================================================================


@router.get(
    "/department/{department_id}",
    response_model=StandardResponse[DepartmentAggregateReportResponse],
    summary="Get department-level aggregate attendance metrics",
)
async def get_department_report(
    department_id: uuid.UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_READ, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    semester_id: Annotated[uuid.UUID | None, Query()] = None,
) -> StandardResponse[DepartmentAggregateReportResponse]:
    """Return aggregated attendance metrics across all department offerings."""
    await _verify_unit_subtree_access(db, current_user, department_id)

    report = await ReportingService.get_department_report(
        db=db,
        university_id=current_user.university_id,
        academic_unit_id=department_id,
        semester_id=semester_id,
    )
    return StandardResponse(data=DepartmentAggregateReportResponse(**report))


@router.get(
    "/department/{department_id}/export",
    summary="Export department aggregate report to CSV or XLSX",
)
async def export_department_report(
    department_id: uuid.UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_EXPORT, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    semester_id: Annotated[uuid.UUID | None, Query()] = None,
    format: Annotated[str, Query(description="Export format: CSV or XLSX")] = "CSV",
) -> Response:
    """Download department aggregate report in CSV or XLSX format."""
    await _verify_unit_subtree_access(db, current_user, department_id)

    report = await ReportingService.get_department_report(
        db=db,
        university_id=current_user.university_id,
        academic_unit_id=department_id,
        semester_id=semester_id,
    )

    fmt = format.upper().strip()
    unit_code = report.get("academic_unit_code", "dept")
    if fmt == ExportFormat.XLSX.value:
        content = ExportService.export_department_report_xlsx(report)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"department_report_{unit_code}.xlsx"
    else:
        content = ExportService.export_department_report_csv(report)
        media_type = "text/csv; charset=utf-8"
        filename = f"department_report_{unit_code}.csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/faculty/{faculty_id}",
    response_model=StandardResponse[FacultyAggregateReportResponse],
    summary="Get faculty-level aggregate attendance report",
)
async def get_faculty_report(
    faculty_id: uuid.UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_READ, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    semester_id: Annotated[uuid.UUID | None, Query()] = None,
) -> StandardResponse[FacultyAggregateReportResponse]:
    """Return faculty roll-up of departmental attendance metrics."""
    await _verify_unit_subtree_access(db, current_user, faculty_id)

    report = await ReportingService.get_faculty_report(
        db=db,
        university_id=current_user.university_id,
        faculty_id=faculty_id,
        semester_id=semester_id,
    )
    return StandardResponse(data=FacultyAggregateReportResponse(**report))


# =============================================================================
# 5. Lecturer Operational Report
# =============================================================================


@router.get(
    "/lecturers/{lecturer_id}",
    response_model=StandardResponse[LecturerOperationalReportResponse],
    summary="Get operational report of sessions conducted by an instructor",
)
async def get_lecturer_report(
    lecturer_id: uuid.UUID,
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_READ, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    semester_id: Annotated[uuid.UUID | None, Query()] = None,
) -> StandardResponse[LecturerOperationalReportResponse]:
    """Return neutral operational reporting on scheduled vs conducted sessions."""
    report = await ReportingService.get_lecturer_report(
        db=db,
        university_id=current_user.university_id,
        lecturer_id=lecturer_id,
        semester_id=semester_id,
    )
    return StandardResponse(data=LecturerOperationalReportResponse(**report))


@router.get(
    "/dashboard/summary",
    response_model=StandardResponse[DashboardSummaryResponse],
    summary="Get administrative dashboard summary counts",
)
async def get_dashboard_summary(
    current_user: Annotated[
        User,
        Depends(require_permission(PermissionCode.REPORTS_ATTENDANCE_READ, allow_scoped=True)),
    ],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[DashboardSummaryResponse]:
    """Return aggregated operational and domain counts for the administrative dashboard."""
    summary = await ReportingService.get_dashboard_summary(
        db=db,
        university_id=current_user.university_id,
    )
    return StandardResponse(data=DashboardSummaryResponse.model_validate(summary))
