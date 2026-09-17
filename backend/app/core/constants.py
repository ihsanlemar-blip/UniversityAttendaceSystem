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
    DEVICES_SELF_READ = "devices.self_read"
    DEVICES_SELF_REGISTER = "devices.self_register"
    DEVICES_REPLACEMENT_REQUEST = "devices.replacement_request"
    DEVICES_READ = "devices.read"
    DEVICES_REPLACEMENT_REVIEW = "devices.replacement_review"
    DEVICES_SUSPEND = "devices.suspend"
    DEVICES_REVOKE = "devices.revoke"
    SECURITY_NETWORK_ZONES_MANAGE = "security.network_zones.manage"
    SECURITY_RISK_SIGNALS_READ = "security.risk_signals.read"
    SECURITY_RISK_SIGNALS_REVIEW = "security.risk_signals.review"
    SECURITY_RADIO_ANALYSIS_READ = "security.radio_analysis.read"
    ATTENDANCE_CORRECTIONS_REQUEST = "attendance.corrections.request"
    ATTENDANCE_CORRECTIONS_REVIEW = "attendance.corrections.review"
    ATTENDANCE_CORRECTIONS_OVERRIDE = "attendance.corrections.override"
    ATTENDANCE_EXCUSES_REQUEST = "attendance.excuses.request"
    ATTENDANCE_EXCUSES_REVIEW = "attendance.excuses.review"
    ATTENDANCE_LEAVE_REQUEST = "attendance.leave.request"
    ATTENDANCE_LEAVE_REVIEW = "attendance.leave.review"
    IMPORTS_READ = "imports.read"
    IMPORTS_CREATE = "imports.create"
    IMPORTS_COMMIT = "imports.commit"
    IMPORTS_CANCEL = "imports.cancel"
    REPORTS_ATTENDANCE_READ = "reports.attendance.read"
    REPORTS_ATTENDANCE_EXPORT = "reports.attendance.export"


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
    CAMPUS_NETWORK = "CAMPUS_NETWORK"
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
    OFFLINE_SYNC_RECONCILED = "OFFLINE_SYNC_RECONCILED"
    OFFLINE_CONFLICT_RESOLVED = "OFFLINE_CONFLICT_RESOLVED"
    OFFLINE_PERMIT_ISSUED = "OFFLINE_PERMIT_ISSUED"
    OFFLINE_PERMIT_REVOKED = "OFFLINE_PERMIT_REVOKED"
    CORRECTION_REQUESTED = "CORRECTION_REQUESTED"
    CORRECTION_APPROVED = "CORRECTION_APPROVED"
    CORRECTION_REJECTED = "CORRECTION_REJECTED"
    CORRECTION_CANCELLED = "CORRECTION_CANCELLED"
    EXCUSE_REQUESTED = "EXCUSE_REQUESTED"
    EXCUSE_APPROVED = "EXCUSE_APPROVED"
    EXCUSE_REJECTED = "EXCUSE_REJECTED"
    EXCUSE_CANCELLED = "EXCUSE_CANCELLED"
    LEAVE_REQUESTED = "LEAVE_REQUESTED"
    LEAVE_APPROVED = "LEAVE_APPROVED"
    LEAVE_REJECTED = "LEAVE_REJECTED"
    LEAVE_CANCELLED = "LEAVE_CANCELLED"
    ADMIN_OVERRIDE = "ADMIN_OVERRIDE"
    EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"
    REVERSAL = "REVERSAL"


class OfflinePermitStatus(StrEnum):
    """Offline attendance permit lifecycle status."""

    ISSUED = "ISSUED"
    ACTIVE = "ACTIVE"
    SYNCED = "SYNCED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class OfflineHostSessionStatus(StrEnum):
    """Offline host session operational status."""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    SYNCED = "SYNCED"
    DISPUTED = "DISPUTED"


class OfflineClaimStatus(StrEnum):
    """Offline student attendance claim reconciliation status."""

    PENDING_HOST_EVENTS = "PENDING_HOST_EVENTS"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    CONFLICT = "CONFLICT"


