# Digital Student Attendance System
## 32. Next Implementation Task — Milestone 6 Handoff

**Document Version:** 1.0  
**Status:** Ready for Milestone 6 Execution  
**Task ID:** `TASK-004 — Academic Hierarchy & Calendar Management`  
**Milestone:** 6 (Preparation & Scope Boundary)  

---

> [!WARNING]
> **HANDOFF BOUNDARY**: This task specification is prepared as the formal entry point for Milestone 6.
> **DO NOT EXECUTE THIS TASK DURING MILESTONE 5.**
> Implementation begins only upon explicit human approval to initiate Milestone 6.

---

## 1. Task Objective

Implement the institutional academic hierarchy and academic calendar subsystems for the Digital Student Attendance System, establishing:

1. **Academic Unit Data Models (ADR-017)**:
   - Self-referencing recursive hierarchy table `academic_units` (id, university_id, parent_id, unit_type: `FACULTY`, `DEPARTMENT`, code, name, status, created_at, updated_at).
   - Foreign key constraint ensuring units belong to an active `university_id`.
   - Tree navigation methods (faculties contain departments).
2. **Academic Calendar Data Models**:
   - `academic_years` (id, university_id, name, start_date, end_date, is_current, status).
   - `semesters` (id, academic_year_id, name, sequence_number, start_date, end_date, is_current, status).
   - Validation ensuring non-overlapping current periods per university.
3. **RBAC Integration**:
   - Guarding academic unit creation and updates with `academic_units:manage` or `academic:manage` permissions.
   - Enabling role scoping to specific `FACULTY` or `DEPARTMENT` scope types in `role_assignments`.
4. **Database Migration**:
   - Alembic migration `005_academic_units_and_calendar.py` creating `academic_units`, `academic_years`, and `semesters`.
5. **REST API Endpoints**:
   - `/api/v1/academic-units`: CRUD operations with hierarchical parent/child listings.
   - `/api/v1/academic-years` & `/api/v1/semesters`: Calendar management with active period activation.
6. **Automated Test Suite**:
   - Comprehensive test coverage for recursive unit trees, date validations, calendar activations, and RBAC authorization gates.

---

## 2. Mandatory Reading Before Implementation

The engineer or AI agent implementing Milestone 6 must inspect:
- `docs/01_PRODUCT_REQUIREMENTS_PRD.md` (Section 3 — Institutional Hierarchy)
- `docs/08_DOMAIN_MODEL.md` (Section 2 — Academic Hierarchy Subdomain)
- `docs/09_DATABASE_SCHEMA.md` (Section 3 — Academic Hierarchy & Calendar Tables)
- `docs/10_API_SPECIFICATION.md` (Academic Unit & Calendar Endpoints)
- `docs/13_AGENT_DEVELOPMENT_RULES.md`
- `docs/15_ARCHITECTURE_DECISIONS.md` (ADR-017: Self-Referential Academic Units)
- `docs/23_DATABASE_MIGRATION_PLAN.md`
- `docs/26_DEFINITION_OF_DONE.md`

---

## 3. Allowed Files to Change in Milestone 6

```text
backend/app/models/academic_unit.py
backend/app/models/academic_calendar.py
backend/app/academic/
backend/app/calendar/
backend/migrations/versions/005_academic_units_and_calendar.py
backend/tests/test_academic_units.py
backend/tests/test_academic_calendar.py
```

**Forbidden Modifications in Milestone 6:**
- Do not implement student enrollment or lecturer teaching assignments (Milestone 7).
- Do not implement course catalogs, offerings, or syllabi (Milestone 7).
- Do not implement attendance sessions, QR codes, or Bluetooth scanning (Milestone 8+).
