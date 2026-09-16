# Milestone 15: Attendance Operations, Corrections, Excuses, Leave & Immutable Workflows

**Version:** 1.0  
**Approved Scope:** Configurable student attendance correction window (default 24h) with server-time UTC enforcement and session policy snapshotting; Student self-service correction request workflow with duplicate open request prevention (INV-05); Lecturer and Administrator review queues with deliberate approval and rejection; Immutable revision ledger with actor attribution (INV-06, INV-08) and non-destructive compensating reversals; Absence excuse workflow with medical/official document references; Pre-class leave workflow enforcing Section 38 zero-credit invariant without physical attendance simulation; Flagged manual and emergency attendance review queue; Savepoint-isolated atomic bulk review operations; Comprehensive record audit revision timeline; M14 anti-cheat risk signal context integration without automated sanctioning; Next.js administrative review console (`/admin/attendance/reviews`); and Flutter mobile student attendance history and operations screens.

---

## 1. Executive Summary

Milestone 15 establishes the operational lifecycle, administrative oversight, and immutable workflow foundation for the Digital Student Attendance System. In live university environments, real-world anomalies—such as transient hardware failures, student device depletion, sanctioned institutional leaves, illness, or emergency manual interventions—inevitably occur. 

Milestone 15 resolves these operational realities through structured, auditable domain workflows without violating foundational system invariants. Crucially:
- **No historical evidence is ever deleted or mutated**: Checkpoint tokens, telemetry, BLE measurements, and original attendance outcomes remain immutable.
- **Status adjustments are append-only**: Every approved correction, excuse, manual override, or reversal appends a new `AttendanceRevision` record attributing the human actor, timestamp, justification, and state differential.
- **Client devices never self-certify**: The university server's UTC clock is the sole authority for correction submission deadlines.
- **Risk signals never auto-decide**: Milestone 14 anti-cheat signals inform the human reviewer but never automatically approve, reject, or discipline students.

---

## 2. Fundamental Security & Operational Invariants

1. **Server UTC Clock Sole Authority (INV-02)**:
   - The correction window deadline is evaluated against `utc_now()`.
   - The deadline reference is calculated from the attendance session's `closed_at_utc` (or scheduled class occurrence end if session closed timestamp is unset), using the frozen snapshot policy parameter `lecturer_correction_window_hours` (default: 24 hours).
   - Once `utc_now() >= deadline`, new student correction submissions are strictly rejected with HTTP 400 `CORRECTION_WINDOW_CLOSED`.
   - Administrative overrides (`admin_override`) remain available to privileged administrators beyond the student submission window with mandatory justification.
   - Pending requests submitted *before* the deadline may be reviewed and decided by authorized reviewers at any time after the window closes.

2. **Policy Snapshot Immutability**:
   - The correction window length is captured at session activation inside `AttendanceSession.policy_snapshot["lecturer_correction_window_hours"]`.
   - If a university later updates its global policy (e.g., from 24h to 48h), existing historical sessions continue to enforce their frozen 24h window snapshot.

3. **Single Open Request Rule (INV-05 & Schema Constraints)**:
   - A student may have at most **one open correction request** (`PENDING` or `UNDER_REVIEW`) per attendance record, enforced at the database level via a partial unique index:
     ```sql
     CREATE UNIQUE INDEX uq_open_correction_request_per_record 
     ON attendance_correction_requests (attendance_record_id) 
     WHERE status IN ('PENDING', 'UNDER_REVIEW');
     ```
   - Similarly, at most **one open pre-class leave request** is allowed per student per scheduled `ClassOccurrence`:
     ```sql
     CREATE UNIQUE INDEX uq_open_leave_request_per_occurrence 
     ON attendance_leave_requests (student_id, class_occurrence_id) 
     WHERE status IN ('PENDING', 'UNDER_REVIEW');
     ```

