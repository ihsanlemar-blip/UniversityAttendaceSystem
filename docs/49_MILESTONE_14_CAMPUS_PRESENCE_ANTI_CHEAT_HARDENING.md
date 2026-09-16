# Milestone 14: Campus Network Presence, Radio Environment Analysis & Anti-Cheat Hardening

**Version:** 1.0  
**Approved Scope:** Server-observed source IP resolution with right-to-left reverse proxy trust, Campus Network CIDR zones with longest-prefix matching, short-lived (20s TTL) cryptographic network challenges signed by registered M13 Ed25519 device keys, single-use consumption with idempotent retry and submission revalidation, network presence policy snapshotting (`DISABLED`, `OPTIONAL`, `REQUIRED`), deterministic factorized anti-cheat risk signals for human review (INV-01: never auto-modifying attendance or sanctioning), classroom BLE radio environment diagnostics with RSSI percentiles (strictly no distance conversion), Next.js `/admin/security` management console, and Flutter check-in integration.

---

## 1. Executive Summary

Milestone 14 introduces campus network environmental verification and anti-cheat diagnostic capabilities to the Digital Student Attendance System without compromising user privacy or violating foundational architectural invariants. By validating student presence against server-observed IP subnets using short-lived asymmetric cryptographic challenges and computing passive classroom BLE radio percentiles, the platform provides administrators with clear, explainable diagnostic evidence for human review while preserving all offline fallbacks (Milestone 12) and primary device trust protections (Milestone 13).

---

## 2. Fundamental Security Invariants & Directives

1. **Client Never Dictates Observed IP**:
   - The server attendance engine resolves the client's network address strictly using server-observed socket peer IP and right-to-left reverse proxy traversal against configured `TRUSTED_PROXY_CIDRS`.
   - Client-supplied headers (`X-Forwarded-For`, `Client-IP`, `X-Real-IP`) from untrusted origins are stripped or ignored to prevent address spoofing.

2. **Short-Lived (20s TTL) Single-Use Network Challenges**:
   - Network challenges carry a maximum validity of 20 seconds (`ATTENDANCE_NETWORK_CHALLENGE_TTL_SECONDS = 20`) and an internal cryptographic nonce.
   - Challenges are cryptographically bound to the authenticated student, their registered M13 device, the attendance session, the checkpoint, and the matching campus network zone.
   - Upon verification in `verify_qr_checkin` or `verify_presence_checkin`, challenges transition atomically from `ISSUED` to `CONSUMED`.
   - Replay attempts of consumed challenges are rejected unconditionally. Idempotent retries from the identical student for the identical checkpoint are preserved.

3. **Anti-Cheat Signals Never Auto-Sanction (INV-01 & Section 3)**:
   - Anti-cheat risk signals are deterministic, explainable, factorized diagnostic records created strictly for authorized human administrative review.
   - Signals **never** automatically alter attendance records (mark Absent, revoke credit, or convert Present to Absent) and **never** automatically apply student or lecturer sanctions.
   - Signal review workflow follows a strictly audited progression: `OPEN` -> `ACKNOWLEDGED` -> `RESOLVED` or `DISMISSED` with mandatory explanation notes.
   - Idempotency is guaranteed across repeated check-in attempts via a unique composite `risk_key`.

4. **Zero Physical Distance Claims for Radio Diagnostics**:
   - Classroom BLE radio diagnostics compute statistical percentiles (count, median, p10, p25, p75, p90, min, max) over recorded RSSI samples.
   - Radio metrics reflect dynamic RF multipath interference and occupancy; they are **never** mapped or converted to physical geometric distances.

5. **Offline Fallback Preserved (Milestone 12 & 13)**:
   - Offline emergency attendance claims recorded during campus network blackouts continue to be processed and reconciled without requiring live network challenge verification.

---

## 3. Database Schema (`011_campus_presence_anti_cheat`)

### Tables Introduced:

1. **`campus_network_zones`**:
   - `id`: UUIDv7 (PK)
   - `university_id`: UUID (FK -> `universities.id`, RESTRICT)
   - `building_id`: UUID (FK -> `buildings.id`, SET NULL, nullable)
   - `name`: VARCHAR(128)
   - `code`: VARCHAR(64) (Unique per university: `uq_campus_network_zones_code`)
   - `network_cidr`: VARCHAR(64) (Normalized CIDR prefix)
   - `ip_version`: SMALLINT (4 or 6)
   - `zone_type`: VARCHAR(32) (`CAMPUS_TRUSTED`, `CLASSROOM_HOTSPOT`, `FACULTY_OFFICE`, `RESIDENCE_HALL`, etc.)
   - `status`: VARCHAR(32) (`ACTIVE`, `INACTIVE`, `DEPRECATED`)
   - `priority`: INTEGER (0–1000, higher priority matches first in LPM)
   - `allow_student_presence`: BOOLEAN (default True)
   - `metadata`: JSONB

