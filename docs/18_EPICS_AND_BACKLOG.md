# Digital Student Attendance System
## Epics and Implementation Backlog

**Document Version:** 1.0  
**Status:** Approved Engineering Backlog  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Overview

This document specifies the complete structured engineering backlog for the Digital Student Attendance System. It defines 31 core Epics (`EPIC-001` through `EPIC-031`), decomposed into actionable, single-responsibility tasks with clear IDs.

Each task adheres to the following conventions:
- Granular task boundaries (database, service, API, UI, test).
- Traceable to architectural requirements and database models.
- AI-agent friendly execution units.

---

## 2. Epics and Task Breakdown

### EPIC-001: Repository Bootstrap
- `TASK-001-01`: Create monorepo directory layout (`apps/`, `backend/`, `infra/`, `tests/`, `contracts/`, `scripts/`).
- `TASK-001-02`: Configure universal repository settings (`.editorconfig`, `.gitattributes`, `.gitignore`).
- `TASK-001-03`: Create environment variable specification template (`.env.example`).
- `TASK-001-04`: Scaffold minimal FastAPI application with `/health/live` and `/health/ready` endpoints.
- `TASK-001-05`: Scaffold minimal Next.js TypeScript web application shell.
- `TASK-001-06`: Scaffold minimal Flutter mobile application shell.
- `TASK-001-07`: Create multi-container Docker Compose file (`postgres`, `redis`, `backend`, `worker`, `web`).
- `TASK-001-08`: Implement GitHub Actions CI workflow for linting and type-checking.
- `TASK-001-09`: Initialize Git repository with main branch and commit bootstrap baseline.

### EPIC-002: Backend Foundation
- `TASK-002-01`: Configure Pydantic v2 settings management with `.env` loader.
- `TASK-002-02`: Configure async SQLAlchemy 2.0 engine and scoped sessionmaker.
- `TASK-002-03`: Initialize Alembic async migration environment with autogenerate support.
- `TASK-002-04`: Create Redis connection manager and caching interface.
- `TASK-002-05`: Implement standard API response envelopes and exception handlers.
- `TASK-002-06`: Implement structured JSON logger with request correlation IDs.
- `TASK-002-07`: Set up backend pytest test suite with test database fixture.

### EPIC-003: Authentication
- `TASK-003-01`: Create `users` table migration and SQLAlchemy model with UUIDv7 primary keys.
- `TASK-003-02`: Implement password hashing service using Argon2id with salt.
- `TASK-003-03`: Implement JWT access token generator and validator (HMAC-SHA256).
- `TASK-003-04`: Implement refresh token lifecycle with database tracking and revocation.
- `TASK-003-05`: Implement `/api/v1/auth/login` endpoint with rate-limiting.
- `TASK-003-06`: Implement `/api/v1/auth/refresh` and `/api/v1/auth/logout` endpoints.
- `TASK-003-07`: Implement `/api/v1/auth/me` profile endpoint.
- `TASK-003-08`: Write unit and integration tests for authentication flows.

### EPIC-004: Role-Based Access Control (RBAC)
- `TASK-004-01`: Create `roles`, `permissions`, `role_permissions`, and `role_assignments` tables.
- `TASK-004-02`: Implement database seeder for standard system roles and permission sets.
- `TASK-004-03`: Implement FastAPI dependency `require_permission(permission_code)` with caching.
- `TASK-004-04`: Implement scoped role assignment validator (e.g., Dean scoped to Faculty).
- `TASK-004-05`: Write unit tests verifying authorization enforcement and denial cases.

### EPIC-005: Academic Units
- `TASK-005-01`: Create `universities` table migration and model.
- `TASK-005-02`: Create `academic_units` table with self-referencing `parent_id` (ADR-017).
- `TASK-005-03`: Create `academic_years`, `semesters`, and `sections` table migrations.
- `TASK-005-04`: Implement CRUD services for universities and academic units.
- `TASK-005-05`: Implement REST endpoints `/api/v1/academic/units` and `/api/v1/academic/semesters`.
- `TASK-005-06`: Build Next.js administrative management screens for academic hierarchy.
- `TASK-005-07`: Write unit and integration tests for academic unit hierarchy.

### EPIC-006: Students
- `TASK-006-01`: Create `students` table migration and SQLAlchemy model.
- `TASK-006-02`: Implement student profile service with unique `(university_id, student_number)` check.
- `TASK-006-03`: Implement student user provisioning service (linking user account to student record).
- `TASK-006-04`: Create REST endpoints `/api/v1/students/` (list, create, update, detail).
- `TASK-006-05`: Build Next.js student roster view with search and filtering.
- `TASK-006-06`: Write unit tests for student number validation and unique constraints.

