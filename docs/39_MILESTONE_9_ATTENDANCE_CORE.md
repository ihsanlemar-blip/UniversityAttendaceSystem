# Digital Student Attendance System
## 39. Milestone 9 — Attendance Core Engine & Policy

**Document Version:** 1.0  
**Status:** Completed & Validated  
**Milestone:** 9 (Attendance Core Engine & Policy)  
**Git Feature Branch:** `feature/task-007-attendance-core`  
**Base Commit:** Main branch after Milestone 8.1 reconciliation  

---

## 1. Executive Summary

Milestone 9 implements the central attendance engine and policy evaluation subsystem of the **Digital Student Attendance System**. Building directly upon the academic structure (Milestone 6), course offerings & rosters (Milestone 7), and timetables & concrete class occurrences (Milestone 8), Milestone 9 delivers:
- Hierarchical policy resolution across four institutional scopes (`COURSE` > `PROGRAM` > `FACULTY` > `UNIVERSITY`).
- Strict calendar meeting anchoring: Every attendance session attaches directly to a concrete `ClassOccurrence`.
- Formal attendance session lifecycle state machine (`SCHEDULED` -> `ACTIVE` -> `PAUSED` -> `CLOSED` -> `ARCHIVED`).
- Active roster snapshot freeze: When a session activates, currently enrolled students are frozen into immutable roster records (`AttendanceRecord`) in `PENDING` status.
- Approved three-checkpoint presence architecture: Exactly three discrete checkpoints (`START`, `MIDDLE`, `END`), sequence 1, 2, 3. Alternative popup or half-session models are strictly prohibited.
- Combinatorial evaluation engine: Evaluates all 8 presence patterns (from (0,0,0) to (1,1,1)) against resolved policy thresholds, awarding standardized status (`PRESENT`, `LATE`, `ABSENT`, `EXCUSED`, `LEAVE`) and credit points (1.0, 0.5, 0.0).
- Append-only revision ledger (`AttendanceRevision`): Corrections post-session never mutate original records in-place. Version numbers increment monotonically, and every override demands a recorded justification and actor ID.
- In strict adherence to system boundaries, zero dynamic QR generation (Milestone 10), Bluetooth BLE verification (Milestone 11), device fingerprinting/trust (Milestone 10), physical card fallback (Milestone 10), or offline synchronization (Milestone 12) was introduced.

---

## 2. Core Capabilities Implemented

### 2.1 Hierarchical Policy Engine (`AttendancePolicy`)
- **Model**: `AttendancePolicy` captures attendance rules at configurable scopes (`id`, `university_id`, `scope_type`, `faculty_id`, `program_id`, `course_id`, `min_attendance_pct`, `present_threshold_checkpoints`, `late_threshold_checkpoints`, `checkpoint_window_seconds`, `allow_late_arrival`, `late_arrival_cutoff_minutes`, `is_active`, `created_at`, `updated_at`).
- **4-Tier Scope Resolution Hierarchy**:
  1. `COURSE`: Policy explicitly configured for a specific course offering.
  2. `PROGRAM`: Policy inherited from the degree program offering the course.
  3. `FACULTY`: Policy inherited from the faculty administering the program.
  4. `UNIVERSITY`: Institution-wide fallback default policy.
- **Configurable Defaults**:
  - `min_attendance_pct`: 75.0% default requirement.
  - `present_threshold_checkpoints`: 2 of 3 checkpoints required for full credit.
  - `late_threshold_checkpoints`: 1 checkpoint required for late/partial credit.
  - `checkpoint_window_seconds`: 300 seconds (5 minutes) default window.
- **REST Endpoints**:
  - `POST /api/v1/attendance/policies`: Create or update policy for a given scope.
  - `GET /api/v1/attendance/policies/resolved`: Compute the effective policy hierarchy for a specific course, program, or faculty.

### 2.2 Attendance Sessions (`AttendanceSession`)
- **Occurrence Attachment**: Every `AttendanceSession` references a single concrete calendar meeting (`class_occurrence_id`). A unique database constraint `uq_att_session_occurrence` prevents duplicate sessions for the same class occurrence.
- **Lifecycle State Machine**:
  - `SCHEDULED`: Initial state awaiting class commencement.
  - `ACTIVE`: Session is open; lecturer has activated attendance tracking.
  - `PAUSED`: Temporarily paused; checkpoints can be held.
  - `CLOSED`: Session concluded; final attendance evaluation calculated.
  - `ARCHIVED`: Finalized historical session; locked against automated recalculation.
