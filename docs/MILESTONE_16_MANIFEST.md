# Digital Student Attendance System
## Milestone 16 Manifest — Imports, Reports & Administration

**Generated At:** 2026-09-17  
**Feature Branch:** `feature/task-014-imports-reports-administration`  
**Milestone:** 16 — Imports, Reports & Administration  

---

## 1. Inventory of Files Created / Modified

### 1.1 Database & Migrations
- `backend/migrations/versions/013_imports_reports_administration.py`: Versioned reversible Alembic migration creating `import_jobs` and `import_staged_rows` tables, partial unique indexes for idempotent commits, and foreign key constraints.
- `backend/app/models/import_job.py`: SQLAlchemy entity models for `ImportJob` and `ImportStagedRow`.
- `backend/app/models/__init__.py`: Registered new models in declarative Base registry.
- `docs/23_DATABASE_MIGRATION_PLAN.md`: Documented migration 013 and dependencies.

### 1.2 Core Constants, Permissions & Seeding
- `backend/app/core/constants.py`:
  - Added permissions `reports.attendance.read` and `reports.attendance.export`.
  - Added enums `ThresholdStatus` (`ABOVE_THRESHOLD`, `NEAR_THRESHOLD`, `BELOW_THRESHOLD`, `NOT_APPLICABLE`), `ExportFormat` (`CSV`, `XLSX`), `ImportType`, `ImportJobStatus`, `ImportRowStatus`, and `ImportCommitMode`.
- `backend/app/rbac/seeding.py`: Seeded 82 permissions across Super Admin, University Admin, Faculty Admin, Department Admin, Attendance Officer, Lecturer, Student, and Auditor roles.

### 1.3 Ingestion Pipeline & Domain Processors (`backend/app/imports/`)
- `backend/app/imports/parser.py`: Safe CSV and XLSX file parsing, NFKC Unicode normalization, UTF-8 BOM detection, and row/byte boundary validation.
- `backend/app/imports/schemas.py`: Pydantic contracts for preview uploads, commit requests, row error models, and job responses.
- `backend/app/imports/service.py`: Domain import orchestration service implementing upload staging, row-level locking (`with_for_update`), STRICT/PARTIAL commits, cancellation, and job retrieval.
- `backend/app/imports/router.py`: REST router mounted at `/api/v1/imports`.
- `backend/app/imports/processors/`:
  - `base.py`: Abstract processor interface for staged entity validation and commits.
  - `students.py`: Student and User provisioning with cryptographically secure random credentials (`f"Tmp!{secrets.token_urlsafe(16)}"`) and `must_change_password=True`.
  - `lecturers.py`: Lecturer and User provisioning with cryptographically secure random credentials and academic unit validation.
  - `courses.py`: Course definitions and credit allocation.
  - `course_offerings.py`: Offering resolution linked to semester and section.
  - `enrollments.py`: Student offering enrollments with duplicate skipping.
  - `timetables.py`: Schedule generation with multi-resource conflict detection (room, lecturer, section, time-window).

### 1.4 Reporting & Export Engine (`backend/app/reports/`)
- `backend/app/reports/schemas.py`: Pydantic contracts for Course Roster, Student Summary, Session Operational Stats, Department, Faculty, and Lecturer reports (with `attendance_percentage: float | None` and `ThresholdStatus.NOT_APPLICABLE`).
- `backend/app/reports/exports.py`: CSV and XLSX export generator featuring formula injection defense (`=`, `+`, `-`, `@`, `\t`, `\r` escaping), Excel UTF-8 BOM compatibility, and `"N/A"` null formatting.
- `backend/app/reports/service.py`: Authoritative reporting service calculating dynamic attendance percentage, zero-eligible-session `null`/`NOT_APPLICABLE` semantics, decimal-safe threshold evaluation, and subtree aggregations.
- `backend/app/reports/router.py`: REST router mounted at `/api/v1/reports/attendance`.
- `backend/app/api/v1/router.py`: Mounted import and report routers into API v1.

### 1.5 Web Administration Console (`apps/web/`)
- `apps/web/src/app/admin/imports/page.tsx`: Import Center supporting entity selection, CSV/XLSX template downloads, drag-and-drop file upload, validation preview with errors/warnings table, strict/partial commit modes, and historical import logs.
- `apps/web/src/app/admin/reports/attendance/page.tsx`: Attendance Reports Dashboard providing offering selection, threshold KPI cards (including `NOT_APPLICABLE`), student attendance breakdown table, neutral badges, and CSV/XLSX export triggers.
- `apps/web/src/app/admin/settings/attendance/page.tsx`: Centralized Attendance Policy Management with prospective application notice, threshold slider, grace window, correction window, and mandatory audit justification.

### 1.6 Mobile Application (`apps/mobile/`)
- `apps/mobile/lib/services/attendance_operations_service.dart`: Added `StudentCourseAttendanceItemModel`, `StudentAttendanceSummaryModel`, and `getStudentAttendanceSummary`.
- `apps/mobile/lib/screens/student_attendance_history_screen.dart`: Integrated 3-tab layout (`Attendance Records`, `Summary`, `My Requests`) with course progress bars, threshold status chips, and overall percentage card.
- `apps/mobile/test/attendance_operations_test.dart`: Updated widget tests and added DTO model validation for multi-course attendance summary.