4. **Immutable Revision Ledger & Non-Destructive Reversals (INV-06 & INV-08)**:
   - Neither database records nor audit revisions are hard-deleted.
   - Approval of a correction or excuse updates the attendance record's effective `status` and `attendance_credit` and increments `version_no`, while simultaneously appending an `AttendanceRevision` record documenting:
     - `actor_user_id`: Authenticated reviewer's User ID.
     - `event_type`: `CORRECTION_APPROVED`, `CORRECTION_REJECTED`, `EXCUSE_APPROVED`, `ADMIN_OVERRIDE`, etc.
     - `previous_status`, `new_status`, `previous_credit`, `new_credit`.
     - `reason`: Mandatory human explanation.
     - `occurred_at_utc`: Authoritative server UTC timestamp.
   - Authorized reversals of prior revisions do **not** delete the prior revision; they create a new compensating `REVERSAL` revision restoring prior status while recording the `reversed_revision_id`.

5. **Section 38 Zero-Credit Invariant for Pre-Class Leave**:
   - Approved pre-class leave marks attendance status as `LEAVE`.
   - In accordance with Section 38 institutional policy, `LEAVE` grants exactly **0.00** attendance credit (`attendance_credit = 0.00`) and does **not** simulate or fabricate checkpoint verification credits.

6. **Absence Excuse Integrity**:
   - Approved excuses transition record status to `EXCUSED` with credit determined by policy snapshot (`excused_credit`, typically 0.00 or custom policy value).
   - No fake QR, BLE, or network presence tokens are injected.

7. **Risk Signals Inform, Never Decide (ADR-016 & Section 14)**:
   - M14 anti-cheat risk signals (e.g. proxy mismatch, rapid reuse) associated with a session or student are surfaced in review interfaces for situational awareness.
   - The attendance engine strictly prohibits automatic approvals, automatic rejections, or algorithmic penalties based solely on risk signals.

8. **Stale & Concurrent Review Protection**:
   - Request reviews utilize `SELECT ... FOR UPDATE` row locks.
   - Reviewing an already resolved request (`APPROVED` or `REJECTED`) is rejected with HTTP 400 `REQUEST_ALREADY_RESOLVED`.
   - Repeated idempotent requests with identical decision parameters return the existing state without creating duplicate `AttendanceRevision` ledger entries.

---

## 3. Database Architecture (`012_attendance_ops_corrections`)

### 3.1 Tables Created

1. **`attendance_correction_requests`**:
   - `id`: UUIDv7 (PK)
   - `university_id`: UUID (FK -> `universities.id`, RESTRICT)
   - `attendance_record_id`: UUID (FK -> `attendance_records.id`, RESTRICT)
   - `student_id`: UUID (FK -> `students.id`, RESTRICT)
   - `request_type`: VARCHAR(32) (`WRONG_ABSENT`, `WRONG_LATE`, `CHECKPOINT_NOT_RECORDED`, `TECHNICAL_FAILURE`, `DEVICE_FAILURE`, `NETWORK_FAILURE`, `QR_FAILURE`, `BLE_FAILURE`, `OFFLINE_SYNC_ISSUE`, `OTHER`)
   - `requested_status`: VARCHAR(20) (`PRESENT`, `LATE`)
   - `reason`: VARCHAR(1000)
   - `supporting_note`: VARCHAR(1000), nullable
   - `evidence_payload`: JSONB, nullable
   - `status`: VARCHAR(20) (`PENDING`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `CANCELLED`)
   - `reviewed_by_user_id`: UUID (FK -> `users.id`, SET NULL), nullable
   - `reviewed_at_utc`: TIMESTAMPTZ, nullable
   - `review_note`: VARCHAR(1000), nullable
   - Partial unique index: `uq_open_correction_request_per_record`

2. **`attendance_excuse_requests`**:
   - `id`: UUIDv7 (PK)
   - `university_id`: UUID (FK -> `universities.id`, RESTRICT)
   - `student_id`: UUID (FK -> `students.id`, RESTRICT)
   - `attendance_session_id`: UUID (FK -> `attendance_sessions.id`, SET NULL), nullable
   - `attendance_record_id`: UUID (FK -> `attendance_records.id`, SET NULL), nullable
   - `category`: VARCHAR(32) (`MEDICAL`, `BEREAVEMENT`, `FAMILY_EMERGENCY`, `OFFICIAL_UNIVERSITY_DUTY`, `MILITARY_GOVERNMENT`, `RELIGIOUS_OBSERVANCE`, `WEATHER_FORCE_MAJEURE`, `ACADEMIC_CONFLICT`, `OTHER`)
   - `description`: VARCHAR(1000)
   - `document_reference`: VARCHAR(255), nullable
   - `document_url`: VARCHAR(1000), nullable
   - `status`: VARCHAR(20) (`PENDING`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `CANCELLED`)
   - `reviewed_by_user_id`: UUID (FK -> `users.id`, SET NULL), nullable
   - `reviewed_at_utc`: TIMESTAMPTZ, nullable
   - `review_note`: VARCHAR(1000), nullable