- **Active Roster Snapshot Freeze**:
  - Upon session activation (`POST /api/v1/attendance/sessions/{id}/activate`), the service queries all active student enrollments (`EnrollmentStatus.ENROLLED`) for the course offering and snapshots them as `AttendanceRecord` rows in `PENDING` status.
  - Later enrollment changes do not alter historical session rosters.
- **REST Endpoints**:
  - `POST /api/v1/attendance/sessions`: Initialize session for a `class_occurrence_id`.
  - `POST /api/v1/attendance/sessions/{id}/activate`: Open session and snapshot active student roster.
  - `POST /api/v1/attendance/sessions/{id}/pause`: Pause session.
  - `POST /api/v1/attendance/sessions/{id}/resume`: Resume paused session.
  - `POST /api/v1/attendance/sessions/{id}/close`: Conclude session and trigger automated final evaluation.

### 2.3 Approved 3-Checkpoint Architecture (`AttendanceCheckpoint`)
- **Discrete Three-Checkpoint Sequence**:
  - Sequence 1: `START` — Opened near beginning of class.
  - Sequence 2: `MIDDLE` — Opened near midpoint of class.
  - Sequence 3: `END` — Opened near conclusion of class.
- **Prohibited Models Enforced**: No random popups, no single-half splits.
- **Window Management & UTC Authority (INV-03)**:
  - Checkpoints record `opened_at_utc` and `closed_at_utc`.
  - Checkpoint window expires when current UTC time exceeds `opened_at_utc + window_seconds`.
  - Automated check-in window expiration rejection.
- **REST Endpoints**:
  - `POST /api/v1/attendance/sessions/{id}/checkpoints/{type}/open`: Open `START`, `MIDDLE`, or `END` checkpoint.
  - `POST /api/v1/attendance/sessions/{id}/checkpoints/{type}/close`: Close checkpoint window.

### 2.4 Attendance Evidence & Idempotent Verification (`AttendanceEvidence`)
- **Evidence Model**: Captures presence verification events (`id`, `attendance_session_id`, `attendance_checkpoint_id`, `student_id`, `evidence_source`, `recorded_at_utc`, `telemetry_payload`).
- **INV-05 (No Duplicate Checkpoint Credit)**:
  - Database-enforced unique constraint `uq_att_ev_sess_cp_student` on `(attendance_session_id, attendance_checkpoint_id, student_id)`.
  - Submitting evidence for an already-verified checkpoint in the same session is rejected as a duplicate, preventing replay attacks or double counting.
- **INV-01 (Client Cannot Mark Itself Present)**:
  - Clients submit verification evidence to the server; the attendance service evaluates eligibility, window status, and session state before granting checkpoint credit.
- **Internal Verification Credit Endpoint**:
  - `POST /api/v1/attendance/sessions/{id}/checkpoints/{type}/verify`: Endpoint for authorized verification recording (used in tests and integrated with M10+ token engines).

### 2.5 Combinatorial Evaluation Engine (`AttendanceRecord`)
When an attendance session closes (or incrementally upon checkpoint submission), `AttendanceService._calculate_student_status()` applies the 8-pattern truth table against the resolved policy thresholds:

| Checkpoints Verified (S, M, E) | Count | Default Evaluation | Status Awarded | Credit Points |
|---|---|---|---|---|
| (1, 1, 1) — Full Class | 3 | Meets Present Threshold (>= 2) | `PRESENT` | 1.0 |
| (1, 1, 0) — Start + Middle | 2 | Meets Present Threshold (>= 2) | `PRESENT` | 1.0 |
| (1, 0, 1) — Start + End | 2 | Meets Present Threshold (>= 2) | `PRESENT` | 1.0 |
| (0, 1, 1) — Middle + End | 2 | Meets Present Threshold (>= 2) | `PRESENT` | 1.0 |
| (1, 0, 0) — Start Only | 1 | Early Departure / Partial Attendance | `LATE` | 0.5 |
| (0, 1, 0) — Middle Only | 1 | Late Arrival / Partial Attendance | `LATE` | 0.5 |
| (0, 0, 1) — End Only | 1 | Very Late Arrival / Insufficient Attendance | `ABSENT` (or `LATE` per policy) | 0.0 / 0.5 |
| (0, 0, 0) — None | 0 | No Verification | `ABSENT` | 0.0 |