2. **`campus_network_challenges`**:
   - `id`: UUIDv7 (PK)
   - `university_id`: UUID (FK -> `universities.id`, RESTRICT)
   - `user_id`: UUID (FK -> `users.id`, RESTRICT)
   - `trusted_device_id`: UUID (FK -> `trusted_devices.id`, RESTRICT)
   - `attendance_session_id`: UUID (FK -> `attendance_sessions.id`, RESTRICT)
   - `attendance_checkpoint_id`: UUID (FK -> `attendance_checkpoints.id`, RESTRICT)
   - `network_zone_id`: UUID (FK -> `campus_network_zones.id`, SET NULL, nullable)
   - `nonce`: VARCHAR(64)
   - `nonce_hash`: VARCHAR(64)
   - `issued_ip`: VARCHAR(64)
   - `status`: VARCHAR(32) (`ISSUED`, `CONSUMED`, `EXPIRED`, `INVALIDATED`)
   - `issued_at_utc`: TIMESTAMPTZ
   - `expires_at_utc`: TIMESTAMPTZ (issued_at + 20s)
   - `consumed_at_utc`: TIMESTAMPTZ (nullable)
   - `consumed_ip`: VARCHAR(64) (nullable)

3. **`attendance_risk_signals`**:
   - `id`: UUIDv7 (PK)
   - `university_id`: UUID (FK -> `universities.id`, RESTRICT)
   - `risk_key`: VARCHAR(255) (Unique per university: `uq_attendance_risk_signals_key`)
   - `signal_type`: VARCHAR(64) (Deterministic enum member)
   - `severity`: VARCHAR(20) (`INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
   - `risk_points`: INTEGER (nullable)
   - `subject_type`: VARCHAR(30) (`STUDENT`, `LECTURER`, `SYSTEM`)
   - `subject_user_id`: UUID (FK -> `users.id`, SET NULL, nullable)
   - `trusted_device_id`: UUID (FK -> `trusted_devices.id`, SET NULL, nullable)
   - `attendance_session_id`: UUID (FK -> `attendance_sessions.id`, SET NULL, nullable)
   - `class_occurrence_id`: UUID (FK -> `class_occurrences.id`, SET NULL, nullable)
   - `course_offering_id`: UUID (FK -> `course_offerings.id`, SET NULL, nullable)
   - `context`: JSONB (Explainable telemetry and factor details)
   - `rule_version`: VARCHAR(20) (e.g. "1.0")
   - `status`: VARCHAR(30) (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`)
   - `detected_at`: TIMESTAMPTZ
   - `reviewed_at`: TIMESTAMPTZ (nullable)
   - `reviewed_by_user_id`: UUID (FK -> `users.id`, SET NULL, nullable)
   - `review_note`: TEXT (nullable)

### Policy Enhancements (`attendance_policies`):
- Added columns:
  - `network_presence_mode`: VARCHAR(30) (default `DISABLED`)
  - `lecturer_network_presence_mode`: VARCHAR(30) (default `DISABLED`)
  - `allow_university_wide_zones`: BOOLEAN (default True)

---

## 4. Architectural Implementation Highlights

- **Client Network Resolver (`ClientNetworkResolver`)**: Right-to-left reverse proxy parsing against `TRUSTED_PROXY_CIDRS`, spoof protection, longest-prefix matching (LPM) over IPv4 and IPv6 subnets, and building affinity validation.
- **Canonical Challenge Protocol (`build_network_challenge_payload`)**: Deterministic payload structure signed with student's M13 Ed25519 key:
  `NETWORK_PRESENCE_V1|{challenge_id}|{nonce}|{user_id}|{university_id}|{trusted_device_id}|{attendance_session_id}|{attendance_checkpoint_id}|{network_zone_id}|{issued_iso}|{expires_iso}`
- **Anti-Cheat Risk Engine (`AntiCheatService`)**: Deterministic detection rules for unverified networks, network zone mismatches, replay attacks, forward header spoofing, device replacement velocity, account reuse, overlapping attendance, mass manual attendance, high correction rates, and schedule window deviations.
- **Radio Environment Diagnostics (`RadioAnalysisService`)**: Percentile calculator computing observation counts, median, P10, P25, P75, P90, min, and max RSSI values from recorded BLE evidence.
- **Next.js Web Admin Console (`/admin/security`)**: 3-tab administrative portal providing zone configuration, an interactive human risk review queue with mandatory justification notes, and classroom radio diagnostics.
- **Flutter Mobile Client Integration**: Added `CampusNetworkService`, challenge acquisition and Ed25519 signing via `DeviceKeyService.signNetworkPresenceChallenge`, and network proof attachment during check-in.