### EPIC-007: Lecturers
- `TASK-007-01`: Create `lecturers` table migration and SQLAlchemy model.
- `TASK-007-02`: Implement lecturer profile service with unique `(university_id, employee_code)`.
- `TASK-007-03`: Implement lecturer user provisioning service.
- `TASK-007-04`: Create REST endpoints `/api/v1/lecturers/`.
- `TASK-007-05`: Build Next.js lecturer directory and assignment views.
- `TASK-007-06`: Write unit and integration tests for lecturer management.

### EPIC-008: Courses
- `TASK-008-01`: Create `courses` table migration (code, title, credits, department).
- `TASK-008-02`: Implement course repository and service layer.
- `TASK-008-03`: Create REST endpoints `/api/v1/courses/`.
- `TASK-008-04`: Build Next.js course catalog management screens.
- `TASK-008-05`: Write unit tests for course code uniqueness within university.

### EPIC-009: Course Offerings
- `TASK-009-01`: Create `course_offerings` and `lecturer_assignments` table migrations.
- `TASK-009-02`: Implement offering service linking course, semester, section, and primary lecturer.
- `TASK-009-03`: Create REST endpoints `/api/v1/offerings/`.
- `TASK-009-04`: Build Next.js offering setup interface with lecturer assignment.
- `TASK-009-05`: Write integration tests for course offering lifecycle.

### EPIC-010: Enrollments
- `TASK-010-01`: Create `enrollments` table migration with unique `(course_offering_id, student_id)`.
- `TASK-010-02`: Implement enrollment service with capacity and status tracking (`ACTIVE`, `DROPPED`).
- `TASK-010-03`: Create REST endpoints `/api/v1/offerings/{id}/enrollments`.
- `TASK-010-04`: Build student enrollment view in Next.js.
- `TASK-010-05`: Write unit tests preventing duplicate or inactive student enrollments.

### EPIC-011: Timetable
- `TASK-011-01`: Create `rooms` and `timetables` table migrations (ADR-016 recurrence rules).
- `TASK-011-02`: Implement room management service with capacity and location attributes.
- `TASK-011-03`: Implement recurring timetable rule engine (day of week, start/end time, room).
- `TASK-011-04`: Create timetable conflict detection service (room and lecturer double-booking).
- `TASK-011-05`: Create REST endpoints `/api/v1/timetables/` and `/api/v1/rooms/`.
- `TASK-011-06`: Build Next.js weekly timetable visual scheduler.

### EPIC-012: Class Occurrences
- `TASK-012-01`: Create `class_occurrences` table migration (concrete class instances per ADR-016).
- `TASK-012-02`: Implement occurrence generator service expanding timetable rules into dates.
- `TASK-012-03`: Implement occurrence modification service (cancellation, room change, substitute).
- `TASK-012-04`: Create REST endpoints `/api/v1/occurrences/`.
- `TASK-012-05`: Build Next.js calendar view showing scheduled and modified class occurrences.
- `TASK-012-06`: Write tests verifying recurring rule expansion and occurrence adjustments.

### EPIC-013: Attendance Policies
- `TASK-013-01`: Create `attendance_policies` table migration (thresholds, late rules per ADR-010).
- `TASK-013-02`: Implement policy resolution service (course override -> department -> university default).
- `TASK-013-03`: Create REST endpoints `/api/v1/attendance/policies/`.
- `TASK-013-04`: Build Next.js policy configuration panel with policy preview.
- `TASK-013-05`: Write unit tests for hierarchical policy resolution.

### EPIC-014: Attendance Sessions
- `TASK-014-01`: Create `attendance_sessions` table migration (state: `SCHEDULED`, `ACTIVE`, `CLOSED`).
- `TASK-014-02`: Implement session start service with lecturer assignment and schedule validation.
- `TASK-014-03`: Implement session state machine with transitions and event hooks.
- `TASK-014-04`: Create REST endpoints `/api/v1/attendance/sessions/` (start, pause, resume, close).
- `TASK-014-05`: Implement lecturer authorization check ensuring only assigned staff can control session.
- `TASK-014-06`: Integrate session lifecycle with audit logging service.
- `TASK-014-07`: Write unit and integration tests for session state transitions.