3. **`attendance_leave_requests`**:
   - `id`: UUIDv7 (PK)
   - `university_id`: UUID (FK -> `universities.id`, RESTRICT)
   - `student_id`: UUID (FK -> `students.id`, RESTRICT)
   - `class_occurrence_id`: UUID (FK -> `class_occurrences.id`, RESTRICT)
   - `reason`: VARCHAR(1000)
   - `supporting_note`: VARCHAR(1000), nullable
   - `status`: VARCHAR(20) (`PENDING`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `CANCELLED`)
   - `reviewed_by_user_id`: UUID (FK -> `users.id`, SET NULL), nullable
   - `reviewed_at_utc`: TIMESTAMPTZ, nullable
   - `review_note`: VARCHAR(1000), nullable
   - Partial unique index: `uq_open_leave_request_per_occurrence`

---

## 4. API Endpoints (`/api/v1/attendance/operations/`)

| Method | Endpoint | Description | Permissions |
|---|---|---|---|
| `POST` | `/corrections` | Submit correction request | Student (own record) |
| `GET` | `/corrections/my` | List student's own corrections | Student |
| `GET` | `/corrections/queue` | Review queue of pending corrections | Lecturer, Admin, Officer |
| `POST` | `/corrections/{id}/review` | Approve or reject correction | Lecturer (scoped), Admin |
| `POST` | `/corrections/{id}/cancel` | Cancel own pending correction | Student (owner) |
| `POST` | `/excuses` | Submit absence excuse request | Student |
| `GET` | `/excuses/my` | List student's own excuses | Student |
| `GET` | `/excuses/queue` | Review queue of absence excuses | Lecturer, Admin, Officer |
| `POST` | `/excuses/{id}/review` | Approve or reject absence excuse | Lecturer (scoped), Admin |
| `POST` | `/leave` | Submit pre-class leave request | Student |
| `GET` | `/leave/my` | List student's own leaves | Student |
| `GET` | `/leave/queue` | Review queue of leave requests | Lecturer, Admin, Officer |
| `POST` | `/leave/{id}/review` | Approve or reject leave request | Lecturer (scoped), Admin |
| `POST` | `/overrides` | Privileged administrative status override | University/Faculty/Dept Admin |
| `POST` | `/reversals` | Create compensating revision for prior revision | Admin, Attendance Officer |
| `GET` | `/records/{id}/timeline` | Complete immutable revision history | Student (own), Staff, Auditor |
| `GET` | `/records/{id}/eligibility` | Check correction deadline & open requests | Student, Staff |
| `GET` | `/counts` | Summary counts for dashboard tabs | Lecturer, Admin, Officer |
| `GET` | `/manual-reviews` | Flagged manual/emergency attendance queue | Lecturer, Admin, Officer |
| `POST` | `/manual-reviews/{id}/confirm` | Confirm/adjust manual attendance record | Lecturer (scoped), Admin |
| `POST` | `/bulk-review` | Savepoint-isolated multi-request decision | Lecturer, Admin, Officer |

---

## 5. User Interfaces

### 5.1 Web Administration Console (`apps/web/src/app/admin/attendance/reviews/page.tsx`)
- **KPI Summary Cards**: Real-time counter badges for pending corrections, excuses, leave, and manual reviews.
- **Tabbed Review Queues**:
  1. *Corrections Queue*: Shows course, student, requested status, reason, window status, and M14 risk flags.
  2. *Absence Excuses Queue*: Category tags, document reference preview, and status actions.
  3. *Pre-Class Leave Queue*: Upcoming occurrence timetable details, Section 38 0-credit notice.
  4. *Flagged & Manual Sessions*: Displays emergency overrides and scanner anomalies.
