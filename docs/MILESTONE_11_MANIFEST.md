# Digital Student Attendance System
## Milestone 11 Manifest — Bluetooth Low Energy (BLE) Presence Verification

**Milestone:** 11 (Bluetooth Low Energy Presence Verification)  
**Git Branch:** `feature/task-009-ble-presence-verification`  
**Status:** Completed & Validated  
**Date:** September 2026  

---

## 1. File Inventory

| Path | Category | Description |
|---|---|---|
| `backend/app/core/config.py` | Configuration | Added typed `ATTENDANCE_BLE_*` settings and strict cryptographic separation (`ATTENDANCE_BLE_SIGNING_KEY != AUTH_SIGNING_KEY` and `!= ATTENDANCE_QR_SIGNING_KEY`) |
| `backend/app/attendance/ble.py` | Cryptographic Engine | `BlePresenceEngine` with 17-byte compact binary structure, deterministic rotation slot math, context binding, and constant-time HMAC tag verification |
| `backend/app/attendance/schemas.py` | Pydantic Schemas | `BleAdvertisementResponse`, `BleObservationSchema`, `PresenceCheckInRequest`, `PresenceCheckInResponse` |
| `backend/app/attendance/service.py` | Domain Service | Implemented `generate_checkpoint_ble_advertisement` and `verify_presence_checkin` supporting `QR_ONLY` and `QR_AND_BLE` multi-factor policy modes |
| `backend/app/attendance/router.py` | API Router | Mounted `GET /checkpoints/{checkpoint_id}/ble-advertisement` (with `Cache-Control: no-store`) and `POST /presence/check-in` |
| `backend/tests/test_ble_tokens.py` | Unit Test Suite | 8 pure unit tests verifying rotation math, 17-byte binary layout, context binding, key separation, tampering, and RSSI threshold |
| `backend/tests/test_ble_service.py` | Integration Test Suite | 7 integration tests verifying dual-factor check-in, shared broadcast, idempotency, weak RSSI rejection, expired slots, and snapshot immutability |
| `backend/tests/test_ble_rbac.py` | RBAC Test Suite | 2 end-to-end API tests verifying lecturer authorization, unassigned lecturer 403, student check-in, duplicate check-in, and tampering rejection |
| `apps/mobile/pubspec.yaml` | Mobile Dependencies | Added `flutter_blue_plus: ^2.3.12` and `flutter_ble_peripheral: ^3.1.0` |
| `apps/mobile/android/app/src/main/AndroidManifest.xml` | Mobile Permissions | Added Android BLE permissions (`BLUETOOTH_SCAN` with `neverForLocation`, `BLUETOOTH_ADVERTISE`, `BLUETOOTH_CONNECT`) |
| `apps/mobile/ios/Runner/Info.plist` | Mobile Permissions | Added `NSBluetoothAlwaysUsageDescription` and `NSBluetoothPeripheralUsageDescription` |
| `apps/mobile/lib/services/ble_scanner_service.dart` | Mobile Service | Proximity BLE scanner service for classroom presence beacons |
| `apps/mobile/lib/services/ble_advertiser_service.dart` | Mobile Service | Lecturer BLE advertising broadcaster service |
| `apps/mobile/lib/services/presence_checkin_service.dart` | Mobile Service | HTTP client service submitting multi-factor presence evidence |
| `apps/mobile/lib/screens/student_qr_scanner_screen.dart` | Mobile UI | Integrated live BLE detection status badge with camera viewfinder and dual-factor submission |
| `apps/mobile/test/ble_scanner_service_test.dart` | Mobile Unit Tests | Unit tests verifying BleObservation serialization and mock scanner stream behavior |
| `apps/mobile/test/presence_checkin_service_test.dart` | Mobile Unit Tests | Unit tests verifying PresenceCheckInResult deserialization and exceptions |
| `apps/mobile/test/qr_scanner_screen_test.dart` | Mobile Widget Tests | Widget tests verifying camera preview, release mode hiding of manual input, and live BLE status badge |
| `.github/workflows/ci.yml` | CI Workflow | Added BLE unit, service, and RBAC test suites to Backend Shard 4 |
| `docs/43_MILESTONE_11_BLE_PRESENCE_VERIFICATION.md` | Documentation | Architectural specification for BLE presence verification |
| `docs/44_NEXT_IMPLEMENTATION_TASK.md` | Handoff Document | Boundary and entry specification for Milestone 12 |
| `scripts/check_docs.py` | Verification Script | Updated to validate 45 docs (00-44) and manifests M3 through M11 |

---

## 2. Invariant Audit

1. **Client Cannot Mark Itself Present (INV-01)**: Enforced. The mobile client sends raw telemetry to `POST /api/v1/attendance/presence/check-in`. The server attendance engine evaluates evidence and determines attendance credit.
2. **Attendance Depends on Server/Domain Validation (INV-02)**: Enforced. Multi-factor presence evaluation and checkpoint crediting execute strictly within server domain services.
3. **Student Device Clock Is NOT Authoritative (INV-03)**: Enforced. Token rotation slot computation and expiration rely strictly on the university server UTC clock.
4. **Expired Dynamic QR/Tokens Cannot Grant Attendance (INV-04)**: Enforced. Expired rotation slots are rejected immediately with `BLE_PAYLOAD_EXPIRED`.
5. **No Duplicate Checkpoint Credit (INV-05)**: Enforced. Idempotent response with `already_credited: true` on duplicate submission without double-crediting.
6. **Bluetooth Signal $\neq$ Final Attendance**: Enforced. BLE provides proximity evidence; final attendance status is computed by policy rules in M9 core.
7. **Classroom Shared Broadcast Model**: Enforced. Multiple enrolled students can observe and submit the same classroom advertisement broadcast.
8. **Cryptographic Key Separation**: Enforced. `ATTENDANCE_BLE_SIGNING_KEY` is validated at startup to be distinct from `AUTH_SIGNING_KEY` and `ATTENDANCE_QR_SIGNING_KEY`.
9. **Zero Database Schema Drift**: Enforced. Uses existing `attendance_evidence.source_mode="BLUETOOTH_BLE"` and `evidence_metadata` JSONB. Zero new migrations required.
