# Next Implementation Task: Milestone 14 — Wi-Fi Presence Verification, Radio Environment Analysis & Fraud Scoring

**Status:** Up Next (Do NOT begin implementation in Milestone 13 task)  
**Applies to:** Next Coding Agent Milestone Handoff  

---

## 1. Task Objective

Implement **Milestone 14: Wi-Fi Presence Verification, Radio Environment Analysis & Fraud Scoring** for the Digital Student Attendance System. Milestone 14 introduces contextual campus network environmental verification to detect relay proxies, remote emulator injection, and unauthorized off-campus check-ins.

---

## 2. Invariants & Guardrails (Mandatory)

1. **Strict Non-Intrusiveness**:
   - Do NOT introduce continuous location tracking or background GPS draining.
   - Radio environment scanning (Wi-Fi BSSID/SSID, BLE RSSI) is strictly point-in-time telemetry captured only during active check-in initiation.
2. **Server-Side Evaluation Solely**:
   - The mobile client collects and submits raw radio environment telemetry.
   - The server presence engine alone evaluates room AP match scores and fraud risk thresholds.
   - Client cannot compute its own presence score or approve its own attendance.
3. **Graceful Fallback**:
   - Environments where campus Wi-Fi telemetry is unavailable or restricted by OS privacy settings must fall back smoothly to dynamic QR and BLE dual-factor verification without blocking legitimate students.
4. **Zero Real-World Sleeps**:
   - Fast testing strategy with zero `time.sleep()` or `asyncio.sleep()`.

---

## 3. Anticipated Milestone 14 Scope

1. **Campus Network & Access Point Registry**:
   - Schema mapping facilities and rooms to authorized Wi-Fi BSSIDs and subnet CIDRs (`room_access_points`).
   - Alembic migration `011_wifi_presence_verification.py`.
2. **Environmental Telemetry Collection**:
   - Mobile client point-in-time Wi-Fi BSSID and BLE scan digest generation.
   - Attachment to check-in payload.
3. **Fraud Scoring Engine**:
   - Multi-factor scoring weighting:
     - Checkpoint Token (Dynamic QR)
     - Proximity Factor (BLE Beacon RSSI)
     - Hardware Binding (Ed25519 Device Signature)
     - Environmental Factor (Wi-Fi BSSID Match)
   - Risk classification (`LOW_RISK`, `MEDIUM_RISK`, `FLAGGED_SUSPICIOUS`).
4. **Admin Risk Review Dashboard**:
   - View flagged check-ins with anomaly breakdowns.

---

> [!WARNING]
> Do NOT begin writing code or migrations for Milestone 14 in this session. Milestone 13 must first be merged to `main` with all quality gates verified.
