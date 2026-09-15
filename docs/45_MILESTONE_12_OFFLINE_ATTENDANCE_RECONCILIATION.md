# Milestone 12: Offline Attendance, Signed Offline Authority & Reconciliation

**Version:** 1.0  
**Approved Scope:** Emergency fallback attendance engine, asymmetric cryptographic permits (Ed25519), ephemeral lecturer host keys, monotonic clock anchoring, tamper-evident host event hash chains, rotating dynamic offline QR/BLE challenges, local outbox persistence, idempotent sync inboxes, and deterministic reconciliation.

---

## 1. Executive Summary

Milestone 12 establishes the emergency fallback subsystem for the Digital Student Attendance System, enabling continuous attendance tracking during local campus server outages or campus-wide network blackouts. While Milestone 10 and 11 provide online dynamic QR and Bluetooth BLE presence verification, Milestone 12 guarantees operational continuity without sacrificing cryptographic integrity or auditability.

---

## 2. Invariants & Safeguards Enforced

1. **INV-01 (Client Cannot Mark Itself Present)**:
   - Neither the lecturer device nor student mobile client can grant attendance credit locally.
   - The student mobile client captures cryptographic presence evidence (host-signed offline QR challenge + optional BLE tag).
   - The student outbox displays `Locally Recorded (Pending Server Sync)`—never `PRESENT`.
   - The authoritative campus server evaluates evidence signatures, verifies roster membership, and executes `AttendanceService.record_verified_checkpoint_credit`.
2. **INV-03 (Server UTC Clock Authority & Monotonic Anchor)**:
   - Student and lecturer device wall clocks are untrusted.
   - An `OfflineClockAnchor` captures server UTC time and device monotonic uptime at permit receipt.
   - Monotonic drift is bounded (default max 300s). Monotonic rollback (phone reboot) invalidates the anchor and fails closed.
3. **INV-04 (Cryptographic Token Expiry)**:
   - Dynamic offline QR challenges rotate every 20 seconds.
   - Tokens presented outside the tolerance window (±1 slot) are rejected unconditionally.
4. **INV-05 (No Duplicate Checkpoint Credit)**:
   - Checkpoint-level uniqueness constraint `(attendance_checkpoint_id, student_id)` prevents duplicate credit.
   - Retried sync batches are handled idempotently via `SyncInboxEntry`.
5. **INV-07 (Identifiable Offline History & Immutable Revision Ledger)**:
   - Reconciled evidence records carry `source_mode="OFFLINE_SYNC"`.
   - Immutable audit revision logs (`AttendanceRevision`) record all reconciliation and manual conflict overrides.

---

## 3. Cryptographic Architecture

```text
Server Keypair (Ed25519)                      Lecturer Device (Ephemeral Ed25519)
  [OFFLINE_PERMIT_SIGNING_PRIVATE_KEY]           [temporary_host_private_key] (in-memory/keystore)
  [OFFLINE_PERMIT_SIGNING_PUBLIC_KEY]            [temporary_host_public_key]
                |                                             |
                v                                             v
     Signs Offline Permit                         Signs Dynamic QR & Event Chain
  (Binds lecturer pubkey,                        (H_n = SHA256(H_{n-1} || seq || payload))
   validity window, digests)                                  |
                |                                             v
                +------------------------------> Reconciled on Server Sync
```

---

## 4. API Endpoints

- `GET /api/v1/attendance/offline/verification-keys`: Public key retrieval for permit verification.
- `POST /api/v1/attendance/offline/permits/request`: Lecturer permit request with ephemeral public key.
- `POST /api/v1/attendance/offline/sync/host-events`: Ingest lecturer event hash chain and trigger reconciliation.
- `POST /api/v1/attendance/offline/sync/student-claims`: Ingest student attendance claims (authenticated user ID).
- `GET /api/v1/attendance/offline/conflicts`: Administrative review queue for disputed offline events.
- `POST /api/v1/attendance/offline/conflicts/{id}/resolve`: Administrative conflict resolution and manual credit.

---

## 5. Database Tables Added (Migration 009)

1. `offline_attendance_permits`
2. `offline_host_sessions`
3. `offline_host_events`
4. `offline_attendance_claims`
5. `sync_inbox_entries`
6. `offline_sync_conflicts`
