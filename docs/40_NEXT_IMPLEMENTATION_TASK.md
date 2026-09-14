# Digital Student Attendance System
## 40. Next Implementation Task — Milestone 10 Handoff

**Document Version:** 1.0  
**Status:** Ready for Milestone 10 Execution  
**Task ID:** `TASK-008 — Dynamic QR & Cryptographic Presence Tokens`  
**Milestone:** 10 (Dynamic QR & Cryptographic Presence Tokens)  
**Governing Specs:** `docs/01_PRODUCT_REQUIREMENTS_PRD.md`, `docs/04_ATTENDANCE_RULES.md`, `docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md`, `docs/07_SYSTEM_ARCHITECTURE.md`, `docs/08_DOMAIN_MODEL.md`, `docs/09_DATABASE_SCHEMA.md`, `docs/10_API_SPECIFICATION.md`, `docs/15_ARCHITECTURE_DECISIONS.md`

---

> [!WARNING]
> **HANDOFF BOUNDARY**: This task specification is prepared as the formal entry point for Milestone 10.
> **DO NOT EXECUTE THIS TASK DURING MILESTONE 9.**
> Implementation begins only upon explicit human approval to initiate Milestone 10.

---

## 1. Task Objective

Implement the dynamic QR code generation, cryptographic token rotation, mobile scanning ingestion, server-side HMAC token validation, device trust/binding validation, and anti-cheating presence controls for the **Digital Student Attendance System**, establishing:

### 1.1 Dynamic Checkpoint QR Generation (`PresenceTokenEngine`)
- **Discrete Checkpoint Association**:
  - Tokens are generated exclusively within an active `AttendanceCheckpoint` (`START`, `MIDDLE`, or `END`).
  - No continuous or unstructured QR broadcasting; token rotation operates strictly during the active window of the respective checkpoint.
- **HMAC-SHA256 Token Structure**:
  - Payload encodes: `session_id`, `checkpoint_id`, `checkpoint_type`, `step_index`, `university_id`, and cryptographic signature.
  - Server secret key (`PRESENCE_HMAC_SECRET`) signs tokens deterministically.
- **Rotation Window**:
  - Checkpoint tokens rotate every 20–30 seconds (configurable, default: 20 seconds).
  - Tolerance window: Exactly ±1 time step allowed to absorb network latency and device rendering jitter.
- **Authoritative Server UTC Clock (INV-03 & INV-04)**:
  - Step indices and validation windows are derived strictly from server UTC time.
  - Expired tokens (> 1 step window) are unconditionally rejected with HTTP 400/422 `TOKEN_EXPIRED`.

### 1.2 Mobile Scan Ingestion & Evidence Processing (`EvidenceSubmission`)
- **Evidence Verification Pipeline**:
  - Student scans rotating QR code on classroom display using the Flutter mobile client.
  - Client submits payload: `session_id`, `checkpoint_id`, `token`, `client_timestamp`, `device_id`, `device_signature`.
- **Client Cannot Mark Itself Present (INV-01)**:
  - Client submits token evidence; the server verifies signature, step validity, student enrollment, and session state before granting checkpoint credit.
- **No Duplicate Checkpoint Credit (INV-05)**:
  - Validated check-ins invoke the attendance engine idempotently, rejecting second attempts for the same checkpoint in the same session (`CHECKPOINT_ALREADY_VERIFIED`).

### 1.3 Device Trust & Anti-Cheating Controls
- **Single Device Binding**:
  - Verify device binding against registered student hardware (`student_devices.device_id`).
  - Flag or reject submissions from unregistered or multi-account devices (proxy attendance prevention).
- **Rate Limiting & Replay Protection**:
  - Single-use token validation or nonce checking to prevent replay of captured QR frames across devices.

---

## 2. Technical Deliverables for Milestone 10

1. **Cryptographic Core & Token Services**:
   - `backend/app/attendance/tokens.py`: HMAC-SHA256 dynamic token generator, step calculator, and validator with ±1 step tolerance.
   - `backend/app/attendance/device_trust.py`: Student device binding and hardware verification logic.
2. **Dynamic QR Display Endpoints (Lecturer Classroom Screen)**:
   - `GET /api/v1/attendance/sessions/{id}/checkpoints/{type}/token`: Retrieve currently active rotating token payload and refresh interval.
   - WebSocket or SSE stream (optional/secondary) for real-time token broadcasting in classroom.
3. **Student Scan & Check-in API**:
   - `POST /api/v1/attendance/check-in`: Submit scanned QR token, device telemetry, and record attendance evidence.
4. **Automated Test Matrix**:
   - Dynamic token generation and verification within current time step.
   - Token acceptance within ±1 step tolerance window.
   - Token rejection outside tolerance window (INV-04).
   - Duplicate scan rejection within same checkpoint (INV-05).
   - Tampered payload signature verification failure.
   - Device mismatch / untrusted device rejection.

---

## 3. Mandatory Reading Before Implementation

The engineer or AI agent implementing Milestone 10 must inspect:
- `docs/00_PROJECT_VISION.md`
- `docs/01_PRODUCT_REQUIREMENTS_PRD.md` (Section 7 — Dynamic QR & Presence Verification)
- `docs/04_ATTENDANCE_RULES.md`
- `docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md` (Section 3 — Dynamic QR Cryptographic Scheme)
- `docs/07_SYSTEM_ARCHITECTURE.md`
- `docs/08_DOMAIN_MODEL.md`
- `docs/09_DATABASE_SCHEMA.md`
- `docs/10_API_SPECIFICATION.md`
- `docs/13_AGENT_DEVELOPMENT_RULES.md`
- `docs/15_ARCHITECTURE_DECISIONS.md` (ADR-003: Dynamic QR Code with Cryptographic Salt)
- `docs/39_MILESTONE_9_ATTENDANCE_CORE.md`

---

## 4. Strict Prohibitions for Milestone 10

1. **NO BLE Verification**:
   - Do NOT implement Bluetooth Low Energy advertising or beacon ranging (strictly Milestone 11).
2. **NO Offline Queue / Sync**:
   - Do NOT implement offline signed token queueing or sync protocols (strictly Milestone 12).
3. **NO Modification of Approved 3-Checkpoint Architecture**:
   - Do NOT alter `START`, `MIDDLE`, `END` sequence or replace with popups.
4. **NO Client Clock Authority**:
   - Do NOT allow client-submitted timestamps to dictate token validity. Server UTC clock remains the sole authority.
