# Digital Student Attendance System
## Implementation Roadmap

**Document Version:** 1.0  
**Status:** Approved Engineering Roadmap  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Roadmap Architecture & Phasing Strategy

This roadmap specifies the 20 implementation phases (Phase 0 through Phase 19) required to construct, test, harden, and deploy the Digital Student Attendance System.

The sequence follows strict domain and architectural dependency order:
```text
Foundation & Infrastructure -> Identity & Master Data -> Scheduling -> Attendance Engine ->
Anti-Cheating & Devices -> Offline/Sync Resilience -> Governance & Reporting -> Hardening & Pilot
```

---

## 2. Implementation Phases

### Phase 0 — Repository Bootstrap
- **Goals**: Establish monorepo governance, tooling baseline, container orchestration, linting, CI automation, and developer ergonomics.
- **Prerequisites**: Approved Milestone 1–3 documentation.
- **Deliverables**:
  - Monorepo directory structure (`apps/`, `backend/`, `infra/`, `tests/`, `contracts/`).
  - Minimal FastAPI application with `/health/live` and `/health/ready`.
  - Minimal Next.js web application shell.
  - Minimal Flutter mobile application shell.
  - `docker-compose.yml` for PostgreSQL 16, Redis 7, Backend, Worker, Web.
  - GitHub Actions CI workflow for linting, type-checking, and tests.
- **Acceptance Criteria**:
  - `git status` clean on main branch.
  - Health checks return HTTP 200 OK.
  - CI pipeline passes without warnings.
- **Dependencies**: None.
- **Major Risks**: Tooling version mismatch across developer host environments (Windows/macOS/Linux).

---

### Phase 1 — Backend Foundation
- **Goals**: Establish database connectivity, async SQLAlchemy 2.0 engine, Alembic migrations framework, Redis client, standard API response envelopes, error handling, and structured logging.
- **Prerequisites**: Phase 0.
- **Deliverables**:
  - `backend/app/core/` config, db engine, redis, exceptions, logging.
  - Alembic initialization with async driver and automated migration checks.
  - Initial foundation migration (`001_foundation`).
  - Unit and integration test fixtures with PostgreSQL test database.
- **Acceptance Criteria**:
  - Database migrations apply cleanly up and down.
  - Standard error envelope `{"error": {"code": "...", "message": "...", "details": ...}}` enforced.
  - Redis connection pool verified with health checks.
- **Dependencies**: Phase 0.
- **Major Risks**: Flaky database test fixtures; connection leak under async SQLAlchemy.

---

### Phase 2 — Authentication and RBAC
- **Goals**: Implement local-first user authentication, password hashing (Argon2id), JWT access/refresh token lifecycle, and granular Role-Based Access Control (RBAC).
- **Prerequisites**: Phase 1.
- **Deliverables**:
  - Database tables: `users`, `roles`, `permissions`, `role_permissions`, `role_assignments`.
  - Seed migration for standard university roles (System Admin, University Admin, Dean, Department Head, Lecturer, Student, Auditor).
  - Auth routes: `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me`.
  - RBAC dependency middleware (`require_permission(...)`).
- **Acceptance Criteria**:
  - Password hashing uses Argon2id with work factor parameters.
  - Refresh tokens support single-use rotation and revocation.
  - Non-authorized requests return HTTP 403 Forbidden with clear permission context.
- **Dependencies**: Phase 1.
- **Major Risks**: Token leakage, timing attacks on login endpoints.

---

### Phase 3 — Academic Structure and Master Data
- **Goals**: Model university organizational hierarchy, academic calendar, sections, students, and lecturers.
- **Prerequisites**: Phase 2.
- **Deliverables**:
  - Tables: `universities`, `academic_units` (flexible parent-child hierarchy per ADR-017), `academic_years`, `semesters`, `sections`, `students`, `lecturers`.
  - CRUD services and REST endpoints under `/api/v1/academic/`.
  - Web UI views in Next.js for managing university structure and rosters.
- **Acceptance Criteria**:
  - Academic unit hierarchy supports arbitrary depth (Faculty -> Department -> Program).
  - Student numbers and lecturer employee codes unique within university scope.
- **Dependencies**: Phase 2.
- **Major Risks**: Deeply recursive queries on academic units without proper index optimization.

---

