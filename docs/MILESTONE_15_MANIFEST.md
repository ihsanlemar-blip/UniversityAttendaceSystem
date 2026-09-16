# Digital Student Attendance System
## Milestone 15 Manifest — Attendance Operations, Corrections, Excuses, Leave & Immutable Workflows

**Generated At:** 2026-09-17  
**Feature Branch:** `feature/task-013-attendance-operations-corrections`  
**Milestone:** 15 — Attendance Operations, Corrections, Excuses, Leave & Immutable Workflows  

---

## 1. Inventory of Files Created / Modified

### 1.1 Database & Migrations
- `backend/migrations/versions/012_attendance_ops_corrections.py`: Versioned reversible Alembic migration creating `attendance_correction_requests`, `attendance_excuse_requests`, and `attendance_leave_requests` tables, partial unique indexes for single-open-request invariants, and PostgreSQL enum types.
- `backend/app/models/attendance_correction.py`: SQLAlchemy entity models for `AttendanceCorrectionRequest`, `AttendanceExcuseRequest`, and `AttendanceLeaveRequest`.
- `backend/app/models/attendance_record.py`: Eager relationship mapping for revisions and student details.
- `backend/app/models/__init__.py`: Registered new models in declarative Base registry.
- `docs/23_DATABASE_MIGRATION_PLAN.md`: Documented migration 012 and dependencies.

### 1.2 Core Constants, Permissions & Seeding
- `backend/app/core/constants.py`: Added 6 operational permissions (`attendance.corrections.request`, `attendance.corrections.review`, `attendance.corrections.override`, `attendance.excuses.request`, `attendance.excuses.review`, `attendance.leave.request`), audit event types (`CORRECTION_REQUESTED`, `CORRECTION_APPROVED`, `CORRECTION_REJECTED`, `EXCUSE_REQUESTED`, `EXCUSE_APPROVED`, `EXCUSE_REJECTED`, `LEAVE_REQUESTED`, `LEAVE_APPROVED`, `LEAVE_REJECTED`, `REVERSAL`), and enums (`CorrectionRequestType`, `CorrectionRequestStatus`, `ExcuseCategory`, `ExcuseRequestStatus`, `LeaveRequestStatus`).
- `backend/app/rbac/seeding.py`: Seeded operational permissions across Super Admin, University Admin, Faculty Admin, Department Admin, Lecturer, Student, and Auditor roles.

### 1.3 Operations Domain Service & API Router (`backend/app/attendance/`)
- `backend/app/attendance/operations_schemas.py`: Request and response schemas for corrections, excuses, leave requests, administrative overrides, compensating reversals, timelines, eligibility checks, queue items, and bulk review batches.
- `backend/app/attendance/operations_service.py`: Domain operations service implementing:
  - `check_correction_window`: Server UTC 24h deadline calculation from closed session snapshot.
  - `submit_correction_request` / `cancel_correction_request`: Student self-service lifecycle with single open request validation.
  - `review_correction_request`: Scoped reviewer approval/rejection with row-level locking, version increment, and immutable `AttendanceRevision` generation.
  - `admin_override`: Out-of-window administrative adjustments with mandatory justification (INV-08).
  - `reverse_revision`: Non-destructive compensating reversal creating a new `REVERSAL` audit revision (INV-06).
  - `submit_excuse_request` / `review_excuse_request`: Absence excuse workflow updating records to `EXCUSED` without fake tokens.
  - `submit_leave_request` / `review_leave_request`: Pre-class leave workflow enforcing Section 38 zero-credit invariant.
  - `get_record_timeline`: Chronological audit trail retrieval with actor attribution.
  - `check_record_eligibility`: Real-time student eligibility and window deadline check.
  - `get_manual_reviews_queue` / `confirm_manual_review`: Deliberate human confirmation of manual/emergency attendance.
  - `bulk_review`: Savepoint-isolated multi-item review batch execution.
- `backend/app/attendance/operations_router.py`: REST router mounted at `/api/v1/attendance/operations`.
- `backend/app/api/v1/router.py`: Mounted operations router into API v1.

### 1.4 Web Administration Console (`apps/web/`)
- `apps/web/src/app/admin/attendance/reviews/page.tsx`: Production review console featuring:
  - KPI summary counters for pending corrections, excuses, leave, and manual reviews.
  - 4 review queues (Corrections, Excuses, Leave, Manual & Flagged).
  - Multi-factor risk indicators and M14 anti-cheat diagnostics badges.
  - Approval, rejection, administrative override, and compensating reversal action modals.
  - Bulk review action bar with progress feedback and error isolation.
  - Immutable revision timeline drawer with actor attribution.
  - Stale conflict handling (`HTTP 409` / `REQUEST_ALREADY_RESOLVED`).

### 1.5 Mobile Application (`apps/mobile/`)
- `apps/mobile/lib/services/attendance_operations_service.dart`: Client API service for corrections, excuses, leave, eligibility, and timelines.
- `apps/mobile/lib/screens/student_attendance_history_screen.dart`: Student history screen with Records and My Requests dual tabs, bottom sheets for submission, cancel action, and revision timeline view.
- `apps/mobile/lib/main.dart`: Integrated navigation card into student home screen.

### 1.6 Automated Test Suites
- `backend/tests/test_attendance_corrections.py`: 9 tests verifying submission, 24h deadline boundaries, duplicate prevention, approval/rejection, admin overrides, and reversals.
- `backend/tests/test_attendance_operations_rbac.py`: 2 tests verifying student, lecturer, and auditor role permissions and boundary restrictions.
- `backend/tests/test_attendance_overrides_and_audit.py`: 4 tests verifying non-empty justification requirement, append-only ledger immutability, and actor attribution.
- `backend/tests/test_attendance_operations_e2e.py`: 8 tests verifying end-to-end excuse lifecycle, Section 38 leave zero-credit rule, manual review confirmation, bulk review atomicity, stale conflict handling, dashboard counts, and cross-tenant isolation.
- `apps/mobile/test/attendance_operations_test.dart`: DTO serialization, Section 38 zero-credit validation, offline safety check, and widget rendering tests.

### 1.7 CI/CD Pipeline Configuration
- `.github/workflows/ci.yml`: Added `test_attendance_operations_rbac.py` to Shard 1, and `test_attendance_corrections.py` and `test_attendance_operations_e2e.py` to Shard 4 (achieving 59/59 test files sharded).

---

## 2. Key Commits

- `978a206`: `feat(attendance-ops): implement corrections, excuses, leave & immutable workflow foundation (M15 Part 1)`
- `12c44b2`: `feat(attendance-ops): Milestone 15 Part 2 - Operational UI, review queues, audit timelines & E2E integration`

---

## 3. Known Limitations & Non-Goals (Milestone 16 Boundaries)

- Bulk student/lecturer enrollment CSV/Excel imports belong to Milestone 16.
- Institutional aggregate attendance reporting (75% threshold tracking) belongs to Milestone 16.
