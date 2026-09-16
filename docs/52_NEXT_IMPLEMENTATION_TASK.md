# Next Implementation Task: Milestone 16 — Imports, Reports & Administration

**Status:** Up Next (Do NOT begin implementation in Milestone 15 task)  
**Applies to:** Next Coding Agent Milestone Handoff  

---

## 1. Task Objective

Implement **Milestone 16: Imports, Reports & Administration** for the Digital Student Attendance System. Milestone 16 introduces high-throughput institutional data ingestion (Excel / CSV imports for students, lecturers, courses, enrollments, and timetables with validation preview and row-level error staging) alongside comprehensive attendance analytics, 75% threshold compliance alerts, official downloadable exports, and administrative operational dashboards.

---

## 2. Invariants & Guardrails (Mandatory)

1. **Transaction Staging & Validation Preview**:
   - Institutional imports (Excel/CSV) must parse, validate, and present a preview of changes before applying them to core academic and identity tables.
   - Row-level errors must be itemized clearly (e.g. invalid email format, duplicate student number, non-existent department ID) without aborting the entire batch preview.
2. **Immutable Attendance Aggregation**:
   - Attendance reports and 75% threshold metrics must be calculated dynamically from finalized `AttendanceRecord` outcomes and `AttendanceRevision` ledgers.
   - Reporting queries must respect university and academic subtree RBAC boundaries without leaking cross-tenant data.
3. **Downloadable Audit Trail**:
   - Official downloadable exports (CSV / Excel / PDF) must reflect the authoritative state of the attendance records at generation time and log an export audit entry attributing the requesting administrator.
4. **Preserve Fast Testing Strategy**:
   - Maintain sharded CI execution with real PostgreSQL 16 and Redis 7 service containers.
   - Maintain zero real-world sleeps (`time.sleep` / `asyncio.sleep`).

---

## 3. Anticipated Milestone 16 Scope

1. **Institutional Data Imports**:
   - Excel (`.xlsx`) and CSV parsing services for:
     - Students & User accounts
     - Lecturers & Academic profile assignments
     - Courses & Course Offerings
     - Student Enrollments
     - Timetables & Class Schedules
   - Two-phase import workflow: Upload & Staged Validation Preview -> Admin Confirmation & Atomic Ingestion.
   - Row-level import error tracking table (`import_jobs`, `import_row_errors`).
2. **Attendance Reports & Analytics**:
   - Course-level, offering-level, student-level, and department-level attendance aggregation.
   - Institutional 75% minimum attendance threshold tracking and at-risk student alerting.
   - Session completion and checkpoint participation rate metrics.
3. **Official Exports**:
   - Downloadable attendance ledgers in CSV, Excel, and structured PDF formats.
4. **Administrative Operations Dashboards**:
   - Enhanced administrative monitoring views for department heads, deans, and university registrars.

---

> [!WARNING]
> Do NOT begin writing code, schemas, or migrations for Milestone 16 in this session. Milestone 15 must first be merged to `main` with all quality gates verified.
