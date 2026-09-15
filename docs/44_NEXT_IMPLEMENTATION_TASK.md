# Next Implementation Task: Milestone 12 — Offline Capability & Device Trust

## 1. Task Objective

Implement **Milestone 12: Offline Capability & Device Trust** for the Digital Student Attendance System. Milestone 12 enables resilient attendance capture in network-degraded classroom environments (e.g. basement lecture halls, connectivity drops) while enforcing device binding and trust constraints to prevent unauthorized multi-device proxy attendance.

---

## 2. Invariants & Guardrails (Mandatory)

* **INV-01 (Client Cannot Mark Itself Present)**: Offline attendance events carry signed offline permits and local evidence signatures. When synced, the server alone validates cryptographic signatures and evaluates attendance credit.
* **INV-03 (Authoritative University Clock)**: Offline permits have strict server-issued expiration windows. Synced offline records must fall within the authorized permit window.
* **INV-07 (Offline Events Remain Identifiable)**: All attendance evidence captured offline must carry explicit metadata (`OFFLINE_CAPTURED`) and `source_mode="OFFLINE_SYNC"`. Server reconciliation must record sync latency and offline audit logs.
* **Device Binding Invariant**: A student account can only have one active bound mobile device at a time. Device change requests require administrative approval or secure cooldown periods.
* **Append-Only Audit Ledger**: Reconciled offline check-ins must create append-only audit records. Corrections cannot overwrite historical evidence.
* **Zero Real-World Sleeps**: Fast testing strategy with zero `time.sleep()` or `asyncio.sleep()`.

---

## 3. High-Level Milestone 12 Scope

1. **Device Trust & Binding**:
   - Device enrollment and cryptographic key pair registration (`POST /api/v1/devices/register`).
   - Hardware-backed key attestation or unique device fingerprint verification.
   - Enforce single active bound device per student profile.
2. **Offline Attendance Permits**:
   - Pre-issued, short-lived cryptographic permits for scheduled class occurrences (`GET /api/v1/attendance/sessions/{session_id}/offline-permit`).
   - Permits signed with dedicated `ATTENDANCE_OFFLINE_SIGNING_KEY`.
3. **Local Queue & Outbox/Inbox Sync**:
   - Mobile SQLite/encrypted storage outbox for offline check-in events.
   - Synchronization protocol (`POST /api/v1/attendance/sync/offline-batch`).
   - Server-side conflict resolution and replay protection via permit nonces.
4. **Testing & Validation**:
   - Unit tests for offline permit signing, verification, and tamper detection.
   - Integration tests against real PostgreSQL 16 verifying outbox sync, replay rejection, and device binding enforcement.
   - RBAC tests verifying student enrollment and device ownership.