- **Audit Revision Timeline Modal**: Full visual chronological audit trail detailing each status change, actor, and justification note.
- **Bulk Decision Action Bar**: Enables selective batch approval/rejection with progress tracking and isolated error handling.
- **Safety Dialogs**: Explicit confirmation modals for approvals, mandatory rejection reasons, and compensating reversal justifications.

### 5.2 Flutter Mobile Client (`apps/mobile/`)
- **`StudentAttendanceHistoryScreen`**: Dual-tab interface integrated into student home screen:
  - *Records Tab*: Historical attendance records with color-coded status badges, verification method tags, and "Request Correction" / "Submit Excuse" bottom sheet modals.
  - *My Requests Tab*: Filterable list of student's own requests (`PENDING`, `APPROVED`, `REJECTED`) with cancel capability for unreviewed items.
- **Eligibility Checking**: In-line validation prevents launching correction requests after window deadline or when another request is already active.

---

## 6. Role-Based Access Control (RBAC) Matrix

| Operation | Student | Assigned Lecturer | Unassigned Lecturer | Dept Admin | Faculty Admin | Uni Admin | Auditor |
|---|---|---|---|---|---|---|---|
| Submit Correction | Yes (own) | No | No | No | No | No | No |
| Cancel Correction | Yes (own, pending) | No | No | No | No | No | No |
| View My Requests | Yes (own) | No | No | No | No | No | No |
| Review Correction | No | Yes (assigned course) | Denied (403) | Yes (dept subtree) | Yes (faculty subtree) | Yes | Denied (403) |
| Review Excuse | No | Yes (assigned course) | Denied (403) | Yes (dept subtree) | Yes (faculty subtree) | Yes | Denied (403) |
| Review Leave | No | Yes (assigned course) | Denied (403) | Yes (dept subtree) | Yes (faculty subtree) | Yes | Denied (403) |
| Admin Override | No | No | No | Yes (dept subtree) | Yes (faculty subtree) | Yes | Denied (403) |
| Revision Reversal | No | No | No | Yes (dept subtree) | Yes (faculty subtree) | Yes | Denied (403) |
| View Timeline | Yes (own record) | Yes (assigned course) | Denied (403) | Yes (dept subtree) | Yes (faculty subtree) | Yes | Yes (Read-Only) |
| Cross-University | Denied (403) | Denied (403) | Denied (403) | Denied (403) | Denied (403) | Denied (403) | Denied (403) |

---

## 7. Verification & Testing

- **Backend Automated Tests (23/23 passing)**:
  - `test_attendance_corrections.py`: Submission, 24h deadline boundary (deadline - 1s vs deadline + 1s), duplicate open request prevention, review lifecycle, admin overrides, revision reversals.
  - `test_attendance_operations_rbac.py`: Role boundaries, permission checks, subtree scoping.
  - `test_attendance_overrides_and_audit.py`: Mandatory justification enforcement, revision ledger immutability.
  - `test_attendance_operations_e2e.py`: Full end-to-end integration, excuse lifecycle, leave zero-credit rule, manual review queue, bulk review atomicity, stale conflict handling, and cross-tenant isolation.
- **Zero Real Sleeps**: All tests inject fake UTC timestamps via `utc_now()` mocking.
- **Migration Verification**: `012_attendance_ops_corrections` verified reversible (`downgrade 011` -> `upgrade head` -> `alembic check` with zero schema drift).
- **Client Quality**:
  - Web: `npm run lint`, `npm run type-check`, `npm run build` (Turbopack, 7/7 routes clean).
  - Mobile: `dart format`, `flutter analyze` (0 issues), `flutter test` (54/54 passed).
  - Governance: `check_secrets.py` (clean), `check_docs.py` (clean).

---

## 8. Milestone 16 Boundary

Milestone 15 is strictly bounded to attendance operations, corrections, excuses, leaves, and immutable audit timelines.
The following features are **explicitly deferred to Milestone 16**:
- Batch bulk CSV/Excel student, lecturer, and timetable imports.
- Row-level import staging, preview, and error reconciliation.
- Institutional attendance percentage threshold reporting (e.g. 75% rule alerts).
- PDF/CSV downloadable aggregated attendance ledgers.
