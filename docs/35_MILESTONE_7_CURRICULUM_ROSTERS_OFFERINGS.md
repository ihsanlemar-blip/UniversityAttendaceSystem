# Digital Student Attendance System
## 35. Milestone 7 — Master Curriculum, People Profiles, Rosters & Course Offerings

**Document Version:** 1.0  
**Status:** Completed & Validated  
**Milestone:** 7 (Master Curriculum, People Profiles, Rosters & Course Offerings)  
**Git Feature Branch:** `feature/task-005-curriculum-rosters-offerings`  
**Base Commit:** `9390234`  

---

## 1. Executive Summary

Milestone 7 implements the academic curriculum catalog, student cohort sections, individual people profiles (students and lecturers), semester course offerings, multi-instructor teaching assignments, and student course enrollments for the **Digital Student Attendance System**. In strict compliance with `AGENTS.md` and the specification documents (`docs/01_PRODUCT_REQUIREMENTS_PRD.md`, `docs/04_ATTENDANCE_RULES.md`, `docs/08_DOMAIN_MODEL.md`, `docs/09_DATABASE_SCHEMA.md`, and `docs/15_ARCHITECTURE_DECISIONS.md`), **zero timetable/facilities logic** (no `rooms`, `buildings`, recurring timetable patterns, or schedule conflict resolution per ADR-016), **zero class occurrences** (no calendar meeting occurrences per ADR-016), and **zero attendance engine logic** (no attendance sessions, checkpoints, dynamic QR tokens, BLE scanning, device trust, or offline attendance) were introduced.

The curriculum, rosters, and offerings platform provides:
1. **Master Course Catalog (`Course`)**:
   - `courses`: Institutional curriculum catalog (`id`, `university_id`, `academic_unit_id`, `code`, `name`, `credit_hours`, `description`, `status`, timestamps).
   - Case-insensitive uniqueness constraint: `UNIQUE (university_id, LOWER(code))`.
   - Optional academic unit placement validating that target department/faculty belongs to the current university.
2. **Student Cohort Sections (`Section`)**:
   - `sections`: Student cohort grouping (`id`, `university_id`, `academic_unit_id`, `semester_id`, `code`, `name`, `status`, timestamps).
   - Uniqueness constraint: `UNIQUE (university_id, semester_id, code)`.
   - Allows section code reuse across different semesters while preventing collisions within the same academic semester session.
3. **Student Profiles (`Student`)**:
   - `students`: Academic learner profile (`id`, `user_id`, `university_id`, `student_number`, `academic_unit_id`, `section_id`, `admission_date`, `status`, timestamps).
   - 1:1 user account linkage: `UNIQUE (user_id)` with `ON DELETE RESTRICT` foreign key, preventing destructive cascade deletion of user accounts referenced by offerings, timetables, and future attendance history.
   - Institutional matriculation uniqueness: `UNIQUE (university_id, student_number)`.
   - Personal profile access endpoint `/api/v1/students/me`.
4. **Lecturer Profiles (`Lecturer`)**:
   - `lecturers`: Academic instructor profile (`id`, `user_id`, `university_id`, `employee_code`, `academic_unit_id`, `title`, `status`, timestamps).
   - 1:1 user account linkage: `UNIQUE (user_id)` with `ON DELETE RESTRICT` foreign key, preventing destructive cascade deletion of user accounts referenced by offerings, timetables, and future attendance history.
   - Institutional employee code uniqueness: `UNIQUE (university_id, employee_code)`.
   - Personal profile access endpoint `/api/v1/lecturers/me`.
5. **Course Offerings (`CourseOffering`)**:
   - `course_offerings`: Semester delivery instance coupling Course + Semester + optional Section (`id`, `university_id`, `course_id`, `semester_id`, `section_id`, `academic_unit_id`, `status`, timestamps).
   - Engine-level uniqueness guaranteed via dual partial unique indexes:
     - `uq_course_offerings_with_section` on `(university_id, course_id, semester_id, section_id) WHERE section_id IS NOT NULL`
     - `uq_course_offerings_without_section` on `(university_id, course_id, semester_id) WHERE section_id IS NULL`
6. **Co-Teaching Lecturer Assignments (`LecturerAssignment`)**:
   - `lecturer_assignments`: Instructor assignment to offerings (`id`, `course_offering_id`, `lecturer_id`, `is_primary`, `assignment_type`, `status`, timestamps).
   - Single primary instructor guarantee: Database-enforced partial unique index `uq_lecturer_assignments_single_primary` on `(course_offering_id) WHERE (is_primary = true AND status = 'ACTIVE')`.
   - Supports co-teaching, lab instructors, and teaching assistants (`CO_TEACHER`, `ASSISTANT`).
   - Personal offerings query `/api/v1/lecturers/me/offerings`.
