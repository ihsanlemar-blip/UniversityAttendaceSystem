"""System-wide core constants and status enums."""

from enum import StrEnum


class Environment(StrEnum):
    """Execution environment mode."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class RecordStatus(StrEnum):
    """Generic active status for institutional entities."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    SUSPENDED = "SUSPENDED"


# HTTP and Header Constants
HEADER_REQUEST_ID = "X-Request-ID"
DEFAULT_TIMEZONE = "Asia/Kabul"
DEFAULT_LOCALE = "en"
API_V1_STR = "/api/v1"


class UserStatus(StrEnum):
    """User account lifecycle status."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    LOCKED = "LOCKED"


class SystemRole(StrEnum):
    """Standard system roles."""

    SUPER_ADMIN = "SUPER_ADMIN"
    UNIVERSITY_ADMIN = "UNIVERSITY_ADMIN"
    FACULTY_ADMIN = "FACULTY_ADMIN"
    DEPARTMENT_ADMIN = "DEPARTMENT_ADMIN"
    ATTENDANCE_OFFICER = "ATTENDANCE_OFFICER"
    LECTURER = "LECTURER"
    STUDENT = "STUDENT"
    AUDITOR = "AUDITOR"


class AcademicUnitType(StrEnum):
    """Supported academic organizational unit types per ADR-017."""

    FACULTY = "FACULTY"
    DEPARTMENT = "DEPARTMENT"
    PROGRAM = "PROGRAM"
    OTHER = "OTHER"


class ScopeType(StrEnum):
    """Authorization scope hierarchy level."""

    UNIVERSITY = "UNIVERSITY"
    ACADEMIC_UNIT = "ACADEMIC_UNIT"
    COURSE_OFFERING = "COURSE_OFFERING"


class RevocationReason(StrEnum):
    """Reason for refresh session revocation."""

    ROTATED = "ROTATED"
    LOGOUT = "LOGOUT"
    LOGOUT_ALL = "LOGOUT_ALL"
    REUSE_DETECTED = "REUSE_DETECTED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    ADMIN_REVOKED = "ADMIN_REVOKED"


class PermissionCode(StrEnum):
    """Standard system permission codes."""

    USERS_READ = "users.read"
    USERS_CREATE = "users.create"
    USERS_UPDATE = "users.update"
    USERS_DISABLE = "users.disable"
    USERS_ENABLE = "users.enable"
    USERS_RESET_PASSWORD = "users.reset_password"
    ROLES_READ = "roles.read"
    ROLES_CREATE = "roles.create"
    ROLES_UPDATE = "roles.update"
    PERMISSIONS_READ = "permissions.read"
    ROLE_ASSIGNMENTS_READ = "role_assignments.read"
    ROLE_ASSIGNMENTS_MANAGE = "role_assignments.manage"
    SESSIONS_READ = "sessions.read"
    SESSIONS_REVOKE = "sessions.revoke"
    AUDIT_READ = "audit.read"
    ACADEMIC_UNITS_READ = "academic_units.read"
    ACADEMIC_UNITS_MANAGE = "academic_units.manage"
    ACADEMIC_YEARS_READ = "academic_years.read"
    ACADEMIC_YEARS_MANAGE = "academic_years.manage"
    SEMESTERS_READ = "semesters.read"
    SEMESTERS_MANAGE = "semesters.manage"
    COURSES_READ = "courses.read"
    COURSES_MANAGE = "courses.manage"
    SECTIONS_READ = "sections.read"
    SECTIONS_MANAGE = "sections.manage"
    STUDENTS_READ = "students.read"
    STUDENTS_MANAGE = "students.manage"
    LECTURERS_READ = "lecturers.read"
    LECTURERS_MANAGE = "lecturers.manage"
    COURSE_OFFERINGS_READ = "course_offerings.read"
    COURSE_OFFERINGS_MANAGE = "course_offerings.manage"
    ENROLLMENTS_READ = "enrollments.read"
    ENROLLMENTS_MANAGE = "enrollments.manage"
    BUILDINGS_READ = "buildings.read"
    BUILDINGS_CREATE = "buildings.create"
    BUILDINGS_UPDATE = "buildings.update"
    BUILDINGS_DEACTIVATE = "buildings.deactivate"
    ROOMS_READ = "rooms.read"
    ROOMS_CREATE = "rooms.create"
    ROOMS_UPDATE = "rooms.update"
    ROOMS_DEACTIVATE = "rooms.deactivate"
    TIMETABLES_READ = "timetables.read"
    TIMETABLES_CREATE = "timetables.create"
    TIMETABLES_UPDATE = "timetables.update"
    TIMETABLES_DEACTIVATE = "timetables.deactivate"
    TIMETABLES_GENERATE = "timetables.generate_occurrences"
    CLASS_OCCURRENCES_READ = "class_occurrences.read"
    CLASS_OCCURRENCES_CANCEL = "class_occurrences.cancel"
    CLASS_OCCURRENCES_RESCHEDULE = "class_occurrences.reschedule"
    ATTENDANCE_POLICIES_READ = "attendance_policies.read"
    ATTENDANCE_POLICIES_MANAGE = "attendance_policies.manage"
    ATTENDANCE_SESSIONS_READ = "attendance_sessions.read"
    ATTENDANCE_SESSIONS_MANAGE = "attendance_sessions.manage"
    ATTENDANCE_CHECKPOINTS_MANAGE = "attendance_checkpoints.manage"
    ATTENDANCE_RECORDS_READ = "attendance_records.read"
    ATTENDANCE_RECORDS_OVERRIDE = "attendance_records.override"
    ATTENDANCE_AUDIT_READ = "attendance_audit.read"
    ATTENDANCE_SELF_READ = "attendance.self_read"


class StudentStatus(StrEnum):
    """Student enrollment and academic lifecycle status."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    GRADUATED = "GRADUATED"
    WITHDRAWN = "WITHDRAWN"


