# Milestone 16: Imports, Reports & Administration

**Version:** 1.0  
**Approved Scope:** Comprehensive institutional data ingestion pipeline for Students, Lecturers, Courses, Course Offerings, Enrollments, and Timetables with two-phase staging, pre-commit validation preview, row-level error reporting, and safe atomic commits (STRICT and PARTIAL modes); Authoritative institutional attendance reports across Course Roster, Student multi-course summaries, Session operational statistics, Department and Faculty subtrees, and Lecturer assignments; Configurable attendance threshold evaluation with neutral status indicators (`ABOVE_THRESHOLD`, `NEAR_THRESHOLD`, `BELOW_THRESHOLD`) and decimal-safe boundary logic; Downloadable CSV and XLSX exports hardened against CSV formula injection (`=`, `+`, `-`, `@`, `\t`, `\r`) and Excel UTF-8 BOM compatibility; Centralized web administrative console (`/admin/imports`, `/admin/reports/attendance`, `/admin/settings/attendance`); Student mobile attendance summary tab with pull-to-refresh; Zero-denominator attendance safety; Frozen historical roster protection; and Migration 013 database schema.

---

## 1. Executive Summary

Milestone 16 establishes the administrative back-office and analytical reporting capabilities of the Digital Student Attendance System. High-throughput universities require reliable data import workflows to onboard thousands of students, lecturers, curriculum courses, and semester timetables without corrupting production state or crashing operational services. Furthermore, registrars, deans, department chairs, lecturers, and students require transparent, real-time analytics to monitor attendance compliance against the institutional 75% minimum threshold without evaluative discipline or automated sanctions.

Milestone 16 delivers this end-to-end functionality across backend services, database migrations, web admin consoles, and mobile clients while upholding all foundational system invariants:
- **No Direct Mutation Before Commit**: File uploads parse and stage rows in dedicated staging tables (`import_jobs`, `import_staged_rows`). Production domain entities are mutated only upon explicit administrator confirmation.
- **Strict Atomicity & Reviewable Staging**: In `STRICT` commit mode, a single blocking row error halts production commit, preserving the staging table for inspection. In `PARTIAL` mode, valid rows commit while invalid rows are skipped.
- **Idempotency & Concurrency Safety**: Commit operations utilize row-level locking (`with_for_update`) on the import job header. Retrying a committed job returns deterministic conflict status (HTTP 409) without duplicating entities.
- **Frozen History Invariant**: Ingesting late enrollments or timetable alterations changes future scheduling only; past closed sessions, rosters, evidence, and audit logs remain permanently frozen.
- **Formula Injection Defense & Export Parity**: Export endpoints enforce strict sanitization prepending `'` to dangerous spreadsheet characters (`=`, `+`, `-`, `@`, `\t`, `\r`) and prepend UTF-8 BOM (`\ufeff`) for proper Dari/Pashto script rendering in Excel.
- **Neutral Attendance Thresholding**: Attendance percentage is evaluated into non-judgmental states (`ABOVE_THRESHOLD`, `NEAR_THRESHOLD` within 5% margin, `BELOW_THRESHOLD`). Thresholds never trigger automatic academic failure or disciplinary actions.
- **Zero-Denominator Safety**: When a student has zero conducted sessions in a course, the reporting engine returns 100.0% without division-by-zero, NaN, or Infinity errors.

---

## 2. Supported Import Domains & Capabilities

Milestone 16 implements high-throughput parsers and domain processors for 6 institutional entities:

