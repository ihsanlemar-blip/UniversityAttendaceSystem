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
