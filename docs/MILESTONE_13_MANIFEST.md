# Digital Student Attendance System
## Milestone 13 Manifest — Student Device Registration, Primary Device Trust & Cryptographic Attendance Binding

**Generated At:** 2026-09-16  
**Feature Branch:** `feature/task-011-device-registration-trust`  
**Milestone:** 13 — Student Device Registration, Primary Device Trust & Cryptographic Attendance Binding  

---

## 1. Inventory of Files Created / Modified

### 1.1 Database & Migrations
- `backend/migrations/versions/010_device_registration_trust.py`: Versioned Alembic migration creating `trusted_devices`, `device_registration_challenges`, `device_replacement_requests`, and `device_trust_events` tables with partial unique index `uq_trusted_devices_active_student`.
- `backend/app/models/trusted_device.py`: SQLAlchemy 2.0 declarative models for device entities.
- `backend/app/models/__init__.py`: Registered device models.

### 1.2 Backend Core & Security
- `backend/app/core/constants.py`: Added enums (`DeviceStatus`, `DeviceRole`, `DeviceReplacementStatus`, `DeviceTrustEventType`) and 7 fine-grained RBAC permissions (`device:register`, `device:view`, `device:replace`, `device:manage`, `device:approve_replacement`, `device:view_all`, `device:suspend`, `device:reactivate`).
- `backend/app/core/config.py`: Added settings `ATTENDANCE_DEVICE_TRUST_ENABLED` (boolean, default True) and `DEVICE_REGISTRATION_CHALLENGE_LIFETIME_SECONDS` (int, default 300).
- `backend/app/rbac/seeding.py`: Seeded device permissions for Student, Lecturer, Admin, and Super Admin roles.

### 1.3 Device Trust Subsystem (`backend/app/devices/`)
- `backend/app/devices/__init__.py`: Package initialization.
- `backend/app/devices/crypto.py`: Asymmetric Ed25519 cryptographic routines (SPKI key parsing, SHA-256 canonical fingerprint generation, payload builders, and signature verification).
- `backend/app/devices/schemas.py`: Pydantic request/response schemas for registration challenges, activations, replacement requests, admin reviews, and device proof objects.
- `backend/app/devices/service.py`: `DeviceTrustService` managing single active device invariant, challenge-response proof-of-possession, atomic replacements, student self-revocation, administrative suspension/reactivation, and online check-in proof verification.
- `backend/app/devices/router.py`: REST API mounted at `/api/v1/devices` enforcing strict RBAC permissions.
- `backend/app/api/v1/router.py`: Registered device router in root API v1 router.

### 1.4 Attendance Presence Engine Integration
- `backend/app/attendance/schemas.py`: Integrated optional `device_proof` in `QRCheckInRequest`.
- `backend/app/attendance/service.py`: Enforced device trust verification on dynamic QR check-ins; records device ID and fingerprint in evidence metadata.
- `backend/app/attendance/offline_schemas.py`: Added `device_proof` to `OfflineClaimSubmissionItem`.
- `backend/app/attendance/offline_service.py`: Enforced device trust verification during offline claim submission and batch reconciliation.

### 1.5 Web Client (`apps/web/`)
- `apps/web/src/app/admin/devices/page.tsx`: Production administrative management console featuring:
  - 3-Tab interface: "Active Trusted Devices", "Pending Replacement Requests", and "Device Trust Audit Events".
  - Quick action controls: Approve/Reject device replacement requests with notes, Suspend active devices, Reactivate suspended devices.
  - Live status badges, cryptographic fingerprint rendering, and search filters.