7. **Student Enrollments & Rosters (`Enrollment`)**:
   - `enrollments`: Student enrollment in course offerings (`id`, `university_id`, `course_offering_id`, `student_id`, `status`, `enrolled_at`, `dropped_at`, timestamps).
   - Canonical single-row enrollment guarantee: Composite unique constraint `uq_enrollments_offering_student` on `(course_offering_id, student_id)`.
   - Audit and history preservation (Invariant 6): Dropping an enrollment sets `status = 'DROPPED'` and records `dropped_at = utc_now()`, preserving historical presence and audit history without erasing data.
   - Idempotent reactivation: Re-enrollment updates the existing canonical row to `status = 'ACTIVE'`, clears `dropped_at = NULL`, and updates `enrolled_at`, preventing row duplication and keeping roster/ClassOccurrence logic strictly unambiguous.
   - Personal enrollments query `/api/v1/students/me/enrollments`.
8. **RBAC Seeding & Subtree-Aware Access Scoping**:
   - Added 12 canonical permissions: `courses.view`, `courses.manage`, `sections.view`, `sections.manage`, `students.view`, `students.manage`, `lecturers.view`, `lecturers.manage`, `course_offerings.view`, `course_offerings.manage`, `enrollments.view`, `enrollments.manage`.
   - Seeded into canonical roles (`SUPER_ADMIN`, `UNIVERSITY_ADMIN`, `FACULTY_ADMIN`, `DEPARTMENT_ADMIN`, `ATTENDANCE_OFFICER`, `LECTURER`, `STUDENT`, `AUDITOR`).
   - `require_permission(..., allow_scoped=True)` enables fine-grained academic subtree authorization: Faculty Admins are authorized within their faculty subtree, and strictly rejected (HTTP 403 `PERMISSION_DENIED`) on sibling faculties or unrelated units.
9. **Reversible Alembic Migration 006**:
   - Created `backend/migrations/versions/006_curriculum_and_rosters.py` chained from `005_academic_units_and_calendar.py`.
   - Full roundtrip `upgrade head` -> `downgrade -1` -> `upgrade head` verified.
   - Zero Alembic drift confirmed via `alembic check`.

---

## 2. Invariant Compliance Verification

| Invariant | Description | Milestone 7 Status | Verification Details |
|---|---|---|---|
| **INV-01** | Client Cannot Mark Itself Present | **PRESERVED** | Attendance engine deferred. Roster and offering endpoints manage enrollments and curriculum definitions only. |
| **INV-02** | Attendance Depends on Server/Domain Validation | **PRESERVED** | Course offerings and enrollments established. Domain validation will evaluate presence against registered offering rosters in Milestone 9+. |
| **INV-03** | Student Device Clock Is NOT Authoritative | **ENFORCED** | Enrollment timestamps (`enrolled_at`, `dropped_at`) and audit logs generated using server UTC authority. |
| **INV-04** | Expired Dynamic QR/Tokens Cannot Grant Attendance | **PRESERVED** | Deferred to Milestone 10+. |
| **INV-05** | No Duplicate Checkpoint Credit | **PRESERVED** | Deferred to Milestone 9+. |
| **INV-06** | Corrections Cannot Erase History | **ENFORCED** | Dropped enrollments retain records with `status = DROPPED` and `dropped_at` timestamp. Historical records are immutable. |
| **INV-07** | Offline Events Remain Identifiable | **PRESERVED** | Deferred to Milestone 12+. |
| **INV-08** | Manual Attendance Overrides Remain Identifiable | **PRESERVED** | Deferred to Milestone 9+. |

---

## 3. Verification Summary

```text
Backend Test Suite:        121 passed (100%)
Ruff Linter:               All checks passed (0 errors)
Ruff Formatter:            114 files inspected, all formatted
MyPy Strict Typechecker:   Success: no issues found in 81 source files
Web Client Type-Check:     Passed (0 errors)
Web Client Linter:         Passed (0 errors)
Web Client Build:          Next.js 16.3.3 Turbopack build succeeded
Mobile Client Analyze:     No issues found (0 warnings, 0 errors)
Mobile Client Tests:       3 passed (100%)
Alembic Schema Drift:      No new upgrade operations detected (Zero drift)
Docker Compose Services:   5/5 running and healthy
```
