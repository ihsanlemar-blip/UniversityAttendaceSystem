# Digital Student Attendance System
## 36. Next Implementation Task — Milestone 8 Handoff

**Document Version:** 1.0  
**Status:** Ready for Milestone 8 Execution  
**Task ID:** `TASK-006 — Facilities, Timetable & Class Occurrences`  
**Milestone:** 8 (Preparation & Scope Boundary)  

---

> [!WARNING]
> **HANDOFF BOUNDARY**: This task specification is prepared as the formal entry point for Milestone 8.
> **DO NOT EXECUTE THIS TASK DURING MILESTONE 7.**
> Implementation begins only upon explicit human approval to initiate Milestone 8.

---

## 1. Task Objective

Implement the physical facilities master data, recurring timetable schedule rules, and concrete class occurrences generation engine for the Digital Student Attendance System, establishing:

1. **Facilities & Physical Spaces**:
   - `buildings`: Campus buildings (`id`, `university_id`, `name`, `code`, `status`, timestamps).
   - `rooms`: Classroom, lecture hall, and lab spaces (`id`, `university_id`, `building_id`, `room_number`, `capacity`, `network_subnet`, `status`, timestamps).
2. **Recurring Timetable Schedules (`Timetable`)**:
   - `timetables`: Recurring weekly schedule rules per ADR-016 (`id`, `university_id`, `course_offering_id`, `room_id`, `day_of_week`, `start_time`, `end_time`, `status`, timestamps).
   - Room and lecturer schedule conflict detection: prevent overlapping bookings for the same room or same instructor on identical days and time windows.
3. **Concrete Class Occurrences Engine (`ClassOccurrence`)**:
   - `class_occurrences`: Concrete calendar instances generated from timetables per ADR-016 (`id`, `university_id`, `timetable_id`, `course_offering_id`, `room_id`, `substitute_lecturer_id`, `scheduled_start_utc`, `scheduled_end_utc`, `status` [`SCHEDULED`, `COMPLETED`, `CANCELLED`]).
   - Occurrence generator service projecting recurring timetable rules over the academic semester calendar date range.
4. **Database Migration**:
   - Alembic migration `007_facilities_and_timetable.py` creating `buildings`, `rooms`, `timetables`, and `class_occurrences` with constraints, foreign keys, and indexes.
5. **REST API Endpoints**:
   - `/api/v1/buildings`: Campus building CRUD.
   - `/api/v1/rooms`: Room catalog and capacity management.
   - `/api/v1/timetables`: Weekly recurring schedule rules and conflict validation.
   - `/api/v1/class-occurrences`: Concrete calendar occurrences query, reschedule, and cancellation.
6. **Automated Test Suite**:
   - Conflict engine test coverage (double-booking prevention for rooms and instructors).
   - Semester occurrence expansion verification.
   - Tenant and academic unit subtree authorization testing.

---

## 2. Mandatory Reading Before Implementation

The engineer or AI agent implementing Milestone 8 must inspect:
- `docs/01_PRODUCT_REQUIREMENTS_PRD.md` (Section 5 — Facilities & Scheduling)
- `docs/08_DOMAIN_MODEL.md` (Section 4 — Facilities & Timetable Subdomain)
- `docs/09_DATABASE_SCHEMA.md` (Section 5 — Facilities & Scheduling)
- `docs/10_API_SPECIFICATION.md` (Facilities & Occurrence Endpoints)
- `docs/15_ARCHITECTURE_DECISIONS.md` (ADR-016: Timetable Patterns vs Concrete Class Occurrences)
- `docs/13_AGENT_DEVELOPMENT_RULES.md`
- `docs/23_DATABASE_MIGRATION_PLAN.md`
- `docs/26_DEFINITION_OF_DONE.md`

---

## 3. Strict Prohibitions for Milestone 8

1. **NO Attendance Engine Logic**:
   - Do NOT implement attendance records, sessions, check-in tokens, or validation rules (Milestone 9).
2. **NO Dynamic QR or BLE**:
   - Do NOT implement dynamic QR code generation or BLE presence scanning (Milestones 10 and 11).
3. **NO Offline Reconciliation**:
   - Do NOT implement offline token storage or sync endpoints (Milestone 12).
4. **NO Manual DB Edits**:
   - All schema evolution must strictly proceed through Alembic migration `007`.