class LecturerStatus(StrEnum):
    """Lecturer employment and operational status."""

    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    RESIGNED = "RESIGNED"
    RETIRED = "RETIRED"


class OfferingStatus(StrEnum):
    """Course offering delivery lifecycle status."""

    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EnrollmentStatus(StrEnum):
    """Student offering enrollment lifecycle status."""

    ACTIVE = "ACTIVE"
    DROPPED = "DROPPED"
    COMPLETED = "COMPLETED"
    WITHDRAWN = "WITHDRAWN"


class LecturerAssignmentType(StrEnum):
    """Role/type of lecturer assignment for an offering."""

    PRIMARY = "PRIMARY"
    CO_TEACHER = "CO_TEACHER"
    ASSISTANT = "ASSISTANT"


class BuildingStatus(StrEnum):
    """Campus building operational lifecycle status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RoomStatus(StrEnum):
    """Room and facility space operational lifecycle status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"


class RoomType(StrEnum):
    """Physical classroom and facility space classification."""

    CLASSROOM = "CLASSROOM"
    LABORATORY = "LABORATORY"
    LECTURE_HALL = "LECTURE_HALL"
    AUDITORIUM = "AUDITORIUM"
    OTHER = "OTHER"


class TimetableStatus(StrEnum):
    """Recurring weekly timetable schedule rule status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ClassOccurrenceStatus(StrEnum):
    """Concrete calendar meeting occurrence operational status."""

    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"


class PolicyScopeType(StrEnum):
    """Attendance policy scope level in resolution hierarchy."""

    UNIVERSITY = "UNIVERSITY"
    FACULTY = "FACULTY"
    PROGRAM = "PROGRAM"
    COURSE = "COURSE"


class AttendanceSessionStatus(StrEnum):
    """Attendance session operational lifecycle status."""

    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class AttendanceCheckpointType(StrEnum):
    """Approved attendance checkpoint types per specifications."""

    START = "START"
    MIDDLE = "MIDDLE"
    END = "END"


class AttendanceCheckpointStatus(StrEnum):
    """Checkpoint execution state machine status."""

    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class AttendanceStatus(StrEnum):
    """Official attendance record status taxonomy."""

    PENDING = "PENDING"
    PRESENT = "PRESENT"
    LATE = "LATE"
    ABSENT = "ABSENT"
    EXCUSED = "EXCUSED"
    LEAVE = "LEAVE"


class EvidenceSourceMode(StrEnum):
    """Evidence capture modality source."""

    MANUAL = "MANUAL"
    SYSTEM_AUTOMATED = "SYSTEM_AUTOMATED"
    PHYSICAL_CARD_FALLBACK = "PHYSICAL_CARD_FALLBACK"
    ONLINE_DYNAMIC_QR = "ONLINE_DYNAMIC_QR"
    BLUETOOTH_BLE = "BLUETOOTH_BLE"
    OFFLINE_SYNC = "OFFLINE_SYNC"


class AttendanceAuditEventType(StrEnum):
    """Attendance revision ledger audit event classification."""

    SESSION_INITIALIZED = "SESSION_INITIALIZED"
    SESSION_OPENED = "SESSION_OPENED"
    SESSION_PAUSED = "SESSION_PAUSED"
    SESSION_RESUMED = "SESSION_RESUMED"
    SESSION_CLOSED = "SESSION_CLOSED"
    CHECKPOINT_OPENED = "CHECKPOINT_OPENED"
    CHECKPOINT_CLOSED = "CHECKPOINT_CLOSED"
    CHECKPOINT_CREDITED = "CHECKPOINT_CREDITED"
    MANUAL_CHECKPOINT_CREDIT = "MANUAL_CHECKPOINT_CREDIT"
    MANUAL_RECORD_OVERRIDE = "MANUAL_RECORD_OVERRIDE"
    EXCUSED_APPLIED = "EXCUSED_APPLIED"
    LEAVE_APPLIED = "LEAVE_APPLIED"
    EVALUATION_FINALIZED = "EVALUATION_FINALIZED"
