"""Pydantic schemas and contracts for Attendance Reports and Analytics."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict

from backend.app.core.constants import ThresholdStatus


class StudentCourseAttendanceItem(BaseModel):
    """Attendance summary for a student in a specific course offering."""

    model_config = ConfigDict(from_attributes=True)

    course_offering_id: uuid.UUID
    course_code: str
    course_name: str
    semester_code: str
    section_code: str | None = None
    total_sessions_conducted: int
    eligible_sessions: int
    attendance_credit: float
    attendance_percentage: float | None = None
    present_count: int
    late_count: int
    absent_count: int
    excused_count: int
    leave_count: int
    has_revision: bool
    threshold_percentage: float
    threshold_status: ThresholdStatus


class StudentAttendanceSummaryResponse(BaseModel):
    """Complete multi-course attendance summary for a student."""

    model_config = ConfigDict(from_attributes=True)

    student_id: uuid.UUID
    student_number: str
    student_name: str
    generated_at_utc: datetime.datetime
    courses: list[StudentCourseAttendanceItem]
    overall_average_percentage: float | None = None
    below_threshold_count: int


class CourseRosterReportItem(BaseModel):
    """Attendance record line item for a student within a course roster."""

    model_config = ConfigDict(from_attributes=True)

    student_id: uuid.UUID
    student_number: str
    student_name: str
    eligible_sessions: int
    attendance_credit: float
    attendance_percentage: float | None = None
    present_count: int
    late_count: int
    absent_count: int
    excused_count: int
    leave_count: int
    has_revision: bool
    threshold_status: ThresholdStatus


class CourseRosterReportResponse(BaseModel):
    """Roster attendance report for a concrete course offering."""

    model_config = ConfigDict(from_attributes=True)

    course_offering_id: uuid.UUID
    course_code: str
    course_name: str
    semester_code: str
    section_code: str | None = None
    total_sessions_conducted: int
    threshold_percentage: float
    near_threshold_margin: float
    total_enrolled: int
    average_attendance_percentage: float | None = None
    above_threshold_count: int
    near_threshold_count: int
    below_threshold_count: int
    not_applicable_count: int = 0
    generated_at_utc: datetime.datetime
    roster: list[CourseRosterReportItem]
    page: int
    page_size: int
    total_pages: int


class SessionReportResponse(BaseModel):
    """Detailed operational breakdown for a single attendance session."""

    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    occurrence_id: uuid.UUID
    course_code: str
    course_name: str
    semester_code: str
    section_code: str | None = None
    lecturer_code: str | None = None
    lecturer_name: str | None = None
    room_number: str | None = None
    building_code: str | None = None
    opened_at_utc: datetime.datetime | None = None
    closed_at_utc: datetime.datetime | None = None
    status: str
    roster_count: int
    start_credited_count: int
    middle_credited_count: int
    end_credited_count: int
    present_count: int
    late_count: int
    absent_count: int
    excused_count: int
    leave_count: int
    manual_count: int
    offline_count: int
    revision_count: int
    network_presence_mode: str
    host_type: str
    generated_at_utc: datetime.datetime


class DepartmentOfferingSummaryItem(BaseModel):
    """Offering summary item in departmental aggregate report."""

    model_config = ConfigDict(from_attributes=True)

    course_offering_id: uuid.UUID
    course_code: str
    course_name: str
    semester_code: str
    section_code: str | None = None
    enrolled_count: int
    conducted_sessions_count: int
    average_attendance_percentage: float | None = None
    below_threshold_count: int
    near_threshold_count: int
    not_applicable_count: int = 0


class DepartmentAggregateReportResponse(BaseModel):
    """Department-level aggregate attendance metrics across active offerings."""

    model_config = ConfigDict(from_attributes=True)

    academic_unit_id: uuid.UUID
    academic_unit_code: str
    academic_unit_name: str
    total_courses: int
    total_offerings: int
    total_students_enrolled: int
    department_average_percentage: float | None = None
    below_threshold_count: int
    near_threshold_count: int
    above_threshold_count: int
    not_applicable_count: int = 0
    generated_at_utc: datetime.datetime
    offerings: list[DepartmentOfferingSummaryItem]


class FacultyAggregateReportResponse(BaseModel):
    """Faculty-level aggregate metrics rolling up departmental attendance."""

    model_config = ConfigDict(from_attributes=True)

    academic_unit_id: uuid.UUID
    academic_unit_code: str
    academic_unit_name: str
    total_departments: int
    total_students: int
    faculty_average_percentage: float | None = None
    below_threshold_count: int
    near_threshold_count: int
    above_threshold_count: int
    not_applicable_count: int = 0
    generated_at_utc: datetime.datetime
    departments: list[DepartmentAggregateReportResponse]


class LecturerOperationalReportResponse(BaseModel):
    """Neutral operational summary of sessions conducted by an instructor."""

    model_config = ConfigDict(from_attributes=True)

    lecturer_id: uuid.UUID
    employee_code: str
    lecturer_name: str
    sessions_scheduled: int
    sessions_conducted: int
    manual_attendance_count: int
    offline_sessions_count: int
    revision_count: int
    generated_at_utc: datetime.datetime