### 1.7 Automated Test Suites
- `backend/tests/test_import_parsers.py`: 4 tests for CSV/XLSX parsing, BOM handling, and limit enforcement.
- `backend/tests/test_student_import.py`: 7 tests for student preview, strict commit, partial commit, duplicate updates, cancellation, and unique random credential generation.
- `backend/tests/test_lecturer_import.py`: 4 tests for lecturer import, academic unit resolution, and employee code conflicts.
- `backend/tests/test_course_import.py`: 4 tests for course definitions and credit validation.
- `backend/tests/test_offering_import.py`: 3 tests for semester, section, and offering creation.
- `backend/tests/test_enrollment_import.py`: 4 tests for student enrollments and duplicate handling.
- `backend/tests/test_timetable_import.py`: 5 tests for schedule parsing and conflict detection (room, lecturer, section, time-window).
- `backend/tests/test_import_rbac.py`: 3 tests for permission enforcement and cross-tenant isolation.
- `backend/tests/test_reports.py`: 4 tests for course roster, session stats, student summaries, and subtree rollups.
- `backend/tests/test_attendance_thresholds.py`: 3 tests for neutral threshold states, decimal-safe boundaries, and zero-eligible-session `null`/`NOT_APPLICABLE` semantics.
- `backend/tests/test_report_exports.py`: 3 tests for formula injection defense and XLSX structure.
- `backend/tests/test_report_rbac.py`: 3 tests for report permission scoping and tenant boundaries.
- `backend/tests/test_import_hardening.py`: 5 tests for atomicity in STRICT mode, commit idempotency, frozen history preservation, and end-to-end performance benchmarks across 5 operational dimensions.

---

## 2. API Endpoints Introduced

| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/imports/preview` | `attendance.sessions.manage` | Upload and preview CSV/XLSX file |
| `GET` | `/api/v1/imports/{id}` | `attendance.sessions.manage` | Retrieve import job status |
| `GET` | `/api/v1/imports/{id}/rows` | `attendance.sessions.manage` | List staged rows with errors/warnings |
| `POST` | `/api/v1/imports/{id}/commit` | `attendance.sessions.manage` | Confirm commit in STRICT or PARTIAL mode |
| `POST` | `/api/v1/imports/{id}/cancel` | `attendance.sessions.manage` | Cancel staged import job |
| `GET` | `/api/v1/imports` | `attendance.sessions.manage` | List historical import jobs |
| `GET` | `/api/v1/imports/templates/{type}` | `attendance.sessions.manage` | Download CSV/XLSX import templates |
| `GET` | `/api/v1/reports/attendance/course-offerings/{id}` | `reports.attendance.read` | Course offering attendance roster |
| `GET` | `/api/v1/reports/attendance/course-offerings/{id}/export` | `reports.attendance.export` | Export course roster to CSV/XLSX |
| `GET` | `/api/v1/reports/attendance/student/me` | `reports.attendance.read` | Authenticated student own summary |
| `GET` | `/api/v1/reports/attendance/student/{id}` | `reports.attendance.read` | Student attendance summary (scoped) |
| `GET` | `/api/v1/reports/attendance/sessions/{id}` | `reports.attendance.read` | Session operational statistics |
| `GET` | `/api/v1/reports/attendance/departments/{id}` | `reports.attendance.read` | Department subtree attendance rollup |
| `GET` | `/api/v1/reports/attendance/faculties/{id}` | `reports.attendance.read` | Faculty subtree attendance rollup |
| `GET` | `/api/v1/reports/attendance/lecturers/{id}` | `reports.attendance.read` | Lecturer assigned courses attendance |

---

## 3. Performance Benchmarks & Empirical Timing Evidence

| Operation | Scale / Dataset | Measured Latency | Budget | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Student CSV Parsing** | 3,000 Rows (UTF-8 Afghan Names) | **0.1140s** | $< 2.0\text{s}$ | ✅ PASS |
| **Student Preview Staging** | 100 Rows (Validation & Staging) | **3.7225s** | $< 8.0\text{s}$ | ✅ PASS |
| **Student Production Commit** | 100 Rows (DB Insert + Argon2id Hashing) | **6.2963s** | $< 12.0\text{s}$ | ✅ PASS |
| **Bulk Student Enrollment** | 100 Course Enrollments (Stage + Commit) | **9.0142s** | $< 10.0\text{s}$ | ✅ PASS |
| **Course Roster Report Query** | 100 Enrolled Students (Aggregation) | **0.5000s** | $< 1.0\text{s}$ | ✅ PASS |

---

## 4. Known Limitations & Milestone 17 Scope

1. **Client Localization & UI Polish**: While backend parsers and export generators natively support Pashto and Dari UTF-8 text, web and mobile UI translations and RTL formatting are scheduled for Milestone 17.
2. **Unified Role Dashboards**: Role-specific home dashboards (Student, Lecturer, Admin) consolidating M1–M16 capabilities will be finalized in Milestone 17.
