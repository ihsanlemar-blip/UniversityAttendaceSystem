# Digital Student Attendance System
## 37. Milestone 8 — Facilities, Timetable & Class Occurrences

**Document Version:** 1.0  
**Status:** Completed & Validated  
**Milestone:** 8 (Facilities, Timetable & Class Occurrences)  
**Git Feature Branch:** `feature/task-006-facilities-timetable-occurrences`  
**Base Commit:** Main branch after Milestone 7.1 merge  

---

## 1. Executive Summary

Milestone 8 establishes the scheduling and concrete meeting foundation of the **Digital Student Attendance System**. In accordance with the system vision, ADR-016, and the project architectural directives:
- Timetables model abstract, recurring weekly schedule patterns.
- Class occurrences represent concrete calendar meetings generated deterministically from timetables or scheduled manually.
- The university's official timezone (`ZoneInfo(university.timezone)`) governs calendar math, while authoritative database timestamps are stored in UTC.
- In strict adherence to `AGENTS.md` and Milestone 8 boundaries, **zero attendance engine logic** (no `attendance_sessions`, checkpoints, dynamic QR tokens, BLE scanning, device trust, or offline sync) was introduced.

---

## 2. Core Capabilities Implemented

### 2.1 Master Facilities Data (`Building` & `Room`)
- **Building**: Represents campus physical structures (`id`, `university_id`, `code`, `name`, `status`, `created_at`, `updated_at`).
  - Institutional uniqueness: `UNIQUE(university_id, LOWER(code))`.
  - Soft deactivation preserving historical rooms and scheduled occurrences.
- **Room**: Represents individual classrooms, laboratories, and lecture halls (`id`, `university_id`, `building_id`, `room_number`, `name`, `capacity`, `room_type`, `floor`, `status`, `created_at`, `updated_at`).
  - Strict data integrity: `capacity > 0`, `building_id` foreign key with `ON DELETE RESTRICT`.
  - Building uniqueness: `UNIQUE(building_id, LOWER(room_number))`.
  - Tenant isolation: Room creation validates that the parent building belongs to the same university.

### 2.2 Recurring Timetable Rules (`Timetable`)
- Represents recurring weekly schedule slots:
  - Fields: `id`, `university_id`, `course_offering_id`, `room_id`, `lecturer_id`, `weekday`, `start_time`, `end_time`, `effective_from`, `effective_to`, `status`.
  - Invariants: `weekday BETWEEN 1 AND 7` (1=Monday ... 7=Sunday), `start_time < end_time`, `effective_from <= effective_to`.
  - Foreign key constraints: `course_offering_id`, `room_id`, `lecturer_id` enforce `ON DELETE RESTRICT`.
  - Boundaries: Restricts effective date ranges within the parent `Semester`'s `start_date` and `end_date`.

### 2.3 Multidimensional Conflict Detection Engine
Before inserting or updating any timetable rule, `SchedulingService._validate_timetable_conflicts()` validates:
1. **Room Conflict (`ROOM_SCHEDULE_CONFLICT`)**: A room cannot be double-booked for another active timetable rule or occurrence at overlapping weekly time intervals within overlapping effective dates.
2. **Lecturer Conflict (`LECTURER_SCHEDULE_CONFLICT`)**: An instructor cannot be assigned to teach two classes simultaneously.
3. **Section Cohort Conflict (`SECTION_SCHEDULE_CONFLICT`)**: A cohort section cannot have overlapping classes across different courses.
4. **Offering Self-Conflict (`DUPLICATE_TIMETABLE_RULE`)**: The same course offering cannot define duplicate overlapping timetable slots.
- **Adjacent Slots Supported**: Contiguous classes (e.g. 08:00–09:30 and 09:30–11:00) share boundaries without conflict (`start < other_end AND end > other_start`).

