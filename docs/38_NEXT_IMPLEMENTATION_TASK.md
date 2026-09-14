# Digital Student Attendance System
## 38. Next Implementation Task — Milestone 9 Handoff

**Document Version:** 1.1  
**Status:** Ready for Milestone 9 Execution  
**Task ID:** `TASK-007 — Attendance Core Engine`  
**Milestone:** 9 (Preparation & Scope Boundary)  
**Governing Specs:** `docs/01_PRODUCT_REQUIREMENTS_PRD.md`, `docs/04_ATTENDANCE_RULES.md`, `docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md`, `docs/08_DOMAIN_MODEL.md`, `docs/09_DATABASE_SCHEMA.md`

---

> [!WARNING]
> **HANDOFF BOUNDARY**: This task specification is prepared as the formal entry point for Milestone 9.
> **DO NOT EXECUTE THIS TASK DURING MILESTONE 8.**
> Implementation begins only upon explicit human approval to initiate Milestone 9.

---

## 1. Task Objective

Implement the core attendance session lifecycle, 3-checkpoint evaluation model (`START`, `MIDDLE`, `END`), student attendance records, status state transitions, policy calculations, and manual overrides for the **Digital Student Attendance System**, establishing:

### 1.1 Attendance Sessions (`AttendanceSession`)
- **Occurrence Attachment**: Every `AttendanceSession` MUST strictly attach to a concrete calendar meeting (`class_occurrences.id`).
- **Lifecycle State Machine**: `SCHEDULED` -> `ACTIVE` -> `PAUSED` -> `CLOSED` -> `ARCHIVED`.
- **Session Control**: Lecturer-controlled session activation, pause, resumption, and closure.
- **Authoritative Server Time (INV-03)**: Session start, pause, resume, and close times are recorded strictly using university server UTC clock.

### 1.2 Approved 3-Checkpoint Architecture (`AttendanceCheckpoint`)
- **Three Checkpoints per Class**: Exactly three discrete checkpoints:
  1. `START`: Opened near class beginning (default window: ~3–5 minutes, configurable).
  2. `MIDDLE`: Opened near the midpoint of class (default window: ~3–5 minutes, configurable).
  3. `END`: Opened near class conclusion (default window: ~3–5 minutes, configurable).
- **No Alternative Checkpoint Models**: Do NOT use `FIRST_HALF`, `SECOND_HALF`, or `RANDOM_POP`.
- **Configurable Windows**: Checkpoint duration window (~3–5 minutes default) is configurable.
- **Server UTC Anchoring**: Checkpoints record `opened_at_utc` and `closed_at_utc` using authoritative server time.

### 1.3 Attendance Status Taxonomy & Combination Interpretation
- **Approved Attendance Statuses**:
  - `PRESENT`: Full attendance meeting policy thresholds.
  - `LATE`: Student completed initial verification after the late threshold or met partial attendance criteria.
  - `ABSENT`: Student failed to verify minimum required checkpoints.
  - `EXCUSED`: Administratively excused absence with documented justification.
  - `LEAVE`: Approved institutional or medical leave.
  - `PENDING` / `UNVERIFIED`: Internal state while session checkpoints remain active or under conflict review.
- **Combinatorial Checkpoint Evaluation Rules** (configurable per `docs/04_ATTENDANCE_RULES.md`):
  - **Start + Middle + End**: Full attendance (`PRESENT`).
  - **Any 2 of 3**: Partial or full attendance depending on configurable policy.
  - **Start only**: Possible early departure / partial attendance.
  - **Middle only**: Late arrival / partial attendance.
  - **End only**: Very late arrival / normally insufficient attendance.
  - **Zero checkpoints**: Normally evaluated as `ABSENT`.
- **Configurable Attendance Requirement**:
  - Default minimum course attendance percentage: **75%** (configurable).
  - Configurable hierarchy precedence: Course override -> Program override -> Faculty override -> University default.
- **Invariants Enforced**:
  - **INV-01 (Client Cannot Mark Itself Present)**: Mobile and web clients submit verification evidence; the server attendance engine alone determines status.
  - **INV-05 (No Duplicate Checkpoint Credit)**: Exactly one verification credit per student per checkpoint in a session.