| Import Domain | Required Columns | Optional Columns | Supported Actions | Foreign Key Validations |
| :--- | :--- | :--- | :--- | :--- |
| **STUDENTS** | `student_number`, `first_name`, `last_name` | `email`, `phone`, `academic_unit_code`, `admission_date` | `CREATE`, `UPDATE` | `AcademicUnit` code |
| **LECTURERS** | `employee_code`, `first_name`, `last_name` | `email`, `phone`, `academic_unit_code`, `title` | `CREATE`, `UPDATE` | `AcademicUnit` code |
| **COURSES** | `code`, `name`, `credits`, `academic_unit_code` | `description` | `CREATE`, `UPDATE` | `AcademicUnit` code |
| **COURSE_OFFERINGS** | `course_code`, `semester_code` | `section_code`, `capacity` | `CREATE`, `UPDATE` | `Course`, `Semester`, `Section` |
| **ENROLLMENTS** | `student_number`, `course_code`, `semester_code` | `section_code` | `CREATE`, `SKIP` (if duplicate) | `Student`, `CourseOffering` |
| **TIMETABLES** | `course_code`, `semester_code`, `day_of_week`, `start_time`, `end_time` | `section_code`, `room_building`, `room_number`, `lecturer_code` | `CREATE` | `CourseOffering`, `Room`, `Lecturer` |

### File Format & Parsing Rules
- **Formats**: RFC 4180 CSV (`text/csv`) and Microsoft Excel 2007+ OpenXML Spreadsheet (`.xlsx`).
- **Encoding**: UTF-8 and UTF-8 with BOM (`utf-8-sig`) natively decoded, preserving Afghan Perso-Arabic scripts (Dari and Pashto).
- **Unicode Normalization**: NFKC normalization applied to all text cells; whitespace trimmed. Empty strings normalize to `None`.
- **Limits**: Maximum upload size: 10 MB (`10,485,760` bytes). Maximum data rows: 5,000 per file. Exceeding limits rejects the upload immediately with HTTP 422 `VALIDATION_ERROR`.
- **Header Normalization**: Headers are case-insensitive and normalized to snake_case (e.g., `Student ID` $\rightarrow$ `student_id`, `First Name` $\rightarrow$ `first_name`).

---

## 3. Two-Phase Import Architecture & Staging Lifecycle

```
[Administrator Upload] 
         │ (CSV / XLSX)
         ▼
[ImportParser: parse_import_file()] ── Validate max_bytes, max_rows, UTF-8 BOM
         │
         ▼
[ImportProcessor: validate_and_stage()] ── Entity validation, foreign key resolution
         │
         ▼
[Database Staging Tables]
  ├── import_jobs (Header: READY, PENDING, COMMITTING, COMPLETED, CANCELLED)
  └── import_staged_rows (Row status: VALID, WARNING, ERROR)
         │
         ▼
[Administrator Preview via /admin/imports] ── Inspect summary, errors, warnings
         │
  ┌──────┴────────────────────────┐
  ▼                               ▼
[Commit: STRICT Mode]           [Commit: PARTIAL Mode]
Requires error_count == 0       Commits valid rows
Rejects on any row error        Skips error rows
         │                               │
         └───────────────┬───────────────┘
                         ▼
             [processor.commit_row()] ── Row-locked via with_for_update()
                         │
                         ▼
             [Production Domain Tables]
             (users, students, lecturers, courses, etc.)
```

### Staging Tables (`013_imports_administration`)
1. `import_jobs`:
   - `id`: UUID primary key.
   - `university_id`: Multi-tenant boundary.
   - `created_by_user_id`: Attributed actor.
   - `import_type`: Enum string (`STUDENTS`, `LECTURERS`, etc.).
   - `commit_mode`: `STRICT` or `PARTIAL`.
   - `status`: `PENDING`, `READY`, `COMMITTING`, `COMPLETED`, `FAILED`, `CANCELLED`.
   - `row_count`, `valid_count`, `warning_count`, `error_count`, `commit_count`.
   - `summary_json`: Metadata containing actor ID, execution timestamp, created and updated samples.
2. `import_staged_rows`:
   - `id`: UUID primary key.
   - `job_id`: Foreign key to `import_jobs`.
   - `row_number`: 1-indexed spreadsheet line number.
   - `raw_data_json`: Raw parsed row payload.
   - `normalized_data_json`: Cleaned payload with type coercion.
   - `action`: `CREATE` or `UPDATE`.
   - `status`: `VALID`, `WARNING`, `ERROR`, `COMMITTED`, `SKIPPED`.
   - `errors_json`: Itemized list of errors `[{"code": "...", "message": "..."}]`.
   - `warnings_json`: Itemized list of non-blocking warnings.
   - `resolved_entity_id`, `resolved_entity_type`: Target entity linkage.