### EPIC-015: Attendance Checkpoints
- `TASK-015-01`: Create `checkpoints` table migration (type: `START`, `MIDDLE`, `END` per ADR-009).
- `TASK-015-02`: Implement checkpoint triggering service with configurable active duration (3–5 min).
- `TASK-015-03`: Implement automatic checkpoint closing task via Celery / Redis expiration.
- `TASK-015-04`: Create REST endpoints `/api/v1/attendance/sessions/{id}/checkpoints`.
- `TASK-015-05`: Build real-time countdown timer component in Lecturer UI.
- `TASK-015-06`: Write tests validating checkpoint duration enforcement and auto-closure.

### EPIC-016: Attendance Evidence
- `TASK-016-01`: Create `attendance_evidence` table migration (tokens, device telemetry, network IP).
- `TASK-016-02`: Implement evidence ingestion service recording raw check-in telemetry.
- `TASK-016-03`: Implement campus network validation service (subnet/BSSID verification).
- `TASK-016-04`: Create student check-in ingestion endpoint `POST /api/v1/attendance/check-in`.
- `TASK-016-05`: Write tests verifying evidence persistence and immutability.

### EPIC-017: Final Attendance Records
- `TASK-017-01`: Create `checkpoint_results` and `final_attendance_records` table migrations.
- `TASK-017-02`: Implement checkpoint aggregator mapping student evidence into checkpoint status.
- `TASK-017-03`: Implement final attendance evaluation engine (evaluating 2-of-3 checkpoints, late rules).
- `TASK-017-04`: Create session finalization service with database transaction locks.
- `TASK-017-05`: Create student attendance record query endpoints `/api/v1/attendance/records/`.
- `TASK-017-06`: Write unit tests verifying policy rules: Present, Late, Absent, Excused.

### EPIC-018: Dynamic Tokens
- `TASK-018-01`: Implement HMAC-SHA256 rotating token generator with 20–30s rotation window.
- `TASK-018-02`: Implement server-side token validator with ±1 window drift tolerance.
- `TASK-018-03`: Implement token streaming endpoint using Server-Sent Events (SSE) for Lecturer screen.
- `TASK-018-04`: Build dynamic QR renderer in Flutter and Next.js lecturer views.
- `TASK-018-05`: Write tests verifying expired, forged, or replayed tokens are rejected.

### EPIC-019: Device Registration
- `TASK-019-01`: Create `devices` and `device_registrations` table migrations.
- `TASK-019-02`: Implement cryptographic keypair generation in Flutter (Secure Enclave / Keystore).
- `TASK-019-03`: Create device registration request endpoint `POST /api/v1/devices/register`.
- `TASK-019-04`: Implement device approval workflow (first device auto-approved, subsequent require admin).
- `TASK-019-05`: Implement request digital signature verification middleware for student check-ins.
- `TASK-019-06`: Build Next.js device management screen for administrators to review changes.
- `TASK-019-07`: Write unit and security tests for device key verification and replay prevention.

### EPIC-020: Bluetooth Presence
- `TASK-020-01`: Implement BLE advertiser in Flutter lecturer mode broadcasting ephemeral service UUID.
- `TASK-020-02`: Implement BLE scanner in Flutter student mode scanning for lecturer beacon.
- `TASK-020-03`: Update check-in submission API to accept BLE RSSI evidence.
- `TASK-020-04`: Implement proximity evaluation service scoring BLE signal strength.
- `TASK-020-05`: Write tests verifying presence score computation with and without BLE evidence.

### EPIC-021: Physical QR Cards
- `TASK-021-01`: Create `physical_cards` table migration (card serial, public hash, issued status).
- `TASK-021-02`: Implement card issuance service generating cryptographically signed QR cards.
- `TASK-021-03`: Build Flutter "Staff Scan Physical Card" mode in Lecturer app.
- `TASK-021-04`: Implement staff-authenticated card check-in endpoint `POST /api/v1/attendance/card-scan`.
- `TASK-021-05`: Write tests ensuring physical card scans are restricted to authorized staff.

### EPIC-022: Offline Attendance
- `TASK-022-01`: Create `offline_permits` table migration for offline session pre-authorization.
- `TASK-022-02`: Implement offline permit issuance service signing session parameters with server key.
- `TASK-022-03`: Implement local SQLite/Drift session storage on Flutter lecturer app.
- `TASK-022-04`: Implement local peer check-in collection on lecturer mobile device.
- `TASK-022-05`: Implement offline session upload and reconciliation service on backend.
- `TASK-022-06`: Write integration tests simulating full offline session capture and reconciliation.

