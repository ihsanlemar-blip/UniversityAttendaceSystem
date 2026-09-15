# Milestone 13: Student Device Registration, Primary Device Trust & Cryptographic Attendance Binding

**Version:** 1.0  
**Approved Scope:** Asymmetric Ed25519 device identities, OS secure hardware storage (Android Keystore / iOS Keychain), single active primary device invariant, proof of possession registration challenges, authorized device replacement workflow, cryptographic attendance check-in binding (online & offline), and administrative device trust governance.

---

## 1. Executive Summary

Milestone 13 introduces hardware-backed device registration and primary device trust to eliminate proxy attendance, token sharing, and unauthorized remote check-ins. By binding each student strictly to a single active physical mobile device via asymmetric Ed25519 cryptographic keys, attendance claims cannot be forged or delegated even if access credentials or dynamic tokens are forwarded.

---

## 2. Fundamental Security Invariants

1. **Private Keys Never Leave the Device**:
   - The private key is generated on the student mobile device and persisted strictly within hardware-backed secure storage (`FlutterSecureStorage` using Android Keystore / iOS Keychain).
   - Private keys are **never** transmitted across the network, **never** stored in the database, **never** written to log files, and **never** returned in API responses.
   - The university server stores only the public key in PEM format and its canonical SHA-256 fingerprint.

2. **Single Active Device per Student (`uq_trusted_devices_active_student`)**:
   - Each student is constrained at the database engine level to at most one `ACTIVE` trusted device.
   - Enforced via PostgreSQL partial unique index:
     ```sql
     CREATE UNIQUE INDEX uq_trusted_devices_active_student
     ON trusted_devices (student_id)
     WHERE status = 'ACTIVE';
     ```

3. **Proof of Possession (Challenge-Response Registration)**:
   - Device registration cannot be achieved by merely presenting a public key.
   - The server issues a cryptographically secure, single-use, time-bounded (default 300s) challenge with a random nonce.
   - The device must sign the canonical registration payload using its private key. The server validates the Ed25519 signature before activating the device.

4. **Authorized Device Replacement Workflow**:
   - A student attempting to register on a secondary phone cannot overwrite their active device.
   - The student must initiate a `DeviceReplacementRequest` providing the candidate device's public key, proof of possession, and a justification reason.
   - University administrators review replacement requests via the Web UI (`/admin/devices`).
   - Approval executes an atomic state transition:
     `old_device.status = REPLACED`, `new_device.status = ACTIVE`, and `request.status = APPROVED`.

5. **Cryptographic Attendance Evidence Binding**:
   - When `ATTENDANCE_DEVICE_TRUST_ENABLED=True`, presence check-ins (dynamic QR, BLE dual-factor, offline claims) require a `DeviceProofSchema` containing `device_id`, `proof_id`, and `signature`.
   - The canonical payload includes the student's `user_id`, `university_id`, `device_id`, `proof_id`, and modality token (`qr_token` or `offline_claim_id`).
   - Any check-in from an unregistered, replaced, suspended, or revoked device, or with an invalid signature, is rejected unconditionally with HTTP 403.

6. **Immutable Device Trust Audit Ledger (`device_trust_events`)**:
   - All lifecycle events (`CHALLENGE_ISSUED`, `REGISTERED`, `REPLACEMENT_REQUESTED`, `REPLACEMENT_APPROVED`, `REPLACEMENT_REJECTED`, `SUSPENDED`, `REACTIVATED`, `REVOKED`, `LOST_REPORTED`) are recorded in an append-only audit ledger with actor IDs and network metadata.

---

## 3. Threat Model & Defenses

| Threat Scenario | Attack Vector | Milestone 13 Defense |
| :--- | :--- | :--- |
| **Token Forwarding / Proxy Attendance** | Student in lecture takes screenshot or photo of dynamic QR/BLE code and messages it to an absent peer. | The absent peer cannot sign the check-in with the enrolled student's private key. Submissions without valid Ed25519 device signatures are rejected (HTTP 403). |
| **Simultaneous Multi-Device Login** | Student logs in on multiple phones and shares credentials with friends to check in simultaneously in different classes. | Database partial unique index permits only 1 active device per student. Second device registration requires administrative approval and revokes the first. |
| **Private Key Extraction** | Attacker attempts to dump device application data to clone the student's identity. | Hardware-backed Android Keystore / iOS Keychain prevents non-root key extraction. OS-level sandboxing protects key material. |
| **Replay Attacks** | Attacker intercepts a signed check-in proof and re-submits it in a subsequent checkpoint. | Proof payloads bind checkpoint-specific nonces/tokens (`qr_token`, `claim_id`) and unique `proof_id`. Expired tokens fail validation. |
| **Rogue Device Claim in Offline Mode** | Student attempts to submit forged offline claims from an unapproved phone during a campus network blackout. | Server reconciliation verifies device trust proof against the student's active device public key before granting attendance credit. |

---

## 4. Database Schema (`010_device_registration_trust`)

