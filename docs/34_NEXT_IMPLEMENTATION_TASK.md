# Digital Student Attendance System
## 34. Next Implementation Task — Milestone 7 Handoff

**Document Version:** 1.0  
**Status:** Ready for Milestone 7 Execution  
**Task ID:** `TASK-005 — Course Catalog, Offerings & Section Enrollment`  
**Milestone:** 7 (Preparation & Scope Boundary)  

---

> [!WARNING]
> **HANDOFF BOUNDARY**: This task specification is prepared as the formal entry point for Milestone 7.
> **DO NOT EXECUTE THIS TASK DURING MILESTONE 6.**
> Implementation begins only upon explicit human approval to initiate Milestone 7.

---

## 1. Task Objective

Implement the master curriculum, course offerings, section assignments, and student enrollment subsystems for the Digital Student Attendance System, establishing:

1. **Course Catalog Models**:
   - `courses` table (`id`, `university_id`, `academic_unit_id`, `code`, `name`, `credits`, `status`, created_at, updated_at).
   - Foreign keys linking courses to active academic units and universities.
2. **Sections & Course Offerings**:
   - `sections` table (`id`, `university_id`, `academic_unit_id`, `semester_id`, `code`, `name`, `status`).
   - `course_offerings` table (`id`, `university_id`, `course_id`, `semester_id`, `section_id`, `status`).
   - `lecturer_assignments` connecting teaching staff to course offerings.
3. **Student Profiles & Enrollments**:
   - `students` profile table (`id`, `user_id`, `university_id`, `student_number`, `academic_unit_id`, `status`).
   - `enrollments` table connecting students to course offerings (`ACTIVE`, `DROPPED`).
4. **Database Migration**:
   - Alembic migration `006_courses_sections_and_enrollments.py` creating the respective tables with constraints and indexes.
5. **REST API Endpoints**:
   - `/api/v1/courses`: Course catalog CRUD operations.
   - `/api/v1/sections`: Section creation and management.
   - `/api/v1/course-offerings`: Offering scheduling and lecturer linking.
   - `/api/v1/enrollments`: Student section and offering enrollment management.
6. **Automated Test Suite**:
   - Comprehensive test coverage for course creation, offering semester linkage, enrollment states, and scoped authorization gates.

---

## 2. Mandatory Reading Before Implementation

The engineer or AI agent implementing Milestone 7 must inspect:
- `docs/01_PRODUCT_REQUIREMENTS_PRD.md` (Sections 4 & 5 — Academic Structure & Students)
- `docs/08_DOMAIN_MODEL.md` (Section 3 — Course Catalog & Enrollment Subdomain)
- `docs/09_DATABASE_SCHEMA.md` (Sections 3 & 4 — Academic Structure, People, Courses)
- `docs/10_API_SPECIFICATION.md` (Course & Enrollment Endpoints)
- `docs/13_AGENT_DEVELOPMENT_RULES.md`
- `docs/15_ARCHITECTURE_DECISIONS.md`
- `docs/23_DATABASE_MIGRATION_PLAN.md`
- `docs/26_DEFINITION_OF_DONE.md`

---

## 3. Allowed Files to Change in Milestone 7

```text
backend/app/models/course.py
backend/app/models/section.py
backend/app/models/course_offering.py
backend/app/models/student.py
backend/app/models/lecturer.py
backend/app/models/enrollment.py
backend/app/courses/
backend/app/enrollments/
backend/migrations/versions/006_courses_sections_and_enrollments.py
backend/tests/test_courses.py
backend/tests/test_enrollments.py
```

**Forbidden Modifications in Milestone 7:**
- Do not implement timetable schedule slots or recurring class meetings (Milestone 8).
- Do not implement attendance sessions, checkpoints, QR code rotation, or Bluetooth BLE scanning (Milestone 8+).
- Do not implement offline attendance reconciliation permits (Milestone 9+).
