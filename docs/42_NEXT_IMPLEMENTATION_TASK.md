# Digital Student Attendance System
## 42. Next Implementation Task — Milestone 11 Handoff

**Document Version:** 1.0  
**Status:** Ready for Milestone 11 Execution  
**Task ID:** `TASK-009 — Bluetooth BLE Presence Verification`  
**Milestone:** 11 (Bluetooth BLE Presence Verification)  
**Governing Specs:** `docs/01_PRODUCT_REQUIREMENTS_PRD.md`, `docs/04_ATTENDANCE_RULES.md`, `docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md`, `docs/07_SYSTEM_ARCHITECTURE.md`, `docs/08_DOMAIN_MODEL.md`, `docs/09_DATABASE_SCHEMA.md`, `docs/10_API_SPECIFICATION.md`, `docs/15_ARCHITECTURE_DECISIONS.md`, `docs/41_MILESTONE_10_DYNAMIC_QR_PRESENCE_TOKENS.md`

---

> [!WARNING]
> **HANDOFF BOUNDARY**: This task specification is prepared as the formal entry point for Milestone 11.
> **DO NOT EXECUTE THIS TASK DURING MILESTONE 10.**
> Implementation begins only upon explicit human approval to initiate Milestone 11.

---

## 1. Task Objective

Implement the Bluetooth Low Energy (BLE) presence verification layer for the **Digital Student Attendance System**, establishing:

### 1.1 Classroom BLE Proximity Verification
- **Beacon Advertising & Scanning**:
  - Lecturer podium or room-mounted BLE beacon advertising rotating ephemeral identifiers.
  - Student mobile device BLE discovery during active checkpoint windows (`START`, `MIDDLE`, `END`).
- **RSSI Proximity & Threshold Filtering**:
  - Calibrated Received Signal Strength Indication (RSSI) filtering to ensure student physical presence inside the classroom boundary (typically $-70$ to $-85$ dBm threshold depending on room size).
  - Prevention of "drive-by" or adjacent-hallway attendance claims.
- **Multi-Factor Presence Verification (Dynamic QR + BLE Proximity)**:
  - Corroboration of dynamic QR token scans with BLE proximity telemetry.
  - Configurable policy thresholds (e.g., QR required, BLE optional/corroborative, or dual-factor strictly required).

### 1.2 Mobile BLE Discovery & Telemetry Ingestion
- **Flutter BLE Client**:
  - Background/foreground BLE scanning with minimal battery impact during checkpoint windows.
  - Packaging BLE telemetry (beacon UUID, major/minor, RSSI, scan timestamp) alongside presence evidence.
- **Client Cannot Mark Itself Present (INV-01)**:
  - Telemetry submitted as raw evidence to `AttendanceEvidence` (`source_mode="BLUETOOTH_BLE"`).
  - Server verifies beacon validity, RSSI thresholds, session window, and active roster.

### 1.3 Anti-Spoofing & Relay Mitigations
- **Rotating Ephemeral Beacons**:
  - Beacon payload rotates on synchronized time slots to prevent static beacon clone/relay attacks.
- **Device Attestation & Telemetry Checks**:
  - Sanity check scan timestamps against authoritative server UTC clock (INV-03).

---

## 2. Technical Deliverables for Milestone 11

1. **Backend BLE Telemetry Processing**:
   - `backend/app/attendance/ble.py`: Beacon cryptographic validation, RSSI threshold evaluation, and distance estimation algorithms.
   - Extension to `AttendanceService.record_verified_checkpoint_credit` supporting `source_mode="BLUETOOTH_BLE"` or composite evidence.
2. **API Endpoints**:
   - `GET /api/v1/attendance/checkpoints/{checkpoint_id}/ble-beacon`: Beacon emission parameters for authorized classroom devices.
   - `POST /api/v1/attendance/ble/verify`: Ingestion endpoint for BLE proximity evidence.
3. **Mobile Client Updates**:
   - `apps/mobile/lib/services/ble_scanner_service.dart`: BLE beacon scanning and telemetry capture.
   - Permissions management for Bluetooth and location permissions on Android/iOS.
4. **Comprehensive Test Suite**:
   - Fast unit tests with simulated RSSI values and rotating beacon IDs.
   - Service integration tests verifying single and dual-factor check-ins.
   - RBAC tests verifying authorization and unassigned lecturer rejections.
5. **Documentation & Handoff**:
   - `docs/43_MILESTONE_11_BLUETOOTH_BLE.md`
   - `docs/44_NEXT_IMPLEMENTATION_TASK.md` (Milestone 12 Offline Attendance & Reconciliation)

---

## 3. Strict Prohibitions & Architectural Invariants

* **DO NOT** introduce hardware dependencies that break CI/CD (all BLE tests must run with mockable telemetry).
* **DO NOT** implement offline queueing or reconciliation during M11 (strictly reserved for Milestone 12).
* **DO NOT** remove or weaken dynamic QR presence verification (M10).
* **DO NOT** allow client to determine proximity; server evaluates raw RSSI against policy rules.
