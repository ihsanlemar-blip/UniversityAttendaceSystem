# Milestone 11 — Bluetooth Low Energy (BLE) Presence Verification Specification

## 1. Executive Summary & Attendance Invariants

Milestone 11 establishes the secondary proximity verification layer via rotating, cryptographically authenticated Bluetooth Low Energy (BLE) broadcasts. Designed to work in synergy with Milestone 10 dynamic QR tokens, BLE provides physical co-presence evidence, preventing remote relay attacks and attendance fraud.

### Core Invariants Enforced

* **INV-01 (Client Cannot Mark Itself Present)**: The student mobile device captures raw BLE advertisement telemetry (compact payload, RSSI, device timestamp) and submits it to the server. The server presence engine cryptographically verifies the advertisement, checks authoritative rotation slots, enforces RSSI proximity thresholds, and awards checkpoint credit. The client never marks itself present.
* **INV-03 (Authoritative University Clock)**: BLE token rotation slots and expiration checks rely strictly on the university server's UTC clock. Device clock manipulations cannot extend slot validity.
* **INV-04 (Zero Tolerance for Expired Tokens)**: BLE payloads expire at their rotation slot boundary (default 20 seconds). Outdated rotation slots are rejected unconditionally with `BLE_PAYLOAD_EXPIRED`.
* **INV-05 (No Duplicate Checkpoint Credit)**: Exactly one credit can be awarded per student per checkpoint per attendance session. Duplicate multi-factor submissions return an idempotent success response with `already_credited: true`.
* **Bluetooth Signal $\neq$ Final Attendance**: Detection of a BLE beacon is physical proximity evidence only. The server domain engine evaluates combined policy evidence before awarding checkpoint credit or calculating attendance status.
* **Classroom Shared Broadcast Model**: The lecturer broadcaster emits a rotating BLE advertisement. Multiple students in the physical room detect and submit the same broadcast within its valid slot.
* **Dual-Factor Presence Policy**: Supports configurable session policy modes (`QR_ONLY` and `QR_AND_BLE`). Under `QR_AND_BLE`, check-in requires both a valid dynamic QR token and a valid contemporaneous BLE observation.
* **Cryptographic Separation**: BLE authentication uses dedicated `ATTENDANCE_BLE_SIGNING_KEY`, which is strictly isolated from `AUTH_SIGNING_KEY` and `ATTENDANCE_QR_SIGNING_KEY`.
* **Student Identity Derivation**: Check-in endpoints derive student identity exclusively from the authenticated JWT context (`current_user`). Request payloads never contain client-supplied student IDs.

---

## 2. Cryptographic Binary Specification

Classroom BLE broadcasts utilize a 17-byte compact binary payload designed for BLE advertising packet constraints (31-byte legacy limit).

### 2.1 17-Byte Binary Structure
```
+---------------+------------------------+------------------------------------+
|  Version (1B) |   Rotation Slot (4B)   |   HMAC-SHA256 Truncated Tag (12B)  |
|     uint8     |     uint32 big-endian  |          96-bit auth tag           |
+---------------+------------------------+------------------------------------+
|    Byte 0     |       Bytes 1-4        |             Bytes 5-16             |
+---------------+------------------------+------------------------------------+
```

### 2.2 Deterministic Cryptographic Context Binding
The 96-bit HMAC tag binds all session and checkpoint context to prevent replay across checkpoints or sessions:
$$\text{Context} = \text{version (1B)} \,\|\, \text{university\_id (16B)} \,\|\, \text{session\_id (16B)} \,\|\, \text{checkpoint\_id (16B)} \,\|\, \text{checkpoint\_type (UTF-8)} \,\|\, \text{rotation\_slot (4B)}$$

$$\text{FullTag} = \text{HMAC-SHA256}(\text{ATTENDANCE\_BLE\_SIGNING\_KEY}, \text{Context})$$

$$\text{TruncatedTag} = \text{FullTag}[0..12]$$

* `version`: Protocol version byte (`0x01`).
* `rotation_slot`: Deterministic 4-byte big-endian integer:
  $$\text{rotation\_slot} = \left\lfloor \frac{\text{server\_time\_utc}}{\text{rotation\_seconds}} \right\rfloor$$
* `TruncatedTag`: First 96 bits (12 bytes) of HMAC-SHA256. Verified in constant time via `hmac.compare_digest`.

---

## 3. Server Architecture & Verification Pipeline

### 3.1 Endpoints
1. `GET /api/v1/attendance/checkpoints/{checkpoint_id}/ble-advertisement`:
   - Restricted to assigned Lecturers and Administrators (enforces `attendance.checkpoint_manage`).
   - Students denied with 403 Forbidden.
   - Requires active session and open checkpoint window.
   - Returns `BleAdvertisementResponse` with `payload_base64`, `payload_hex`, `service_uuid`, `rotation_seconds`, `issued_at`, `expires_at`.
   - Emits `Cache-Control: no-store` to prevent caching.
2. `POST /api/v1/attendance/presence/check-in`:
   - Self-service multi-factor endpoint for enrolled students.
   - Accepts `PresenceCheckInRequest(qr_token, ble_observation)`.
   - Derives student identity from JWT `current_user`.
   - Evaluates session policy requirement mode (`QR_ONLY` or `QR_AND_BLE`).
   - Validates RSSI against configured minimum threshold (default: $\ge -85\text{ dBm}$).
   - Records verified checkpoint credit via core attendance service.
   - Returns `PresenceCheckInResponse` (idempotent duplicate on repeat submission).

---

## 4. Mobile Architecture (Flutter)

* **BLE Scanning (`BleScannerService`)**: Scans for classroom service UUID `0000fee0-0000-1000-8000-00805f9b34fb`. Extracts payload, RSSI, and client timestamp.
* **BLE Broadcasting (`BleAdvertiserService`)**: Advertises 17-byte compact binary payload via `flutter_ble_peripheral`.
* **Multi-Factor Scanner Screen (`StudentQrScannerScreen`)**: Displays real-time camera viewfinder alongside live BLE detection status badge. Bundles QR code with latest observed BLE beacon for submission to `/presence/check-in`.
* **Permissions**:
  - Android: `BLUETOOTH_SCAN` (`neverForLocation`), `BLUETOOTH_ADVERTISE`, `BLUETOOTH_CONNECT`.
  - iOS: `NSBluetoothAlwaysUsageDescription`, `NSBluetoothPeripheralUsageDescription`.