- **Special Statuses Preserved**:
  - `EXCUSED`: 1.0 credit, designated administratively with documented reason.
  - `LEAVE`: 1.0 credit, designated institutional or medical leave.
  - `PENDING`: Checkpoints active; final status awaiting session close.

### 2.6 Immutable Revision Ledger & Manual Overrides (`AttendanceRevision`)
- **INV-06 (Corrections Cannot Erase History)**:
  - When a lecturer or administrator modifies an attendance record post-session, the original record is NOT deleted or overwritten in-place without trace.
  - An append-only ledger entry is written to `attendance_revisions` capturing `previous_status`, `new_status`, `previous_score`, `new_score`, `change_reason`, `actor_id`, and `created_at_utc`.
  - The record's `revision_count` increments monotonically (1, 2, 3...).
- **INV-08 (Manual Attendance Overrides Remain Identifiable)**:
  - `POST /api/v1/attendance/records/{id}/override`: Requires mandatory non-empty justification string (`reason`, min 5 chars) and logs the authenticated user's ID (`changed_by_user_id`).
  - Sets `is_manual_override = True` on the `AttendanceRecord`.

### 2.7 Student Attendance Self-Service & Audit Log
- **Student History (`GET /api/v1/students/me/attendance`)**:
  - Resolves authenticated student profile and returns their complete attendance record history across all sessions and courses.
- **Session Roster (`GET /api/v1/attendance/sessions/{id}/records`)**:
  - Returns the complete attendance sheet for an occurrence session with verified checkpoint breakdown, scores, and revision metadata.
- **Session Audit Trail (`GET /api/v1/attendance/sessions/{id}/audit`)**:
  - Returns the complete immutable audit trail of state transitions, checkpoint openings/closings, and attendance revisions.

### 2.8 Scoped RBAC & Teaching Authority
- **Nine New M9 Permissions Seeded**:
  1. `attendance_policies.manage`: Manage attendance policy rules.
  2. `attendance_policies.view`: View attendance policies.
  3. `attendance_sessions.manage`: Open, pause, resume, close attendance sessions.
  4. `attendance_sessions.view`: View attendance sessions and checkpoints.
  5. `attendance_records.view`: View session attendance records.
  6. `attendance_records.override`: Manually override attendance status (INV-08).
  7. `attendance_records.self_view`: Student personal attendance history self-view.
  8. `attendance_checkpoints.manage`: Open and close checkpoints.
  9. `attendance_audit.view`: View attendance audit logs and revision ledgers.
- **Teaching Authority Verification**:
  - Global roles (`SUPER_ADMIN`, `UNIVERSITY_ADMIN`, `ATTENDANCE_OFFICER`) have university-wide attendance authority.
  - Unit roles (`FACULTY_ADMIN`, `DEPARTMENT_ADMIN`) are authorized across their respective academic subtrees.
  - Instructors (`LECTURER`) are strictly verified against the occurrence: They must be the designated primary lecturer (`lecturer_id`), substitute lecturer (`substitute_lecturer_id`), or an assigned co-lecturer on the `CourseOffering`. Unassigned instructors receive HTTP 403 `PERMISSION_DENIED`.

---

## 3. Database Migration 008

Alembic migration `backend/migrations/versions/008_attendance_core.py` provisions:
- Tables: `attendance_policies`, `attendance_sessions`, `attendance_checkpoints`, `attendance_evidence`, `attendance_records`, `attendance_revisions`.
- Constraints:
  - Unique constraint `uq_att_session_occurrence` on `attendance_sessions(class_occurrence_id)`.
  - Unique constraint `uq_att_cp_session_seq` on `attendance_checkpoints(attendance_session_id, sequence_number)`.
  - Unique constraint `uq_att_ev_sess_cp_student` on `attendance_evidence(attendance_session_id, attendance_checkpoint_id, student_id)`.
  - Unique constraint `uq_att_rec_session_student` on `attendance_records(attendance_session_id, student_id)`.
  - Check constraint `ck_att_policy_pct` on `min_attendance_pct BETWEEN 0 AND 100`.
  - Foreign keys with concise naming (`fk_att_*` <= 35 chars) and `ON DELETE RESTRICT` on master entities.