### EPIC-023: Synchronization
- `TASK-023-01`: Create `sync_outbox` and `sync_inbox` table migrations (ADR-015 transactional outbox).
- `TASK-023-02`: Implement outbox event emitter inside backend domain service transactions.
- `TASK-023-03`: Implement Celery background sync worker batching events to cloud target.
- `TASK-023-04`: Implement cloud sync receiver endpoint with idempotent deduplication.
- `TASK-023-05`: Write tests verifying sync resume after simulated network connection drops.

### EPIC-024: Corrections
- `TASK-024-01`: Create `corrections` table migration with links to original attendance record.
- `TASK-024-02`: Implement correction request service (Lecturer requests change with justification).
- `TASK-024-03`: Implement correction review service (Dean/Admin approves or rejects).
- `TASK-024-04`: Implement recalculation service updating final record status without deleting history.
- `TASK-024-05`: Build Next.js correction management dashboard.
- `TASK-024-06`: Write tests ensuring original records and audit logs are never modified or purged.

### EPIC-025: Audit
- `TASK-025-01`: Create `audit_logs` table migration (actor_id, action, entity, before, after, ip).
- `TASK-025-02`: Implement audit logger service listening to domain events.
- `TASK-025-03`: Create read-only audit log query API with date, actor, and action filters.
- `TASK-025-04`: Build Next.js audit log viewer for authorized System Auditors.
- `TASK-025-05`: Write tests verifying audit records cannot be altered or deleted via API.

### EPIC-026: Risk Detection
- `TASK-026-01`: Create `risk_flags` table migration.
- `TASK-026-02`: Implement anomaly detection rules (rapid IP switching, missing BLE, clock anomalies).
- `TASK-026-03`: Implement risk scoring engine evaluating check-in confidence score.
- `TASK-026-04`: Build suspicious activity indicator in Lecturer live roster and Dean dashboard.
- `TASK-026-05`: Write unit tests for risk score calculation algorithms.

### EPIC-027: Reports
- `TASK-027-01`: Implement attendance aggregation queries (by course, section, student, department).
- `TASK-027-02`: Implement PDF report generation service (official course attendance register).
- `TASK-027-03`: Implement Excel / CSV report export service.
- `TASK-027-04`: Implement exam debarment list generator (students falling below 75% threshold).
- `TASK-027-05`: Build Next.js analytics and reporting dashboard with charts.
- `TASK-027-06`: Write tests verifying percentage calculations across varied credit hour weights.

### EPIC-028: Notifications
- `TASK-028-01`: Create `notifications` table migration.
- `TASK-028-02`: Implement in-app notification service with real-time SSE delivery.
- `TASK-028-03`: Implement automated debarment warning scheduler for students approaching threshold.
- `TASK-028-04`: Build notification inbox widget in Web and Mobile apps.
- `TASK-028-05`: Write unit tests for automated warning dispatch triggers.

### EPIC-029: Imports
- `TASK-029-01`: Create `imports` table migration for tracking batch upload status.
- `TASK-029-02`: Implement CSV parser and schema validator for students, lecturers, and courses.
- `TASK-029-03`: Implement Celery async import worker with dry-run validation mode.
- `TASK-029-04`: Build Next.js CSV upload interface with error preview table.
- `TASK-029-05`: Write integration tests testing valid and malformed CSV batch imports.

### EPIC-030: Security Hardening
- `TASK-030-01`: Configure Redis-backed rate limiting on all public and authentication routes.
- `TASK-030-02`: Implement security headers in Nginx reverse proxy (CSP, HSTS, X-Frame-Options).
- `TASK-030-03`: Configure automated secret scanning in CI (Gitleaks / TruffleHog).
- `TASK-030-04`: Run OWASP Top 10 automated vulnerability scanning and remediate findings.
- `TASK-030-05`: Perform cryptographic signature validation fuzz testing.

### EPIC-031: Pilot
- `TASK-031-01`: Prepare campus server production Docker compose configuration and installation script.
- `TASK-031-02`: Create database seed scripts with pilot faculty, courses, and student cohorts.
- `TASK-031-03`: Conduct end-to-end rehearsal simulating 5 simultaneous classroom sessions.
- `TASK-031-04`: Publish Pilot User Guides for Lecturers and Students.
- `TASK-031-05`: Monitor live pilot operation and record operational feedback.