### 1.6 Mobile Client (`apps/mobile/`)
- `apps/mobile/pubspec.yaml`: Added dependencies `cryptography`, `flutter_secure_storage`, and `crypto`.
- `apps/mobile/lib/services/device_key_service.dart`: Hardware-backed Ed25519 keypair generation, OS secure storage persistence, SHA-256 fingerprinting, canonical payload generation, and digital signing.
- `apps/mobile/lib/screens/student_device_security_screen.dart`: Dedicated student screen displaying device trust status, full/short fingerprints, registration date, activation actions, and "Report Lost/Stolen" revocation workflow.
- `apps/mobile/lib/screens/student_qr_scanner_screen.dart`: Seamlessly signs and attaches device trust proof to dynamic QR scans.
- `apps/mobile/lib/services/qr_checkin_service.dart` & `presence_checkin_service.dart`: Transmits device proof schemas.
- `apps/mobile/lib/offline/offline_storage.dart`: Persists device proof in offline attendance claims.

### 1.7 Automated Test Suites
- `backend/tests/test_device_crypto.py`: 11 tests verifying Ed25519 signature validation, payload determinism, bad signatures, and fingerprint computations.
- `backend/tests/test_device_registration.py`: 8 tests verifying single-use challenges, proof-of-possession, active device single-primary constraints, second-phone rejection, and self-report-lost revocation.
- `backend/tests/test_device_replacement.py`: 6 tests verifying candidate replacement creation, admin approval with atomic status transition, rejection, and invalid state transitions.
- `backend/tests/test_device_rbac.py`: 4 tests verifying student vs admin permission boundaries.
- `backend/tests/test_attendance_device_trust.py`: 4 tests verifying dynamic QR check-in with device proof, tampered/mismatched proof rejection, suspended device rejection, and backward compatibility when disabled.
- `backend/tests/test_offline_device_trust.py`: 3 tests verifying offline claim submission with device proof, rogue device rejection, and batch reconciliation.
- `apps/mobile/test/device_security_test.dart`: 7 tests verifying key generation, persistence, deterministic challenge signing, presence check-in signing, and offline claim signing.

---

## 2. Verification & Quality Gate Results

| Test / Gate | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| **Backend Device Crypto** | `test_device_crypto.py` | 11 passed | PASS |
| **Backend Registration** | `test_device_registration.py` | 8 passed | PASS |
| **Backend Replacement** | `test_device_replacement.py` | 6 passed | PASS |
| **Backend RBAC** | `test_device_rbac.py` | 4 passed | PASS |
| **Backend Attendance Trust** | `test_attendance_device_trust.py` | 4 passed | PASS |
| **Backend Offline Trust** | `test_offline_device_trust.py` | 3 passed | PASS |
| **Backend Regression** | QR, BLE, Offline Reconciliation | 15 passed | PASS |
| **Python Static Typing** | `mypy backend` | 180 files checked, 0 errors | PASS |
| **Python Linting & Formatting**| `ruff check`, `ruff format` | Clean, 0 errors | PASS |
| **Alembic Schema Drift** | `alembic check` | 0 drift detected | PASS |
| **Web Lint & Typecheck** | Next.js `npm run lint`, `type-check` | Clean, 0 errors | PASS |
| **Web Production Build** | Next.js `npm run build` | Turbopack compiled successfully | PASS |
| **Flutter Analysis** | `dart analyze` | 0 errors, 0 warnings | PASS |
| **Flutter Test Suite** | `flutter test` | 43 passed (100%) | PASS |

---

## 3. Compliance with Invariants

- **INV-01 (Client Cannot Mark Itself Present)**: Verified. Client submits signed proof of possession; backend verifies device validity, student enrollment, and session state before granting credit.
- **INV-03 (Server UTC Authority)**: Verified. Server UTC clock governs challenge expiry and proof timestamps.
- **INV-04 (Token Expiration)**: Verified. Registration challenges expire after 300 seconds and can only be consumed once.
- **INV-05 (No Duplicate Credit)**: Verified. Idempotency guarantees remain intact across online and offline check-ins.
- **Single Active Device**: Verified. Database partial unique index `uq_trusted_devices_active_student` ensures no student can possess two simultaneous active devices.
- **Private Key Isolation**: Verified. Device private keys reside strictly in device secure storage and are never transmitted or stored server-side.
