# Digital Student Attendance System
## 38. Next Implementation Task — Milestone 9 Handoff

**Document Version:** 1.0  
**Status:** Ready for Milestone 9 Execution  
**Task ID:** `TASK-007 — Attendance Core Engine`  
**Milestone:** 9 (Preparation & Scope Boundary)  

---

> [!WARNING]
> **HANDOFF BOUNDARY**: This task specification is prepared as the formal entry point for Milestone 9.
> **DO NOT EXECUTE THIS TASK DURING MILESTONE 8.**
> Implementation begins only upon explicit human approval to initiate Milestone 9.

---

## 1. Task Objective

Implement the core attendance session lifecycle, checkpoint evaluation model, student attendance records, status state transitions, and manual overrides for the **Digital Student Attendance System**, establishing:

1. **Attendance Sessions (`AttendanceSession`)**:
   - Anchored strictly to concrete calendar meetings (`class_occurrences.id`).
   - Lifecycle state machine: `SCHEDULED` -> `ACTIVE` -> `PAUSED` -> `CLOSED` -> `ARCHIVED`.
   - Lecturer-controlled session activation, pause, and closure.
2. **Attendance Checkpoints (`AttendanceCheckpoint`)**:
   - Multi-checkpoint evaluation per session (`START`, `MIDDLE`, `END`).
   - Checkpoint activation windows, opening/closing timestamps in server UTC.
   - Evaluation rules computing overall session attendance status (`PRESENT`, `LATE`, `ABSENT`, `EXCUSED`).
3. **Attendance Records (`AttendanceRecord`)**:
   - Learner presence records per student enrollment: `student_id`, `attendance_session_id`, `status`, `score`, `is_late`, `checkpoints_verified`.
   - Append-only audit history revision model per Invariant 6 (`attendance_revisions` or immutable revision chains).
   - Invariant 5: Strict database and service-level prevention of duplicate checkpoint credits.
4. **Manual Attendance Overrides**:
   - Invariant 8: Lecturer or administrator manual status adjustment requiring recorded justification and actor ID logging.
5. **Database Migration**:
   - Alembic migration `008_attendance_core_engine.py` creating session, checkpoint, and record tables with constraints, foreign keys, and indexes.
6. **REST API Endpoints**:
   - `/api/v1/attendance/sessions`: Session lifecycle management.
   - `/api/v1/attendance/sessions/{id}/checkpoints`: Checkpoint configuration and status.
   - `/api/v1/attendance/sessions/{id}/records`: Session roster attendance sheet.
   - `/api/v1/attendance/records/{id}/override`: Manual override with mandatory justification.
   - `/api/v1/students/me/attendance`: Student personal attendance record self-view.
7. **Automated Test Suite**:
   - Lifecycle state transition verification.
   - Checkpoint threshold calculations (`PRESENT`, `LATE`, `ABSENT`).
   - Manual override audit trail verification.
   - Invariant enforcement (INV-01, INV-02, INV-03, INV-05, INV-06, INV-08).

---

## 2. Mandatory Reading Before Implementation

The engineer or AI agent implementing Milestone 9 must inspect:
- `docs/00_PROJECT_VISION.md`
- `docs/01_PRODUCT_REQUIREMENTS_PRD.md` (Section 6 — Attendance Engine)
- `docs/04_ATTENDANCE_RULES.md` (Complete Specification)
- `docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md`
- `docs/08_DOMAIN_MODEL.md` (Section 5 — Attendance Core Subdomain)
- `docs/09_DATABASE_SCHEMA.md` (Section 6 — Attendance Tables)
- `docs/10_API_SPECIFICATION.md` (Attendance Endpoints)
- `docs/13_AGENT_DEVELOPMENT_RULES.md`
- `docs/15_ARCHITECTURE_DECISIONS.md`
- `docs/23_DATABASE_MIGRATION_PLAN.md`
- `docs/26_DEFINITION_OF_DONE.md`

---

## 3. Strict Prohibitions for Milestone 9

1. **NO Dynamic QR Cryptographic Presence Engine**:
   - Do NOT implement TOTP/HMAC dynamic QR code rotation or client token decoders (Milestone 10).
2. **NO Bluetooth BLE Verification**:
   - Do NOT implement BLE beacon advertising or proximity scanning (Milestone 11).
3. **NO Offline Attendance Sync Engine**:
   - Do NOT implement offline signed token caches or conflict reconciliation (Milestone 12).
4. **NO Manual DB Edits**:
   - All schema modifications must strictly proceed through Alembic migration `008`.
