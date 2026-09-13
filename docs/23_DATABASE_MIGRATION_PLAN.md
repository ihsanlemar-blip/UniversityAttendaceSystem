# Digital Student Attendance System
## Database Migration Plan and Dependency Order

**Document Version:** 1.0  
**Status:** Approved Architectural Blueprint  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Overview and Migration Principles

Per **ADR-005 (PostgreSQL Primary Database)** and `docs/09_DATABASE_SCHEMA.md`, database schema changes must be managed via **Alembic** migrations executed in strict topological dependency order.

### Core Migration Principles
1. **Topological Order**: Foreign keys, constraints, and tables must be created according to their domain dependencies.
2. **Reversible Migrations**: Every migration file must implement both `upgrade()` and `downgrade()` functions.
3. **Non-Destructive Evolution**: Migrations in production must not drop historical attendance evidence or audit records.
4. **Zero Manual DB Changes**: Schema updates are strictly applied through versioned Alembic scripts tracked in Git.

---

## 2. Planned Migration Sequence & Implementation Reconciliation

### 2.1 Actual Implemented Migration Sequence (Linear Alembic Revisions)

To support real testability and adhere to modular milestones, the actual linear Alembic revision sequence establishes security, identity, and access control directly following the institutional foundation:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Actual Implemented Revision Chain                    │
│                                                                        │
│  001_foundation_university (Milestone 4 - Completed)                   │
│      │                                                                 │
│      ▼                                                                 │
│  002_identity_users (Milestone 5 - users table)                        │
│      │                                                                 │
│      ▼                                                                 │
│  003_rbac (Milestone 5 - roles, permissions, role_assignments)         │
│      │                                                                 │
│      ▼                                                                 │
│  004_auth_sessions_and_login_attempts (Milestone 5 - sessions/audit)   │
│      │                                                                 │
│      ▼                                                                 │
│  005_academic_units_and_calendar (Milestone 6 - hierarchy & calendar)   │
│      │                                                                 │
│      ▼                                                                 │
│  006_courses_people_and_enrollments (Milestone 7 - curriculum/rosters) │
│      │                                                                 │
│      ▼                                                                 │
│  007_timetable_and_class_occurrences (Milestone 8 - rooms/schedule)     │
│      │                                                                 │
│      ▼                                                                 │
│  008_attendance_core (Milestone 9 - policies/sessions/checkpoints)      │
│      │                                                                 │
│      ▼                                                                 │
│  [Subsequent Milestones - dynamic QR, BLE, offline sync, etc.]         │
└────────────────────────────────────────────────────────────────────────┘
```

*Note: Migrations 001 through 005 are fully applied and operational as of Milestone 6.*

### 2.2 Original Conceptual Grouping (Milestone 3 Architecture Blueprint)

The original conceptual taxonomy grouped academic units before identity. In practice, establishing user identity and role-based access control first allows administrative creation and role scoping of academic units and structures in Milestone 6 without placeholder authentication bypasses.

The original 29-milestone conceptual dependency sequence was:

---

## 3. Migration Dependency Groups

### Group I: Foundation & Institutional Hierarchy
- **`001_foundation_university`**:
  - Tables: `universities`
  - Columns: `id`, `name`, `code`, `timezone`, `default_language`, `status`, timestamps.
  - Dependencies: None (root entity).
- **`002_academic_units`**:
  - Tables: `academic_units`
  - Columns: `id`, `university_id`, `parent_id` (nullable self-reference per ADR-017), `unit_type`, `code`, `name`, `status`.
  - Dependencies: `001`.
- **`003_academic_calendar`**:
  - Tables: `academic_years`, `semesters`
  - Columns: `academic_years` (id, university_id, name, start_date, end_date), `semesters` (id, academic_year_id, name, sequence_no, start_date, end_date).
  - Dependencies: `001`.

### Group II: Identity, Roles, and People
- **`004_identity_users`**:
  - Tables: `users`
  - Columns: `id`, `university_id`, `username`, `password_hash`, `email`, `phone`, `preferred_language`, `status`, `last_login_at`.
  - Constraints: `UNIQUE (university_id, username)`.
  - Dependencies: `001`.
- **`005_rbac_permissions`**:
  - Tables: `roles`, `permissions`, `role_permissions`, `role_assignments`
  - Constraints: `UNIQUE (role_id, permission_id)`.
  - Dependencies: `004`.
- **`006_students_and_lecturers`**:
  - Tables: `students`, `lecturers`, `staff_profiles`
  - Constraints: `UNIQUE (user_id)`, `UNIQUE (university_id, student_number)`, `UNIQUE (university_id, employee_code)`.
  - Dependencies: `002`, `004`.
- **`007_academic_sections`**:
  - Tables: `sections`
  - Foreign keys: `academic_unit_id`, `semester_id`.
  - Dependencies: `002`, `003`.

### Group III: Academic Curriculum & Enrollment
- **`008_courses`**:
  - Tables: `courses`
  - Foreign keys: `university_id`, `academic_unit_id`.
  - Dependencies: `001`, `002`.
- **`009_course_offerings`**:
  - Tables: `course_offerings`
  - Foreign keys: `course_id`, `semester_id`, `section_id`.
  - Dependencies: `007`, `008`.
- **`010_lecturer_assignments`**:
  - Tables: `lecturer_assignments`
  - Foreign keys: `course_offering_id`, `lecturer_id`.
  - Columns: `role` (Primary, Assistant, Lab Instructor).
  - Dependencies: `006`, `009`.
- **`011_enrollments`**:
  - Tables: `enrollments`
  - Foreign keys: `course_offering_id`, `student_id`.
  - Constraints: `UNIQUE (course_offering_id, student_id)`.
  - Dependencies: `006`, `009`.

### Group IV: Facilities & Concrete Scheduling
- **`012_rooms`**:
  - Tables: `rooms`
  - Columns: `id`, `university_id`, `building`, `room_number`, `capacity`, `network_subnet`.
  - Dependencies: `001`.
- **`013_timetables`**:
  - Tables: `timetables` (recurring schedule rules per ADR-016).
  - Foreign keys: `course_offering_id`, `room_id`.
  - Columns: `day_of_week`, `start_time`, `end_time`.
  - Dependencies: `009`, `012`.
- **`014_class_occurrences`**:
  - Tables: `class_occurrences` (concrete calendar instances per ADR-016).
  - Foreign keys: `timetable_id`, `course_offering_id`, `room_id`, `substitute_lecturer_id`.
  - Columns: `scheduled_start_utc`, `scheduled_end_utc`, `status` (`SCHEDULED`, `COMPLETED`, `CANCELLED`).
  - Dependencies: `006`, `012`, `013`.

### Group V: Attendance Core Engine
- **`015_attendance_policies`**:
  - Tables: `attendance_policies`
  - Columns: `university_id`, `academic_unit_id`, `minimum_percentage`, `late_threshold_minutes`, `checkpoints_required_ratio`.
  - Dependencies: `001`, `002`.
- **`016_attendance_sessions`**:
  - Tables: `attendance_sessions`
  - Foreign keys: `class_occurrence_id`, `lecturer_id`, `room_id`, `policy_id`.
  - Columns: `state` (`SCHEDULED`, `ACTIVE`, `PAUSED`, `CLOSED`, `FINALIZED`), `started_at_utc`, `closed_at_utc`.
  - Dependencies: `006`, `012`, `014`, `015`.
- **`017_checkpoints`**:
  - Tables: `checkpoints` (ADR-009).
  - Foreign keys: `attendance_session_id`.
  - Columns: `checkpoint_type` (`START`, `MIDDLE`, `END`), `sequence_no`, `active_from_utc`, `active_until_utc`, `status`.
  - Dependencies: `016`.

### Group VI: Device Binding, Hardware & Evidence
- **`018_devices`**:
  - Tables: `devices`, `device_registrations` (ADR-011).
  - Foreign keys: `user_id`, `student_id`.
  - Columns: `public_key_pem`, `device_fingerprint`, `model`, `os_version`, `status` (`ACTIVE`, `REVOKED`).
  - Dependencies: `004`, `006`.
- **`019_physical_cards`**:
  - Tables: `physical_cards` (ADR-018).
  - Foreign keys: `student_id`.
  - Columns: `card_serial`, `public_hash`, `issued_at`, `status`.
  - Dependencies: `006`.
- **`020_attendance_evidence`**:
  - Tables: `attendance_evidence`
  - Foreign keys: `checkpoint_id`, `student_id`, `device_id`.
  - Columns: `token_payload_hash`, `received_at_utc`, `ip_address`, `ble_rssi`, `verification_score`, `raw_telemetry_json`.
  - Dependencies: `006`, `017`, `018`.
- **`021_checkpoint_results`**:
  - Tables: `checkpoint_results`
  - Foreign keys: `checkpoint_id`, `student_id`.
  - Columns: `status` (`VERIFIED`, `ABSENT`, `FLAGGED`), `resolved_at_utc`.
  - Constraints: `UNIQUE (checkpoint_id, student_id)`.
  - Dependencies: `006`, `017`.
- **`022_final_attendance_records`**:
  - Tables: `final_attendance_records`
  - Foreign keys: `attendance_session_id`, `student_id`.
  - Columns: `status` (`PRESENT`, `LATE`, `ABSENT`, `EXCUSED`), `checkpoints_attended`, `confidence_score`, `finalized_at_utc`.
  - Constraints: `UNIQUE (attendance_session_id, student_id)`.
  - Dependencies: `006`, `016`.

### Group VII: Governance, Audit, Resilience & Replication
- **`023_corrections`**:
  - Tables: `corrections`
  - Foreign keys: `final_attendance_record_id`, `requested_by_user_id`, `reviewed_by_user_id`.
  - Columns: `previous_status`, `new_status`, `reason`, `status` (`PENDING`, `APPROVED`, `REJECTED`).
  - Dependencies: `004`, `022`.
- **`024_risk_flags`**:
  - Tables: `risk_flags`
  - Foreign keys: `attendance_evidence_id`, `student_id`.
  - Columns: `flag_type` (`IP_MISMATCH`, `NO_BLE`, `RAPID_REUSE`), `severity`, `details_json`.
  - Dependencies: `006`, `020`.
- **`025_audit_logs`**:
  - Tables: `audit_logs`
  - Columns: `id`, `actor_user_id`, `action`, `entity_name`, `entity_id`, `before_state_json`, `after_state_json`, `ip_address`, `created_at_utc`.
  - Dependencies: `004`.
- **`026_notifications`**:
  - Tables: `notifications`
  - Foreign keys: `user_id`.
  - Columns: `title`, `message`, `category`, `read_at_utc`, `created_at_utc`.
  - Dependencies: `004`.
- **`027_imports`**:
  - Tables: `imports`
  - Foreign keys: `initiated_by_user_id`.
  - Columns: `import_type`, `filename`, `total_rows`, `processed_rows`, `status`, `error_log_json`.
  - Dependencies: `004`.
- **`028_offline_permits`**:
  - Tables: `offline_permits` (ADR-002, ADR-015).
  - Foreign keys: `lecturer_id`, `class_occurrence_id`.
  - Columns: `permit_token_hash`, `issued_at_utc`, `expires_at_utc`, `reconciled_at_utc`.
  - Dependencies: `006`, `014`.
- **`029_sync_outbox`**:
  - Tables: `sync_outbox`, `sync_inbox` (ADR-015 transactional outbox).
  - Columns: `id`, `event_type`, `aggregate_type`, `aggregate_id`, `payload_json`, `status` (`PENDING`, `SENT`, `FAILED`), `attempts`, `created_at_utc`.
  - Dependencies: None (generic transactional replication).
