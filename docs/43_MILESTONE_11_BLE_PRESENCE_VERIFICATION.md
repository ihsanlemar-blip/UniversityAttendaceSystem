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

### 4.1 Lecturer BLE Broadcaster (`LecturerBleBroadcastScreen` & `LecturerBleService`)
* **Broadcasting UI**: Screen displaying course code, course name, checkpoint badge (`START`, `MIDDLE`, `END`), and a circular countdown gauge (`${secondsRemaining}s`) indicating remaining validity in the current rotation slot.
* **Rotation Lifecycle**: 
  - On mount/start, fetches live advertisement payload from `GET /api/v1/attendance/checkpoints/{checkpoint_id}/ble-advertisement` via `LecturerBleService`.
  - Converts the base64-encoded server payload to raw 17 binary bytes and passes it to `BleAdvertiserService.startAdvertisingFromBase64()`.
  - When remaining validity drops to $\le 1\text{s}$, automatically re-fetches the latest rotation slot from the server and updates the radio broadcast without interruption.
  - Lifecycle controls: Lecturers can **Pause** (halts radio broadcast; UI switches to Paused), **Resume** (re-fetches and broadcasts current valid slot), or **Stop Beacon** (halts radio and concludes broadcast).
  - Screen disposal immediately cancels rotation timers and calls `_advertiserService.stopAdvertising()`.
* **Hardware & Permission Handling**:
  - Checks `checkSupported()`: If peripheral mode is unsupported on hardware, displays informative non-blocking guidance (`BLE Peripheral Mode Unsupported`) indicating students can still check in using the classroom dynamic QR code.
  - If Bluetooth is disabled or permission denied, presents actionable `Bluetooth Disabled` state with `Retry Connection` button.
  - Handles server domain errors: `SESSION_PAUSED` suspends broadcast with status banner; `CHECKPOINT_NOT_OPEN` / `CHECKPOINT_WINDOW_EXPIRED` halts radio and shows `Broadcast Concluded`.

### 4.2 Student Multi-Factor Scanner (`StudentQrScannerScreen` & `BleScannerService`)
* **BLE Scanning (`BleScannerService`)**: Continuously scans for classroom service UUID `0000fee0-0000-1000-8000-00805f9b34fb`. Parses incoming `serviceData` (or fallback `manufacturerData`), captures raw 17 bytes, RSSI, client timestamp, and emits typed `BleObservation`.
* **Viewfinder Badge**: Displays live detection status (`Classroom BLE detected (-XX dBm)` with green icon, or `Searching for classroom BLE beacon...`).
* **Multi-Factor Bundling**: Combines scanned dynamic QR token with the contemporaneous BLE observation and submits to `POST /api/v1/attendance/presence/check-in`.

### 4.3 Service Data & Binary Transmission Contract
* **Zero Base64 Over Radio**: The backend issues `payload_base64` (a 24-character base64 string) over HTTPS.
* **Decoding to Binary**: In `ble_advertiser_service.dart`, `startAdvertisingFromBase64` executes `base64.decode()`, producing exactly 17 raw binary bytes (`Uint8List`).
* **Radio Emission**: `AndroidAdvertiseData` broadcasts the raw 17-byte buffer under `serviceDataUuid: serviceUuid` and `manufacturerData: payload`. Base64 text is never transmitted over the Bluetooth radio.
* **Student Reception & Submission**: The student scanner receives the exact 17 raw bytes in `advertisementData.serviceData`, base64-encodes them for HTTPS transport, and sends them to `/presence/check-in`. The server decodes the 17 bytes and performs constant-time HMAC-SHA256 verification.

### 4.4 Proximity RSSI Policy & Institutional Default
* **Default Threshold**: Configured at `ATTENDANCE_BLE_MIN_RSSI = -85 dBm` (institution default).
* **Policy-Configurable**: Overridable per session via `session.policy_snapshot.get("ble_min_rssi")`.
* **Heuristic Nature**: `-85 dBm` is an empirical classroom wall-attenuation heuristic, NOT a distance guarantee. Real-world RF absorption varies by room geometry, human density, and wall materials. RSSI is validated between `-120 dBm` and `0 dBm`.
* **Residual Risk**: Client-reported RSSI can be modified on rooted/tampered devices. Proximity verification relies on the combination of rotating dynamic QR and BLE, not RSSI in isolation.

### 4.5 Mobile Platform Permissions
* **Android**:
  - `android.permission.BLUETOOTH_SCAN` with `android:usesPermissionFlags="neverForLocation"` (Android 12+ API 31+).
  - `android.permission.BLUETOOTH_ADVERTISE`.
  - `android.permission.BLUETOOTH_CONNECT`.
* **iOS**:
  - `NSBluetoothAlwaysUsageDescription`: Explains Bluetooth proximity verification during attendance sessions.
  - `NSBluetoothPeripheralUsageDescription`: Explains classroom presence beacon broadcasting for lecturers.

---

## 5. Physical Device Acceptance Checklist

> [!CAUTION]
> The following 30-item acceptance checklist must be manually executed with physical devices before production deployment. In automated CI/CD and developer environments, software verification is complete via mockable BLE stream abstractions and zero real-world sleeps.

**Test Setup:**
* **Device A:** Lecturer physical phone (Android / iOS)
* **Device B:** Student physical phone (Android)
* **Device C:** Student physical phone (iOS)