---

## 4. Timetable Conflict Detection Engine

The timetable processor enforces scheduling sanity across institutional resources before allowing class occurrence generation:
1. **Time Window Consistency**: `start_time` must precede `end_time` (e.g., 08:30 < 10:00).
2. **Day of Week Range**: Validated against integer days 0–6 (Monday through Sunday) or named days.
3. **Room Availability Conflict**: Detects overlapping class occurrences scheduled in the same room on the same day during overlapping time slots:
   $$\text{Slot}_A \cap \text{Slot}_B \neq \emptyset \iff \max(\text{Start}_A, \text{Start}_B) < \min(\text{End}_A, \text{End}_B)$$
4. **Lecturer Availability Conflict**: Detects overlapping class occurrences assigned to the same instructor.
5. **Section Availability Conflict**: Detects overlapping class occurrences scheduled for the same student cohort section.

---

## 5. Attendance Reporting & Threshold Engine

### Authoritative Attendance Percentage Formula
For any student enrolled in a course offering, the attendance percentage is computed authoritatively by the server domain engine:

$$\text{Attendance Percentage} = \begin{cases} 
\min\left(100.0, \max\left(0.0, \text{round}\left(\frac{\sum \text{attendance\_credit}}{\text{eligible\_sessions}} \times 100.0, 1\right)\right)\right), & \text{if } \text{eligible\_sessions} > 0 \\ 
100.0, & \text{if } \text{eligible\_sessions} = 0 
\end{cases}$$

Where:
- **Eligible Sessions**: Total closed class sessions conducted for which the student was expected to attend.
- **Attendance Credit Allocation**:
  - `PRESENT`: 1.00 credit.
  - `LATE`: Pro-rated credit (default: 0.50 credit, configurable per policy).
  - `ABSENT`: 0.00 credit.
  - `EXCUSED`: 1.00 credit (excused absence per approved medical/institutional excuse).
  - `LEAVE`: 0.00 credit (Section 38: approved leave excuses absence without attendance simulation; excluded from denominator or credited at 0.00 without disciplinary penalty).
- **Revision Reflection**: M15 approved corrections dynamically adjust `attendance_credit` and `status` in the effective record while retaining audit history.
- **Zero-Denominator Defense**: When `eligible_sessions == 0`, percentage defaults to `100.0%` (safe non-penalizing neutral value), completely preventing division-by-zero, NaN, or Infinity errors.

### Configurable Thresholds & Neutral States
Attendance compliance is categorized using decimal-safe comparison:
- **Default Threshold**: 75.0% (configurable between 0.0% and 100.0% via attendance policy).
- **Default Warning Margin**: 5.0%.
- **States**:
  1. `ABOVE_THRESHOLD`: $\text{Percentage} \ge \text{Threshold}$ (e.g., $\ge 75.0\%$).
  2. `NEAR_THRESHOLD`: $\text{Threshold} - \text{Margin} \le \text{Percentage} < \text{Threshold}$ (e.g., $[70.0\%, 75.0\%)$).
  3. `BELOW_THRESHOLD`: $\text{Percentage} < \text{Threshold} - \text{Margin}$ (e.g., $< 70.0\%$).
- **Policy Invariant**: Threshold states are informational and non-punitive. They do not trigger automatic failure, academic suspension, or grading sanctions.

---

## 6. Export Security & Formula Injection Defense

Export endpoints (`/reports/attendance/.../export`) support both UTF-8 CSV and macro-free XLSX formats.

### CSV Formula Injection Defense
Spreadsheet applications (Microsoft Excel, LibreOffice Calc, Google Sheets) interpret leading characters `=, +, -, @, \t, \r` as formulas or shell commands (DDE). The export engine applies `sanitize_cell_value()` to all exported fields:
- If a string starts with `=, +, -, @, \t, \r`, it is prefixed with an apostrophe (`'`).
- Example: `=1+1` $\rightarrow$ `'=1+1`.
- Numeric values (integers, floats) and safe text (e.g., `CS-101`) remain unquoted.
- UTF-8 Byte Order Mark (`\ufeff`) is prepended to CSV responses to ensure Excel opens non-Latin text (Dari/Pashto) seamlessly without mojibake.

