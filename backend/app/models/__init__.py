"""Models package exporting declarative Base and entities."""

from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.academic_year import AcademicYear
from backend.app.models.attendance_checkpoint import AttendanceCheckpoint
from backend.app.models.attendance_evidence import AttendanceEvidence
from backend.app.models.attendance_policy import AttendancePolicy
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.attendance_revision import AttendanceRevision
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from backend.app.models.building import Building
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.course import Course
from backend.app.models.course_offering import CourseOffering
from backend.app.models.enrollment import Enrollment
from backend.app.models.lecturer import Lecturer
from backend.app.models.lecturer_assignment import LecturerAssignment
from backend.app.models.login_attempt import LoginAttempt
from backend.app.models.permission import Permission
from backend.app.models.refresh_session import RefreshSession
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.role_permission import RolePermission
from backend.app.models.room import Room
from backend.app.models.section import Section
from backend.app.models.semester import Semester
from backend.app.models.student import Student
from backend.app.models.timetable import Timetable
from backend.app.models.university import University
from backend.app.models.user import User

__all__ = [
    "AcademicUnit",
    "AcademicYear",
    "AttendanceCheckpoint",
    "AttendanceEvidence",
    "AttendancePolicy",
    "AttendanceRecord",
    "AttendanceRevision",
    "AttendanceSession",
    "Base",
    "Building",
    "ClassOccurrence",
    "Course",
    "CourseOffering",
    "Enrollment",
    "Lecturer",
    "LecturerAssignment",
    "LoginAttempt",
    "Permission",
    "RefreshSession",
    "Role",
    "RoleAssignment",
    "RolePermission",
    "Room",
    "Section",
    "Semester",
    "Student",
    "TimestampMixin",
    "Timetable",
    "UUIDv7PrimaryKeyMixin",
    "University",
    "User",
]
