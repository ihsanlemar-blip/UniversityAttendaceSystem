# Digital Student Attendance System
## 33. Milestone 6 — Academic Structure, Hierarchy & Master Data

**Document Version:** 1.0  
**Status:** Completed & Validated  
**Milestone:** 6 (Academic Structure, Hierarchy & Master Data)  
**Git Feature Branch:** `feature/task-004-academic-structure`  
**Base Commit:** `28bd37b`  

---

## 1. Executive Summary

Milestone 6 implements the institutional academic hierarchy and academic calendar subsystems for the **Digital Student Attendance System**. In strict compliance with `AGENTS.md` and the specification documents (`docs/01_PRODUCT_REQUIREMENTS_PRD.md` Section 4, `docs/08_DOMAIN_MODEL.md` Section 2, `docs/09_DATABASE_SCHEMA.md` Section 3, and `docs/15_ARCHITECTURE_DECISIONS.md` ADR-017), **zero timetable/scheduling engine logic** (no `CourseOffering`, schedule slots, room assignments, recurring meetings, or `ClassOccurrence`) and **zero attendance engine logic** (no attendance sessions, checkpoints, QR codes, Bluetooth BLE, device trust, or offline attendance) were introduced.

The academic structure and master data platform provides:
1. **Flexible, Self-Referential Academic Unit Hierarchy (ADR-017)**:
   - Self-referencing recursive hierarchy table `academic_units` (`id`, `university_id`, `parent_id`, `unit_type`, `code`, `name`, `short_name`, `status`, `sort_order`, timestamps).
   - Supports arbitrary institutional structures: Faculty alone, Faculty $\rightarrow$ Department, Faculty $\rightarrow$ Program, or Faculty $\rightarrow$ Department $\rightarrow$ Program without forcing unnecessary intermediate tiers.
   - Supported unit types: `FACULTY`, `DEPARTMENT`, `PROGRAM`, `OTHER`.
   - UTF-8 multilingual support for localized academic unit titles in Pashto, Dari, and English.
2. **Server-Side Cycle Detection & Hierarchy Integrity**:
   - Algorithmic ancestor traversal preventing circular references: self-parenting ($A \rightarrow A$), direct 2-node cycles ($A \rightarrow B \rightarrow A$), and deep $N$-node transitive cycles ($A \rightarrow B \rightarrow C \rightarrow A$).
   - Strict institutional tenant boundary enforcement rejecting foreign parent unit links (`INVALID_PARENT_UNIT`).
   - Structural integrity guard on soft deactivation: parent units cannot be deactivated while active child units exist (`ACADEMIC_UNIT_HAS_ACTIVE_CHILDREN`).
   - Unit reactivation validation: units cannot be reactivated if their parent unit is inactive (`PARENT_UNIT_INACTIVE`).
3. **High-Performance Hierarchy Tree Navigation**:
   - Dedicated `/api/v1/academic-units/tree` endpoint generating deeply nested hierarchy trees in memory from a single database query, completely eliminating $N+1$ query overhead.
4. **Academic Calendar Management**:
   - `academic_years`: Annual institutional periods (`name`, `code`, `start_date`, `end_date`, `is_current`, `status`). Check constraint: `start_date < end_date`.
   - `semesters`: Discrete calendar sessions (`name`, `code`, `sequence_order`, `start_date`, `end_date`, `is_current`, `status`) linked to parent `academic_year_id`.
   - Date containment validation: Semester `start_date` and `end_date` must strictly fall within parent academic year date bounds.
   - Active period exclusivity: Atomically maintains at most one `is_current = True` academic year and at most one `is_current = True` semester per university.
5. **Hierarchical Subtree RBAC Scoping**:
   - Unlocked `ScopeType.ACADEMIC_UNIT` in `role_assignments`.
   - Subtree inheritance: Users granted roles scoped to an academic unit (e.g. `FACULTY_ADMIN` scoped to Faculty X) possess authoritative administrative access over Faculty X and all its descendant departments and programs.
   - Sibling isolation & IDOR prevention: Scoped access strictly rejects operations on sibling faculties or unrelated units (HTTP 403 `PERMISSION_DENIED`).
   - Declarative route dependency `require_academic_unit_permission(permission_code)` resolving `unit_id` from route parameters.
6. **Reversible Alembic Migration**:
   - Migration `005_academic_units_and_calendar.py` chained from `004_auth_sessions_attempts.py`.
   - Creates `academic_units`, `academic_years`, and `semesters` with UUIDv7 primary keys, cascade/restrict foreign keys, check constraints, composite unique constraints, and B-tree indexes.
   - Tested for clean, bidirectional `upgrade()` and `downgrade()` idempotence without schema drift.

---

## 2. Invariant Compliance Verification