### Tables Introduced:
1. **`trusted_devices`**:
   - `id`: UUID (PK)
   - `student_id`: UUID (FK -> `students.id`)
   - `device_role`: VARCHAR (`PRIMARY`, `BACKUP`)
   - `public_key_pem`: TEXT (Ed25519 SPKI format)
   - `public_key_fingerprint`: VARCHAR(64) (SHA-256 hex)
   - `device_label`: VARCHAR(128)
   - `platform`: VARCHAR(32) (`android`, `ios`, `macos`, `windows`, `linux`, `web`)
   - `app_version`: VARCHAR(32)
   - `status`: VARCHAR(32) (`ACTIVE`, `PENDING_VERIFICATION`, `SUSPENDED`, `REPLACED`, `REVOKED`)
   - `first_registered_at_utc`: TIMESTAMPTZ
   - `last_used_at_utc`: TIMESTAMPTZ
   - `replaced_by_device_id`: UUID (FK -> `trusted_devices.id`, nullable)
   - `suspension_reason`: TEXT (nullable)
   - Partial Unique Index: `uq_trusted_devices_active_student` on `(student_id)` WHERE `status = 'ACTIVE'`.

2. **`device_registration_challenges`**:
   - `id`: UUID (PK)
   - `student_id`: UUID (FK -> `students.id`)
   - `candidate_public_key`: TEXT
   - `candidate_fingerprint`: VARCHAR(64)
   - `nonce`: VARCHAR(64)
   - `status`: VARCHAR(32) (`PENDING`, `VERIFIED`, `EXPIRED`, `CONSUMED`)
   - `issued_at_utc`: TIMESTAMPTZ
   - `expires_at_utc`: TIMESTAMPTZ
   - `consumed_at_utc`: TIMESTAMPTZ (nullable)

3. **`device_replacement_requests`**:
   - `id`: UUID (PK)
   - `student_id`: UUID (FK -> `students.id`)
   - `current_device_id`: UUID (FK -> `trusted_devices.id`)
   - `candidate_public_key`: TEXT
   - `candidate_fingerprint`: VARCHAR(64)
   - `candidate_device_label`: VARCHAR(128)
   - `candidate_platform`: VARCHAR(32)
   - `reason`: TEXT
   - `status`: VARCHAR(32) (`PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`)
   - `requested_at_utc`: TIMESTAMPTZ
   - `reviewed_by_user_id`: UUID (FK -> `users.id`, nullable)
   - `reviewed_at_utc`: TIMESTAMPTZ (nullable)
   - `review_notes`: TEXT (nullable)

4. **`device_trust_events`**:
   - `id`: UUID (PK)
   - `student_id`: UUID (FK -> `students.id`)
   - `device_id`: UUID (FK -> `trusted_devices.id`, nullable)
   - `event_type`: VARCHAR(64)
   - `actor_id`: UUID (FK -> `users.id`, nullable)
   - `ip_address`: VARCHAR(45) (nullable)
   - `user_agent`: VARCHAR(256) (nullable)
   - `event_metadata`: JSONB (nullable)
   - `created_at_utc`: TIMESTAMPTZ

---

## 5. API Endpoints (`/api/v1/devices`)

| Method | Endpoint | Permission / Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/devices/challenges` | `device:register` | Request registration challenge for candidate device |
| `POST` | `/api/v1/devices/register` | `device:register` | Submit challenge signature to activate primary device |
| `GET` | `/api/v1/devices/me` | `device:view` | View current student's active device & trust status |
| `POST` | `/api/v1/devices/me/report-lost` | `device:manage` | Student immediately revokes their own lost/stolen device |
| `POST` | `/api/v1/devices/replacement-requests` | `device:replace` | Submit candidate replacement request |
| `GET` | `/api/v1/devices/replacement-requests` | `device:approve_replacement` | Admin list pending/all replacement requests |
| `POST` | `/api/v1/devices/replacement-requests/{id}/approve` | `device:approve_replacement` | Admin approves replacement request |
| `POST` | `/api/v1/devices/replacement-requests/{id}/reject` | `device:approve_replacement` | Admin rejects replacement request |
| `GET` | `/api/v1/devices/admin/all` | `device:view_all` | Admin device inventory list |
| `POST` | `/api/v1/devices/admin/{id}/suspend` | `device:suspend` | Admin suspends device |
| `POST` | `/api/v1/devices/admin/{id}/reactivate` | `device:reactivate` | Admin reactivates suspended device |

---

## 6. Verification Summary

- **Backend Tests**:
  - `test_device_crypto.py`: 11 passed
  - `test_device_registration.py`: 8 passed
  - `test_device_replacement.py`: 6 passed
  - `test_device_rbac.py`: 4 passed
  - `test_attendance_device_trust.py`: 4 passed
  - `test_offline_device_trust.py`: 3 passed
  - Regression (QR, BLE, Offline): 15 passed
- **Static Analysis**:
  - `ruff check backend`: 0 issues
  - `ruff format --check backend`: 180 files clean
  - `mypy backend`: 0 issues across 180 source files
- **Web Console**:
  - Next.js 16.3.3 Turbopack build passed
  - ESLint and TypeScript compilation passed
  - Route `/admin/devices` operational with 3 tabs (Active Devices, Pending Approvals, History)
- **Mobile Client**:
  - `flutter pub get`: clean
  - `dart analyze`: 0 issues
  - `flutter test`: 43 passed (100%)