class OfflineConflictType(StrEnum):
    """Offline synchronization conflict classification."""

    UNAUTHORIZED_HOST = "UNAUTHORIZED_HOST"
    EXPIRED_PERMIT = "EXPIRED_PERMIT"
    WINDOW_EXPIRED = "WINDOW_EXPIRED"
    CLOCK_DRIFT_EXCESSIVE = "CLOCK_DRIFT_EXCESSIVE"
    EXISTING_RECORD_CONFLICT = "EXISTING_RECORD_CONFLICT"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    HASH_CHAIN_BROKEN = "HASH_CHAIN_BROKEN"
    STUDENT_NOT_ROSTERED = "STUDENT_NOT_ROSTERED"
    DUPLICATE_CLAIM = "DUPLICATE_CLAIM"


class OfflineConflictResolution(StrEnum):
    """Resolution outcome for an offline synchronization conflict."""

    UNRESOLVED = "UNRESOLVED"
    RESOLVED_AUTO = "RESOLVED_AUTO"
    RESOLVED_MANUAL = "RESOLVED_MANUAL"
    DISMISSED = "DISMISSED"


class SyncBatchType(StrEnum):
    """Synchronization inbox payload classification."""

    HOST_EVENTS = "HOST_EVENTS"
    STUDENT_CLAIMS = "STUDENT_CLAIMS"


class SyncEntryStatus(StrEnum):
    """Synchronization inbox processing status."""

    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class DeviceStatus(StrEnum):
    """Registered student device lifecycle status."""

    PENDING_REGISTRATION = "PENDING_REGISTRATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REPLACEMENT_PENDING = "REPLACEMENT_PENDING"
    REPLACED = "REPLACED"
    REVOKED = "REVOKED"
    COMPROMISED = "COMPROMISED"


class DeviceRole(StrEnum):
    """Device role within the attendance trust domain."""

    PRIMARY = "PRIMARY"


class DeviceReplacementStatus(StrEnum):
    """Student primary device replacement request lifecycle status."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class DeviceTrustEventType(StrEnum):
    """Append-only device security and trust lifecycle event type."""

    DEVICE_REGISTRATION_REQUESTED = "DEVICE_REGISTRATION_REQUESTED"
    DEVICE_ACTIVATED = "DEVICE_ACTIVATED"
    DEVICE_REGISTRATION_FAILED = "DEVICE_REGISTRATION_FAILED"
    DEVICE_REPLACEMENT_REQUESTED = "DEVICE_REPLACEMENT_REQUESTED"
    DEVICE_REPLACEMENT_APPROVED = "DEVICE_REPLACEMENT_APPROVED"
    DEVICE_REPLACEMENT_REJECTED = "DEVICE_REPLACEMENT_REJECTED"
    DEVICE_SUSPENDED = "DEVICE_SUSPENDED"
    DEVICE_REACTIVATED = "DEVICE_REACTIVATED"
    DEVICE_REVOKED = "DEVICE_REVOKED"
    DEVICE_MARKED_COMPROMISED = "DEVICE_MARKED_COMPROMISED"


class NetworkPresenceMode(StrEnum):
    """Attendance session campus network presence policy mode."""

    DISABLED = "DISABLED"
    OPTIONAL = "OPTIONAL"
    REQUIRED = "REQUIRED"


class NetworkZoneType(StrEnum):
    """Campus network zone classification."""

    CAMPUS_TRUSTED = "CAMPUS_TRUSTED"
    REMOTE_VPN = "REMOTE_VPN"
    ADMIN_NETWORK = "ADMIN_NETWORK"
    OTHER = "OTHER"


class NetworkZoneStatus(StrEnum):
    """Campus network zone operational status."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class NetworkChallengeStatus(StrEnum):
    """Campus network challenge verification state."""

    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"