### 2.4 Concrete Class Occurrence Generator (`ClassOccurrence`)
- Concrete calendar meetings expanded deterministically per ADR-016:
  - Fields: `id`, `university_id`, `course_offering_id`, `timetable_id`, `room_id`, `lecturer_id`, `substitute_lecturer_id`, `local_date`, `scheduled_start_utc`, `scheduled_end_utc`, `status`, `cancellation_reason`, `rescheduled_from_id`, `rescheduled_to_id`.
  - Institutional timezone conversion: Uses `zoneinfo.ZoneInfo(university.timezone)` to convert local dates and times into authoritative UTC timestamps.
  - Idempotent generation: Database-enforced partial unique index `uq_class_occurrences_timetable_start` on `(timetable_id, scheduled_start_utc) WHERE timetable_id IS NOT NULL`. Rerunning generation creates only missing occurrences without duplicating existing ones.
  - Bulk generation endpoint `/api/v1/semesters/{id}/generate-class-occurrences` expands all active timetable rules across an entire semester.

### 2.5 Cancellation & Rescheduling Workflows
- **Cancellation (`/api/v1/class-occurrences/{id}/cancel`)**:
  - Invariant 6 compliance: Preserves the historical row in the database, transitions status to `CANCELLED`, records the mandatory justification string `cancellation_reason`, and preserves audit history.
- **Rescheduling (`/api/v1/class-occurrences/{id}/reschedule`)**:
  - Validates room, lecturer, and section conflicts for the target new date/time slot.
  - Transitions original occurrence to `RESCHEDULED`.
  - Creates the replacement occurrence in `SCHEDULED` status.
  - Bi-directionally links `rescheduled_to_id` and `rescheduled_from_id` for an unbroken audit chain.

### 2.6 Personal Schedule Self-Views
- **Lecturer Schedule (`/api/v1/lecturers/me/class-occurrences`)**:
  - Resolves authenticated lecturer profile and returns occurrences where the instructor is assigned as primary instructor, co-teacher, or substitute.
- **Student Schedule (`/api/v1/students/me/class-occurrences`)**:
  - Resolves authenticated student profile and returns occurrences for course offerings in which the student holds an active enrollment.

### 2.7 Scoped RBAC Subtree Scoping
- Integrated with `require_permission(..., allow_scoped=True)`:
  - `SUPER_ADMIN` and `UNIVERSITY_ADMIN` have unrestricted university-wide scheduling access.
  - `FACULTY_ADMIN` and `DEPARTMENT_ADMIN` are restricted to their academic unit subtree. Attempting to manage timetables or occurrences outside their unit hierarchy results in HTTP 403 `PERMISSION_DENIED`.
  - Sibling faculties are strictly isolated from each other.

---

## 3. Database Migration 007

Alembic migration `backend/migrations/versions/007_timetable_and_class_occurrences.py` adds:
- Tables: `buildings`, `rooms`, `timetables`, `class_occurrences`.
- Foreign keys with `ON DELETE RESTRICT` on master entities, and `ON DELETE SET NULL` on `timetable_id` and rescheduling links.
- Check constraints on capacities, weekdays, and time intervals.
- Compound and foreign-key indexes for fast conflict detection and calendar queries.
- Verified 100% reversible via roundtrip downgrade and upgrade.
- Verified zero schema drift (`alembic check`).

---

## 4. Invariant Compliance Matrix

| Invariant | Description | Milestone 8 Status | Verification Details |
|---|---|---|---|
| **INV-01** | Client Cannot Mark Itself Present | **PRESERVED** | Attendance sessions and marks deferred to Milestone 9+. |
| **INV-02** | Attendance Depends on Server/Domain Validation | **PRESERVED** | Class occurrences establish the authoritative schedule anchor for Milestone 9 sessions. |
| **INV-03** | Student Device Clock Is NOT Authoritative | **ENFORCED** | Local institutional timezone converted to server UTC timestamps (`scheduled_start_utc`, `scheduled_end_utc`). |
| **INV-04** | Expired Dynamic QR/Tokens Cannot Grant Attendance | **PRESERVED** | Deferred to Milestone 10+. |
| **INV-05** | No Duplicate Checkpoint Credit | **PRESERVED** | Deferred to Milestone 9+. |
| **INV-06** | Corrections Cannot Erase History | **ENFORCED** | Occurrence cancellation preserves rows with `cancellation_reason`; rescheduling bi-directionally links old and new occurrences. |
| **INV-07** | Offline Events Remain Identifiable | **PRESERVED** | Deferred to Milestone 12+. |
| **INV-08** | Manual Attendance Overrides Remain Identifiable | **PRESERVED** | Deferred to Milestone 9+. |
