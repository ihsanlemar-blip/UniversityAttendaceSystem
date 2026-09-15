# Next Implementation Task: Milestone 13 — Student Device Registration & Trust

## 1. Task Objective

Implement **Milestone 13: Student Device Registration & Trust** for the Digital Student Attendance System. Milestone 13 enforces strict single-device binding and cryptographic device attestation for student mobile devices, preventing unauthorized multi-device proxy attendance and credential sharing.

---

## 2. Invariants & Guardrails (Mandatory)

* **Single Active Device Invariant**: Each student account may only have one active registered mobile device at any time.
* **Cryptographic Device Attestation**: Devices generate a hardware-backed asymmetric key pair during registration. Subsequent check-in claims must be signed with this private key.
* **Controlled Device Replacement**: A student cannot arbitrarily bind multiple devices. Device replacement requires administrative approval or a secure cooldown period.
* **Zero Real-World Sleeps**: Fast testing strategy with zero `time.sleep()` or `asyncio.sleep()`.

---

## 3. High-Level Milestone 13 Scope

1. **Device Registration Data Model**:
   - `student_devices` table tracking device fingerprints, public keys, registration status, enrollment date, and attestation metadata.
   - Alembic migration `010_student_device_registration.py`.
2. **Device Registration REST API**:
   - `POST /api/v1/devices/register`: Register new student device with cryptographic public key.
   - `POST /api/v1/devices/replace-request`: Student requests device replacement.
   - `GET /api/v1/devices/pending-approvals`: Admin list of replacement requests.
   - `POST /api/v1/devices/{device_id}/approve`: Admin approves replacement.
3. **Presence Engine Device Verification**:
   - Bind attendance check-in evidence to the student's registered device.
   - Reject check-in requests from unauthorized devices.
4. **Mobile Client Keystore & Key Generation**:
   - Flutter secure hardware key storage and request signing.