class RiskSignalStatus(StrEnum):
    """Attendance risk signal review workflow status."""

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class RiskSeverity(StrEnum):
    """Attendance risk signal severity classification."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskSubjectType(StrEnum):
    """Entity subject classification for attendance risk signal."""

    STUDENT = "STUDENT"
    LECTURER = "LECTURER"
    SESSION = "SESSION"
    DEVICE = "DEVICE"


class RiskSignalType(StrEnum):
    """Deterministic, factorized anti-cheat risk signal types."""

    STUDENT_NETWORK_NOT_TRUSTED = "STUDENT_NETWORK_NOT_TRUSTED"
    STUDENT_NETWORK_ZONE_MISMATCH = "STUDENT_NETWORK_ZONE_MISMATCH"
    NETWORK_PROOF_REPLAY_ATTEMPT = "NETWORK_PROOF_REPLAY_ATTEMPT"
    NETWORK_FORWARD_HEADER_SPOOF_ATTEMPT = "NETWORK_FORWARD_HEADER_SPOOF_ATTEMPT"
    DEVICE_REPLACEMENT_FREQUENCY_HIGH = "DEVICE_REPLACEMENT_FREQUENCY_HIGH"
    DEVICE_ACCOUNT_REUSE_ATTEMPT = "DEVICE_ACCOUNT_REUSE_ATTEMPT"
    STUDENT_OVERLAPPING_ATTENDANCE = "STUDENT_OVERLAPPING_ATTENDANCE"
    SESSION_MANUAL_ATTENDANCE_RATE_HIGH = "SESSION_MANUAL_ATTENDANCE_RATE_HIGH"
    MASS_MANUAL_ATTENDANCE = "MASS_MANUAL_ATTENDANCE"
    SESSION_CORRECTION_RATE_HIGH = "SESSION_CORRECTION_RATE_HIGH"
    SESSION_OUTSIDE_SCHEDULE_WINDOW = "SESSION_OUTSIDE_SCHEDULE_WINDOW"
    LECTURER_NETWORK_NOT_TRUSTED = "LECTURER_NETWORK_NOT_TRUSTED"


class CorrectionRequestType(StrEnum):
    """Categorized root reason for student attendance correction request."""

    WRONG_ABSENT = "WRONG_ABSENT"
    WRONG_LATE = "WRONG_LATE"
    CHECKPOINT_NOT_RECORDED = "CHECKPOINT_NOT_RECORDED"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"
    DEVICE_FAILURE = "DEVICE_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    QR_FAILURE = "QR_FAILURE"
    BLE_FAILURE = "BLE_FAILURE"
    OFFLINE_SYNC_ISSUE = "OFFLINE_SYNC_ISSUE"
    OTHER = "OTHER"


class ExcuseCategory(StrEnum):
    """Categorized reason for student session or occurrence absence excuse."""

    MEDICAL = "MEDICAL"
    OFFICIAL_UNIVERSITY_ACTIVITY = "OFFICIAL_UNIVERSITY_ACTIVITY"
    FAMILY_EMERGENCY = "FAMILY_EMERGENCY"
    TRANSPORT_DISRUPTION = "TRANSPORT_DISRUPTION"
    TECHNICAL_SYSTEM_FAILURE = "TECHNICAL_SYSTEM_FAILURE"
    OTHER = "OTHER"


class CorrectionRequestStatus(StrEnum):
    """Operational workflow lifecycle status for attendance correction requests."""

    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    ESCALATED = "ESCALATED"


class ExcuseRequestStatus(StrEnum):
    """Operational workflow lifecycle status for absence excuse requests."""

    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class LeaveRequestStatus(StrEnum):
    """Operational workflow lifecycle status for pre-class leave requests."""

    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ImportType(StrEnum):
    """Supported institutional domain entity import categories."""

    STUDENTS = "STUDENTS"
    LECTURERS = "LECTURERS"
    COURSES = "COURSES"
    COURSE_OFFERINGS = "COURSE_OFFERINGS"
    ENROLLMENTS = "ENROLLMENTS"
    TIMETABLES = "TIMETABLES"


class ImportJobStatus(StrEnum):
    """State machine lifecycle status for asynchronous and synchronous import jobs."""

    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    COMMITTING = "COMMITTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ImportCommitMode(StrEnum):
    """Execution mode for committing validated staged import rows into domain tables."""

    STRICT = "STRICT"
    PARTIAL = "PARTIAL"


class ImportRowStatus(StrEnum):
    """Validation and staging state for individual spreadsheet rows."""

    VALID = "VALID"
    WARNING = "WARNING"
    ERROR = "ERROR"
    COMMITTED = "COMMITTED"
    SKIPPED = "SKIPPED"


class ImportRowAction(StrEnum):
    """Planned domain entity mutation action derived from staging validation."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    NONE = "NONE"
    SKIP = "SKIP"


class ThresholdStatus(StrEnum):
    """Evaluated attendance threshold compliance states."""

    ABOVE_THRESHOLD = "ABOVE_THRESHOLD"
    NEAR_THRESHOLD = "NEAR_THRESHOLD"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ExportFormat(StrEnum):
    """Supported file formats for data and report exports."""

    CSV = "CSV"
    XLSX = "XLSX"