### Phase 4 — Timetable and Class Occurrences
- **Goals**: Separate recurring schedule rules from concrete class occurrences per ADR-016 to enable room changes, rescheduling, cancellations, and substitute lecturers.
- **Prerequisites**: Phase 3.
- **Deliverables**:
  - Tables: `courses`, `course_offerings`, `lecturer_assignments`, `enrollments`, `rooms`, `timetables`, `class_occurrences`.
  - Schedule generator service converting timetable recurrence rules into concrete `class_occurrences`.
  - Rescheduling and substitute lecturer substitution APIs.
- **Acceptance Criteria**:
  - Class occurrences correctly instantiate with scheduled start/end times in UTC.
  - Schedule conflicts (room or lecturer double-booking) detected and flagged.
- **Dependencies**: Phase 3.
- **Major Risks**: Timezone errors across calendar boundaries; recurring rule edge cases.

---

### Phase 5 — Attendance Core
- **Goals**: Implement the foundational three-checkpoint attendance engine per ADR-009, ADR-010, and PRD specifications.
- **Prerequisites**: Phase 4.
- **Deliverables**:
  - Tables: `attendance_policies`, `attendance_sessions`, `checkpoints`, `attendance_evidence`, `checkpoint_results`, `final_attendance_records`.
  - State machine: `SCHEDULED` -> `ACTIVE` -> `CLOSED` -> `FINALIZED`.
  - Configurable checkpoint scheduler (Start, Middle, End checkpoints).
  - Final attendance decision service evaluating student checkpoint results against policy (e.g., 2-of-3 present, late arrival rules).
- **Acceptance Criteria**:
  - No single boolean column for attendance; evidence and checkpoint results preserved immutably.
  - Final record state strictly computed by server (`PRESENT`, `LATE`, `ABSENT`, `EXCUSED`).
  - Duplicate check-ins for the same checkpoint return idempotent success without duplicate credit.
- **Dependencies**: Phase 4.
- **Major Risks**: Race conditions during high-volume simultaneous checkpoint submissions.

---

### Phase 6 — Dynamic QR / Token
- **Goals**: Implement rotating cryptographic tokens for dynamic QR display to eliminate static image forwarding and proxy attendance.
- **Prerequisites**: Phase 5.
- **Deliverables**:
  - HMAC-SHA256 dynamic token generator with 20–30 second rotation window.
  - Server-side token validation service checking session key, expiration, and window tolerance (±1 step).
  - Real-time token streaming endpoint via SSE (Server-Sent Events) or WebSocket to lecturer client.
- **Acceptance Criteria**:
  - Expired tokens rejected with HTTP 400 `TOKEN_EXPIRED`.
  - Token replay attack rejected once used by the same student for that checkpoint.
- **Dependencies**: Phase 5.
- **Major Risks**: Network latency causing valid tokens to expire before reaching local server.

---

### Phase 7 — Student Mobile Attendance
- **Goals**: Deliver student Flutter mobile application capabilities for scanning dynamic QR codes and submitting attendance check-ins.
- **Prerequisites**: Phase 6.
- **Deliverables**:
  - Camera QR scanner integration in Flutter using Riverpod state management.
  - Secure check-in submission API (`POST /api/v1/attendance/check-in`).
  - Student attendance history, course roster, and attendance status UI screens.
- **Acceptance Criteria**:
  - Check-in payload includes session ID, checkpoint ID, dynamic token, device telemetry, and timestamp.
  - UI cleanly indicates check-in success, checkpoint closed, or session error.
  - RTL language layout (Dari/Pashto) renders correctly.
- **Dependencies**: Phase 6.
- **Major Risks**: Camera permission denial or slow QR focus on budget mobile devices.

---

### Phase 8 — Lecturer Attendance Controls
- **Goals**: Deliver Next.js and Flutter controls for lecturers to launch sessions, display rotating QR codes, view real-time attendee counts, and perform manual adjustments.
- **Prerequisites**: Phase 7.
- **Deliverables**:
  - Lecturer session management dashboard (Start session, trigger checkpoint, pause, close).
  - Live attendance roster with real-time attendee counter.
  - Manual override API with mandatory reason tracking (`STUDENT_DEVICE_DEAD`, `MEDICAL`, etc.).