- Reversibility: Fully verified via `007 -> 008 -> 007 -> 008` roundtrip downgrades and upgrades.
- Zero Schema Drift: Verified via `alembic check`.

---

## 4. Invariant Compliance Matrix

| Invariant | Description | Milestone 9 Status | Verification Details |
|---|---|---|---|
| **INV-01** | Client Cannot Mark Itself Present | **ENFORCED** | Client submits verification evidence; the server attendance engine validates window, session state, and policy before determining status. |
| **INV-02** | Attendance Depends on Server/Domain Validation | **ENFORCED** | Attendance state transitions (`PRESENT`, `LATE`, `ABSENT`, `EXCUSED`, `LEAVE`) execute strictly within `AttendanceService._calculate_student_status`. |
| **INV-03** | Student Device Clock Is NOT Authoritative | **ENFORCED** | Checkpoint windows, session start/end times, and evidence receipt timestamps strictly use the server's UTC clock (`datetime.now(timezone.utc)`). Client timestamps are diagnostic only. |
| **INV-04** | Expired Dynamic QR/Tokens Cannot Grant Attendance | **PRESERVED** | Token generation and cryptographic expiration logic deferred to Milestone 10. Checkpoint window expiration rejection is strictly enforced in M9. |
| **INV-05** | No Duplicate Checkpoint Credit | **ENFORCED** | Unique constraint `(attendance_session_id, attendance_checkpoint_id, student_id)` prevents multiple successful credits for the same checkpoint in a session. |
| **INV-06** | Corrections Cannot Erase History | **ENFORCED** | Manual overrides create an append-only `AttendanceRevision` row recording previous status, new status, actor, and justification while monotonically incrementing `revision_count`. |
| **INV-07** | Offline Events Remain Identifiable | **PRESERVED** | Evidence source schema supports `OFFLINE_CAPTURED`; offline queueing and reconciliation deferred to Milestone 12. |
| **INV-08** | Manual Attendance Overrides Remain Identifiable | **ENFORCED** | `POST /api/v1/attendance/records/{id}/override` requires non-empty justification and logs actor user ID in both the record and the revision ledger. |

---

## 5. Verification & Quality Gates Summary

- **Automated Test Matrix**:
  - `backend/tests/test_attendance_policy.py`: 4/4 passed (Hierarchy resolution, program override, course override, validation).
  - `backend/tests/test_attendance_sessions.py`: 4/4 passed (Lifecycle transitions, duplicate prevention, active roster snapshot, teaching authority).
  - `backend/tests/test_attendance_checkpoints.py`: 5/5 passed (Sequence enforcement, window expiration, duplicate credit prevention, idempotent credit).
  - `backend/tests/test_attendance_evaluation.py`: 4/4 passed (All 8 combinatorial presence patterns, credit scoring, custom policy evaluation).
  - `backend/tests/test_attendance_overrides_and_audit.py`: 4/4 passed (Append-only revisions, mandatory justification, student self-service, session audit log).
  - `backend/tests/test_attendance_rbac.py`: 3/3 passed (Scoped roles, student isolation, unassigned lecturer rejection).
  - Total targeted attendance test pass: **24/24 passed (100%)**.
  - Regression scheduling tests (`test_facilities.py`, `test_timetables.py`, `test_occurrences.py`, `test_scheduling_rbac.py`): **14/14 passed (100%)**.
  - RBAC permission tests (`test_rbac.py`): **6/6 passed (100%)**, verifying all 58 system permissions.
- **Static Analysis & Linters**:
  - `ruff check backend`: 100% clean (zero lint errors).
  - `ruff format --check backend`: 100% clean (148 files properly formatted).
  - `mypy backend/app`: Success (zero issues in 103 source files).
  - `mypy` on attendance tests: Success (zero issues in 6 test files).
- **Web & Mobile Quality Gates**:
  - `apps/web`: `npm.cmd run lint` and `npm.cmd run type-check` passed with 0 errors.
  - `apps/mobile`: `flutter analyze` (0 issues) and `flutter test` (all tests passed).
- **Security Check**:
  - `python scripts/check_secrets.py`: Zero exposed secrets detected.