| # | Test Item | Verification Procedure | Expected Result | Status |
|---|---|---|---|---|
| 1 | Lecturer Login | Authenticate with assigned lecturer credentials on Device A | Dashboard loads with authorized course offerings | [ ] PENDING HARDWARE |
| 2 | Open Active Session | Select scheduled class occurrence and start session | Session status transitions to `ACTIVE` | [ ] PENDING HARDWARE |
| 3 | Open START Checkpoint | Open attendance checkpoint on projector/lecturer app | Checkpoint status is `OPEN`, window begins | [ ] PENDING HARDWARE |
| 4 | Start BLE Broadcasting | Tap "Broadcast BLE Beacon" on Device A | `LecturerBleBroadcastScreen` initializes | [ ] PENDING HARDWARE |
| 5 | Lecturer UI Active Badge | Inspect broadcaster screen on Device A | Displays `BLE BROADCAST ACTIVE` & countdown | [ ] PENDING HARDWARE |
| 6 | Student Enable Bluetooth | Enable Bluetooth on student Device B | Device B Bluetooth radio is active | [ ] PENDING HARDWARE |
| 7 | Student BLE Detection | Open scanner screen on Device B in classroom | Badge indicates `Classroom BLE detected (-XX dBm)` | [ ] PENDING HARDWARE |
| 8 | QR Code Detection | Point Device B camera at classroom projector QR | Dynamic QR code decoded instantly | [ ] PENDING HARDWARE |
| 9 | Dual-Factor Submit | Submit combined QR + BLE evidence from Device B | Submits to `/api/v1/attendance/presence/check-in` | [ ] PENDING HARDWARE |
| 10 | Backend Credit Awarded | Check response payload on Device B | `accepted: true`, `already_credited: false` | [ ] PENDING HARDWARE |
| 11 | Rescan Idempotency (INV-05) | Rescan same QR/BLE on Device B | `accepted: true`, `already_credited: true` (no double credit) | [ ] PENDING HARDWARE |
| 12 | Shared Multi-Student Broadcast | Scan same projected QR & BLE from Device C | Second student accepted: `accepted: true`, credit awarded | [ ] PENDING HARDWARE |
| 13 | Slot Rotation Wait | Observe countdown timer on Device A reach 0s | Timer resets to 20s; payload smoothly refreshes | [ ] PENDING HARDWARE |
| 14 | Payload Update Verification | Compare BLE payload emitted in slot $N$ vs $N+1$ | 17-byte binary payload rotates deterministically | [ ] PENDING HARDWARE |
| 15 | Continuous Detection | Keep Device B scanner open during slot rotation | Detection badge updates to new slot without error | [ ] PENDING HARDWARE |
| 16 | Telemetry Interception | Capture BLE broadcast payload in slot $N$ | Payload extracted for delayed replay test | [ ] PENDING HARDWARE |
| 17 | Expired Slot Rejection (INV-04) | Replay captured slot $N$ after slot expiration | Server rejects with `BLE_PAYLOAD_EXPIRED` (400) | [ ] PENDING HARDWARE |
| 18 | Session Pause Behavior | Lecturer pauses session on web dashboard | Broadcasting halted; student check-ins suspended | [ ] PENDING HARDWARE |
| 19 | Advertiser Radio Halt | Inspect Device A radio when session paused | BLE advertising ceases; UI shows `Broadcast Paused` | [ ] PENDING HARDWARE |
| 20 | Session Resume Reconnection | Lecturer resumes attendance session | Device A fetches new slot; broadcast resumes | [ ] PENDING HARDWARE |
| 21 | Checkpoint Window Close | Let checkpoint window close naturally | Device A concludes broadcast; radio turns off | [ ] PENDING HARDWARE |
| 22 | Student Bluetooth Off | Turn off Bluetooth on Device B | UI displays clear guidance to enable Bluetooth | [ ] PENDING HARDWARE |
| 23 | Lecturer Bluetooth Off | Turn off Bluetooth on Device A | UI displays `Bluetooth Disabled` with retry button | [ ] PENDING HARDWARE |
| 24 | Bluetooth Permission Denied | Deny Bluetooth scan permission on Device B | UI displays actionable permission recovery message | [ ] PENDING HARDWARE |
| 25 | Out-of-Room Attenuation | Move Device B to adjacent hallway/behind wall | RSSI drops significantly ($< -85\text{ dBm}$) | [ ] PENDING HARDWARE |
| 26 | RSSI Attenuation Profile | Record RSSI at 1m, 5m, 10m, and behind classroom door | Log RSSI gradient across physical boundaries | [ ] PENDING HARDWARE |
| 27 | RSSI Boundary Non-Distance | Verify edge-case check-in near threshold | Borderline RSSI evaluated by server threshold | [ ] PENDING HARDWARE |
| 28 | Broadcaster Disposal | Navigate back from Device A broadcaster screen | Radio stops immediately; no orphaned background beacon | [ ] PENDING HARDWARE |
| 29 | Scanner Disposal | Navigate back from Device B scanner screen | Camera and BLE scanning halt immediately | [ ] PENDING HARDWARE |
| 30 | Release Build Integrity | Inspect release APK/IPA build on Device B | Manual token paste field completely absent | [ ] PENDING HARDWARE |

---

## 6. Verification Status & Operational Directives

> [!IMPORTANT]
> **SOFTWARE VERIFICATION COMPLETE; MANUAL BLE DEVICE ACCEPTANCE REQUIRED BEFORE PILOT/PRODUCTION.**
>
> All backend domain services, cryptographic binary encoding/decoding engines, REST routers, Flutter scanning and advertising services, widget screen implementations, and automated test suites are 100% complete and green across unit, integration, and CI quality gates.
> 
> Production and institutional deployment must execute the 30-item Physical Device Acceptance Checklist above on physical Android and iOS hardware in designated lecture halls.