### XLSX Security
Excel files are generated using `openpyxl` with macro support disabled (`.xlsx` format, not `.xlsm`). No external formulas, VBA scripts, or dynamic hyperlinks are embedded.

---

## 7. Web & Mobile Client Interfaces

1. **Next.js Web Admin Console**:
   - `/admin/imports`: Comprehensive Import Center supporting entity selection, CSV/XLSX template downloads, drag-and-drop file upload, validation preview with errors/warnings breakdown, strict/partial commit actions, and historical import logs.
   - `/admin/reports/attendance`: Attendance Dashboard providing course offering selection, student attendance breakdown tables, neutral threshold status badges, KPI summary metrics, and UTF-8 BOM CSV / macro-free XLSX export triggers.
   - `/admin/settings/attendance`: Centralized Attendance Policy Management featuring prospective application notices, threshold slider, late minutes grace window, correction window deadline, and mandatory audit justification.
2. **Flutter Mobile Application**:
   - `StudentAttendanceHistoryScreen`: Integrated 3-tab layout (`Attendance Records`, `Summary`, `My Requests`).
   - Summary tab displays overall attendance percentage circular badge, enrolled courses progress bars, threshold status chips, and session breakdown badges.

---

## 8. Role-Based Access Control (RBAC) & Tenant Isolation

Two new permissions added to `PermissionCode`:
- `reports.attendance.read` (`PermissionCode.REPORTS_ATTENDANCE_READ`)
- `reports.attendance.export` (`PermissionCode.REPORTS_ATTENDANCE_EXPORT`)

System permission count: **82 permissions across 8 system roles**.
- `STUDENT`: Can view own attendance summary (`/reports/attendance/student/me`). Cannot view other students (IDOR prevented). Cannot import data or edit policies.
- `LECTURER`: Can view reports for assigned course offerings. Cannot view unassigned courses or perform institution-wide imports.
- `ATTENDANCE_OFFICER`: Can view operational reports and review attendance requests within designated scope.
- `DEPARTMENT_ADMIN`: Scoped to department academic subtree.
- `FACULTY_ADMIN`: Scoped to faculty academic subtree.
- `UNIVERSITY_ADMIN` & `SUPER_ADMIN`: Institutional-wide access.
- `AUDITOR`: Read-only access to attendance reports and export ledgers. Cannot modify policy configurations.

---

## 9. Verification & Quality Gates Summary

- **Backend Unit & Integration Tests**: 40 passed across import parsers, student import, lecturer import, course import, offering import, enrollment import, timetable import, import RBAC, attendance thresholds, report exports, report RBAC, reports service, and import hardening.
- **Static Quality**:
  - `ruff check backend`: 0 errors.
  - `ruff format --check backend`: 240 files formatted.
  - `mypy backend`: 0 errors across 240 source files.
- **Web Console**:
  - `type-check`: Passed.
  - `lint`: 0 warnings, 0 errors.
  - `build`: Production build successful (all routes compiled).
- **Mobile App**:
  - `dart format`: 100% compliant.
  - `flutter analyze`: 0 issues.
  - `flutter test`: 56 passed.
- **Security & Schema**:
  - `python scripts/check_secrets.py`: 0 secrets exposed.
  - `alembic check`: 0 schema drift on head `013_imports_administration`.
  - Docker Compose: All services (`backend`, `postgres`, `redis`, `web`, `worker`) healthy.

---

## 10. Milestone 17 Boundary & Handoff

Milestone 16 strictly addresses data ingestion, analytical reporting, and policy administration. The following items are explicitly reserved for **Milestone 17: Complete MVP User Experience**:
- End-to-end user experience polish and unified role dashboards (Student, Lecturer, Admin).
- Full bilingual localization (Pashto/Dari/English) with RTL layout enforcement.
- Global navigation consistency, comprehensive loading/empty/error states, and onboarding flows.
- Removal of placeholder/mock interfaces and unified end-to-end manual acceptance testing.