| Invariant | Description | Milestone 6 Status | Verification Details |
|---|---|---|---|
| **INV-01** | Client Cannot Mark Itself Present | **PRESERVED / NOT YET IMPLEMENTED** | Attendance engine deferred. Academic structure endpoints define organizational hierarchy only. |
| **INV-02** | Attendance Depends on Server/Domain Validation | **PRESERVED / NOT YET IMPLEMENTED** | Master data established. Domain validation will govern future attendance sessions attached to academic calendar semesters. |
| **INV-03** | Student Device Clock Is NOT Authoritative | **ENFORCED** | Academic calendar intervals (`start_date`, `end_date`) and audit timestamps are generated and validated using server UTC authority. |
| **INV-04** | Expired Dynamic QR/Tokens Cannot Grant Attendance | **PRESERVED / NOT YET IMPLEMENTED** | Deferred to Milestone 8+. |
| **INV-05** | No Duplicate Checkpoint Credit | **PRESERVED / NOT YET IMPLEMENTED** | Deferred to Milestone 8+. |
| **INV-06** | Corrections Cannot Erase History | **PRESERVED / NOT YET IMPLEMENTED** | Historical revisions deferred to Attendance Engine and Audit milestones. |
| **INV-07** | Offline Events Remain Identifiable | **PRESERVED / NOT YET IMPLEMENTED** | Offline token reconciliation deferred to Milestone 9+. |
| **INV-08** | Manual Attendance Overrides Remain Identifiable | **PRESERVED / NOT YET IMPLEMENTED** | Manual attendance override workflow deferred to Attendance Engine milestone. |

---

## 3. Implemented Subsystems & Endpoints

### 3.1 Academic Hierarchy Subsystem (`/api/v1/academic-units`)

- `POST /api/v1/academic-units`: Creates academic unit. Enforces code uniqueness within university, validates parent existence and active status.
- `GET /api/v1/academic-units`: Lists units with pagination and filtering by `parent_id`, `root_only`, `unit_type`, and `status`.
- `GET /api/v1/academic-units/tree`: Constructs complete organizational tree or subtree rooted at `root_id` in a single query.
- `GET /api/v1/academic-units/{unit_id}`: Returns unit metadata, immediate parent details, active child count, and complete ancestor breadcrumb path.
- `PATCH /api/v1/academic-units/{unit_id}`: Updates unit attributes (`name`, `code`, `short_name`, `sort_order`). Scoped to unit subtree.
- `POST /api/v1/academic-units/{unit_id}/move`: Reparents unit with recursive cycle detection (self-parenting, direct, or transitive cycles rejected).
- `POST /api/v1/academic-units/{unit_id}/deactivate`: Soft-deactivates unit; rejected if active children exist.
- `POST /api/v1/academic-units/{unit_id}/activate`: Reactivates unit; requires parent unit to be active.

### 3.2 Academic Calendar Subsystem (`/api/v1/academic-years` & `/api/v1/semesters`)

- `POST /api/v1/academic-years`: Creates academic year with date validation (`start_date < end_date`) and optional active designation.
- `GET /api/v1/academic-years`: Lists academic years with pagination and filtering.
- `GET /api/v1/academic-years/current`: Retrieves the designated active academic year.
- `GET /api/v1/academic-years/{year_id}`: Retrieves academic year details with nested list of child semesters.
- `PATCH /api/v1/academic-years/{year_id}`: Updates academic year dates, ensuring dates enclose existing semesters.
- `POST /api/v1/academic-years/{year_id}/set-current`: Atomically sets specified year as current and unsets previous current year.
- `POST /api/v1/semesters`: Creates semester session; enforces date bounds containment within parent academic year.
- `GET /api/v1/semesters`: Lists semesters with pagination and filtering by `academic_year_id`.
- `GET /api/v1/semesters/current`: Retrieves the designated active semester.
- `GET /api/v1/semesters/{semester_id}`: Retrieves semester details.
- `PATCH /api/v1/semesters/{semester_id}`: Updates semester dates and attributes with enclosure validation.
- `POST /api/v1/semesters/{semester_id}/set-current`: Atomically sets specified semester as current and unsets previous current semester.

---

## 4. Test Matrix & Verification Results

```text
Test Suite Summary:
----------------------------------------------------------------------
backend/tests/test_academic_units.py       10 passed
backend/tests/test_academic_calendar.py     3 passed
backend/tests/test_academic_rbac.py         2 passed
Existing Backend Tests (Identity/RBAC/Core) 85 passed
----------------------------------------------------------------------
Total Backend Tests:                       100 passed (100% passing)

Static Analysis & Type Checking:
----------------------------------------------------------------------
Ruff check:                                Passed (0 errors)
Ruff format:                               Passed (89 source files)
Mypy strict:                               Passed (89 source files)
Alembic check (Docker):                    Passed (No schema drift)
Next.js lint:                              Passed
Next.js type-check:                        Passed
Next.js build:                             Passed (Turbopack production build)
Flutter analyze:                           Passed (0 issues)
Flutter tests:                             3 passed
Secret scan (scripts/check_secrets.py):    Passed (0 exposed secrets)
```