- **Acceptance Criteria**:
  - Only assigned lecturer or authorized substitute can control the session.
  - Manual adjustments require a reason and are logged in audit ledger.
- **Dependencies**: Phase 7.
- **Major Risks**: Lecturer accidentally closing session prematurely; UI disconnect during live class.

---

### Phase 9 — Device Registration and Trust
- **Goals**: Implement asymmetric cryptographic device binding per ADR-011 to eliminate multiple logins from a single proxy phone.
- **Prerequisites**: Phase 8.
- **Deliverables**:
  - Device key generation in Flutter using Android Keystore / iOS Secure Enclave (Ed25519 or ECDSA).
  - Tables: `devices`, `device_registrations`.
  - Registration approval workflow (auto-approve first device, admin review for device replacement).
  - Check-in request signature verification on backend.
- **Acceptance Criteria**:
  - Check-in from unregistered or unapproved device rejected (`DEVICE_NOT_AUTHORIZED`).
  - One student bound to exactly one active device at a time.
- **Dependencies**: Phase 8.
- **Major Risks**: Secure hardware key storage API inconsistencies across fragmented Android versions.

---

### Phase 10 — Bluetooth Presence
- **Goals**: Add Bluetooth Low Energy (BLE) presence beacon verification per ADR-012 as secondary anti-cheating evidence.
- **Prerequisites**: Phase 9.
- **Deliverables**:
  - Flutter lecturer mode: BLE advertising rotating ephemeral service UUIDs.
  - Flutter student mode: BLE background/foreground scanning capturing signal RSSI and beacon payload.
  - Backend evidence ingestion service recording BLE RSSI in `attendance_evidence`.
- **Acceptance Criteria**:
  - Presence evidence correctly categorized as primary (QR) + secondary (BLE).
  - Missing BLE does not outright fail check-in if campus Wi-Fi and device signature match, but flags risk score.
- **Dependencies**: Phase 9.
- **Major Risks**: Bluetooth permission denial, background scanning throttling on iOS/Android.

---

### Phase 11 — Physical QR Card Fallback
- **Goals**: Support students without smartphones or with dead batteries using staff-scanned physical QR cards per ADR-018.
- **Prerequisites**: Phase 10.
- **Deliverables**:
  - Secure physical student card issuance with signed card serial and cryptographic HMAC.
  - Lecturer app "Scan Student Card" mode.
  - Backend validation endpoint ensuring physical card scanning occurs only by authorized staff in session room.
- **Acceptance Criteria**:
  - Students cannot scan their own or other students' physical cards.
  - Card check-in flagged with evidence type `STAFF_SCANNED_PHYSICAL_CARD`.
- **Dependencies**: Phase 10.
- **Major Risks**: Counterfeit card printing (mitigated by server-signed verification keys).

---

### Phase 12 — Offline Lecturer Host
- **Goals**: Enable local attendance capture when campus network is temporarily completely down, using lecturer's device as temporary local host.
- **Prerequisites**: Phase 11.
- **Deliverables**:
  - Offline session authorization token ("permit") issued by server prior to class.
  - Local SQLite session storage on lecturer device.
  - Local peer-to-peer check-in collection (Wi-Fi hotspot / BLE exchange).
  - Signed offline export bundle.
- **Acceptance Criteria**:
  - Offline session verified by backend using cryptographically signed permit.
  - Ingestion prevents backdating or tampering with timestamps.
- **Dependencies**: Phase 11.
- **Major Risks**: Clock drift on lecturer phone; complex peer-to-peer Wi-Fi connectivity.

---

### Phase 13 — Synchronization
- **Goals**: Implement transactional outbox/inbox replication between local campus server and cloud disaster recovery per ADR-002 and ADR-015.
- **Prerequisites**: Phase 12.
- **Deliverables**:
  - Tables: `sync_outbox`, `sync_inbox`, `sync_status`.
  - Celery background worker periodically batching outbox events to cloud endpoint.
  - Conflict resolution strategy: local campus server is master for attendance transactions.
- **Acceptance Criteria**:
  - Network interruption resumes replication seamlessly without duplicate record generation.
  - Zero data loss during simulated 24-hour campus internet outage.
- **Dependencies**: Phase 12.
- **Major Risks**: Outbox queue growth during prolonged campus network disconnections.

---