### 1.4 Attendance Records & Audit Revision Ledger (`AttendanceRecord`)
- **Student Roster Records**: One record per enrolled student per session (`student_id`, `attendance_session_id`, `status`, `score`, `is_late`, `checkpoints_verified`).
- **Immutable History & Corrections (INV-06)**: When an attendance record is corrected or excused post-session, the historical record is never overwritten or erased; an append-only revision ledger (`attendance_revisions`) preserves the complete audit trail.
- **Manual Overrides (INV-08)**: Manual status changes by lecturers or administrators require recorded justification and immutable actor ID logging.

---

## 2. Technical Deliverables for Milestone 9

1. **Database Migration**:
   - Alembic migration `008_attendance_core_engine.py` creating:
     - `attendance_sessions`
     - `attendance_checkpoints`
     - `attendance_records`
     - `attendance_verifications` (or `checkpoint_records`)
     - `attendance_revisions`
2. **Domain Entities & Services**:
   - `backend/app/attendance/service.py`: Session lifecycle, checkpoint management, combinatorial status calculator, override engine.
   - `backend/app/attendance/schemas.py`: Pydantic contracts for sessions, checkpoints, records, overrides.
   - `backend/app/attendance/router.py`: REST API endpoints.
3. **REST API Endpoints**:
   - `POST /api/v1/attendance/sessions`: Initialize/activate session for a `class_occurrence_id`.
   - `POST /api/v1/attendance/sessions/{id}/pause` / `resume` / `close`: Lifecycle transitions.
   - `POST /api/v1/attendance/sessions/{id}/checkpoints/{checkpoint_type}/open`: Open `START`, `MIDDLE`, or `END` checkpoint.
   - `POST /api/v1/attendance/sessions/{id}/checkpoints/{checkpoint_type}/close`: Close checkpoint window.
   - `GET /api/v1/attendance/sessions/{id}/records`: Session roster attendance sheet.
   - `POST /api/v1/attendance/records/{id}/override`: Manual override with mandatory justification (INV-08).
   - `GET /api/v1/students/me/attendance`: Student personal attendance history self-view.
4. **Automated Test Matrix**:
   - Session lifecycle state transitions.
   - Checkpoint opening/closing and window expiration.
   - Combinatorial status calculation (all 3, 2-of-3, Start-only, Middle-only, End-only, zero checkpoints).
   - No duplicate checkpoint credit (INV-05).
   - Revision ledger immutability on correction (INV-06).
   - Manual override justification and actor logging (INV-08).

---

## 3. Mandatory Reading Before Implementation

The engineer or AI agent implementing Milestone 9 must inspect:
- `docs/00_PROJECT_VISION.md`
- `docs/01_PRODUCT_REQUIREMENTS_PRD.md` (Section 6 — Attendance Engine)
- `docs/04_ATTENDANCE_RULES.md` (Complete Official Specification)
- `docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md`
- `docs/08_DOMAIN_MODEL.md` (Section 5 — Attendance Core Subdomain)
- `docs/09_DATABASE_SCHEMA.md` (Section 6 — Attendance Tables)
- `docs/10_API_SPECIFICATION.md` (Attendance Endpoints)
- `docs/13_AGENT_DEVELOPMENT_RULES.md`
- `docs/15_ARCHITECTURE_DECISIONS.md`
- `docs/23_DATABASE_MIGRATION_PLAN.md`
- `docs/26_DEFINITION_OF_DONE.md`

---

## 4. Strict Prohibitions for Milestone 9

1. **NO Dynamic QR Cryptographic Presence Engine**:
   - Do NOT implement TOTP/HMAC dynamic QR code rotation or client token decoders (strictly Milestone 10).
2. **NO Bluetooth BLE Verification**:
   - Do NOT implement BLE beacon advertising or proximity scanning (strictly Milestone 11).
3. **NO Offline Attendance Sync Engine**:
   - Do NOT implement offline signed token caches or conflict reconciliation (strictly Milestone 12).
4. **NO Manual DB Edits**:
   - All schema modifications must strictly proceed through reversible Alembic migration `008`.