### Phase 14 — Corrections and Audit
- **Goals**: Provide auditable workflows for correcting attendance records post-session while preserving immutable historical truth.
- **Prerequisites**: Phase 13.
- **Deliverables**:
  - Tables: `corrections`, `audit_logs`.
  - Correction request, review, and approval workflow for Lecturers and Deans.
  - Read-only audit trail viewer in Web interface.
- **Acceptance Criteria**:
  - Original record is never overwritten or deleted; new revision record created referencing original.
  - Full audit trail recorded (who, when, why, previous state, new state).
- **Dependencies**: Phase 13.
- **Major Risks**: Accidental permission escalation allowing unauthorized record modifications.

---

### Phase 15 — Reporting and Notifications
- **Goals**: Generate official university attendance reports, debarment warnings (students below 75%), and multi-channel alerts.
- **Prerequisites**: Phase 14.
- **Deliverables**:
  - Analytical SQL queries and PDF/Excel report generators (Course attendance sheet, Student individual summary, Faculty compliance report).
  - Automated threshold warning job flagging students at risk of exam debarment.
  - Notification dispatcher (in-app push, email, SMS where gateway configured).
- **Acceptance Criteria**:
  - Reports calculate attendance percentages accurately based on credit hours and policy.
  - Debarment lists reflect finalized records and approved corrections.
- **Dependencies**: Phase 14.
- **Major Risks**: Heavy report generation blocking main database (mitigated by read-only replica / async worker).

---

### Phase 16 — Imports
- **Goals**: Provide bulk CSV/Excel import tools for onboarding university rosters, courses, students, and schedules from legacy systems.
- **Prerequisites**: Phase 15.
- **Deliverables**:
  - Asynchronous import pipeline in Celery with validation, dry-run preview, and row-level error reporting.
  - Web UI for uploading CSV files, mapping columns, and reviewing import errors.
- **Acceptance Criteria**:
  - Malformed rows cleanly reported with line number and reason; valid rows committed in transaction.
  - Idempotent upsert logic prevents duplicate student accounts on re-import.
- **Dependencies**: Phase 15.
- **Major Risks**: Inconsistent character encoding (UTF-8 / Windows-1252) in university spreadsheets.

---

### Phase 17 — Security Hardening
- **Goals**: Comprehensive security assessment, penetration testing, rate limiting, and cryptographic key management hardening.
- **Prerequisites**: Phase 16.
- **Deliverables**:
  - Rate limiting with Redis per IP, user, and device.
  - TLS 1.3 hardening on campus Nginx reverse proxy.
  - Secret scanning, dependency vulnerability remediation, and OWASP Top 10 validation.
- **Acceptance Criteria**:
  - Dynamic token brute-force attempts blocked by rate limiting.
  - Zero critical/high CVEs in backend, web, or mobile dependencies.
- **Dependencies**: Phase 16.
- **Major Risks**: False positives in rate limiting during peak classroom check-in bursts.

---

### Phase 18 — Load / Reliability Testing
- **Goals**: Validate performance and fault-tolerance under peak university operational stress.
- **Prerequisites**: Phase 17.
- **Deliverables**:
  - Locust and k6 simulation test scripts.
  - 1,000 concurrent students scanning QR codes across 30 active simultaneous classes.
  - Database connection pool tuning, query indexing optimization, and Redis caching.
- **Acceptance Criteria**:
  - 95th percentile check-in API latency under 250ms at peak load.
  - Zero database deadlocks during concurrent checkpoint completions.
- **Dependencies**: Phase 17.
- **Major Risks**: Server CPU saturation during simultaneous HMAC token verification.

---

### Phase 19 — Pilot Deployment
- **Goals**: Deploy system to a live university faculty/department for real-world pilot operation.
- **Prerequisites**: Phase 18.
- **Deliverables**:
  - Production deployment scripts for campus local server.
  - User training guides for Lecturers, Students, and Administrators.
  - Pilot monitoring dashboard and feedback collection mechanism.
- **Acceptance Criteria**:
  - 2-week pilot executed with zero data loss and >98% check-in success rate.
  - Feedback collected and prioritized for Milestone 5 / Phase 20 release.
- **Dependencies**: Phase 18.
- **Major Risks**: End-user resistance, Wi-Fi coverage dead zones in older university lecture halls.
