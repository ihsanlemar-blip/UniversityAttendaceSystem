# Milestone 19 — University Pilot Incident & Defect Log

This log tracks all anomalies, bugs, and edge cases discovered during Milestone 19 field execution across physical classrooms, mobile devices, BLE broadcasters, and campus networks.

---

## Severity Model & Resolution Targets

- **BLOCKER**: Attendance credit loss, cross-tenant exposure, cryptographic or authentication bypass, inability to start or finish lecture session.  
  *Action:* Halt affected pilot activity immediately. Preserve device/server logs. Must resolve before proceeding.
- **HIGH**: Major workflow broken, offline claim unrecoverable on reconnection, systematic failure on a major device model/OS tier.  
  *Action:* Investigate within 4 hours. Mitigation or hotfix required before cohort sign-off.
- **MEDIUM**: Functional defect with documented operational workaround (e.g., manual roll-call fallback available, UI glitch not blocking attendance).  
  *Action:* Schedule fix or document operational procedure.
- **LOW**: Minor cosmetic, localization typo, or non-blocking layout annoyance.  
  *Action:* Log for M20 release polish.

---

## Incident Log Entries

| Incident ID | Date / Time | Reporter | Role | Device / Model | Room / Location | Severity | Summary / Symptom | Status | Resolution / Fix Commit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| *Example: INC-001* | *2026-09-17 10:00* | *QA Lead* | *Lecturer* | *Dell XPS 13 (Caddy/Chrome)* | *Room C* | *LOW* | *RTL badge alignment in Dari on 1366x768* | *RESOLVED* | *CSS padding adjusted in apps/web* |

---

## Incident Details Template (Copy for Each Incident)

### [INC-XXX] Title of Incident

- **Incident ID:** INC-XXX
- **Timestamp (UTC):** YYYY-MM-DD HH:MM:SS
- **Reporter / Actor:** Name / User ID
- **Role:** STUDENT / LECTURER / ADMIN / ATTENDANCE_OFFICER / AUDITOR
- **Device & OS:** e.g. Samsung Galaxy A14, Android 13, One UI Core 5.1
- **Classroom / Location:** e.g. Lecture Hall C (Building 2, 2nd Floor)
- **Course / Session ID:** e.g. CS-201 / Occurrence UUID
- **Severity:** BLOCKER / HIGH / MEDIUM / LOW
- **Expected Behavior:** Description of specification requirement
- **Actual Behavior:** What actually happened during field run
- **Server Trace ID / Mobile Error Code:** e.g. `REQ-2026-98124`, `BLE_RSSI_TOO_LOW`
- **Reproduction Steps:**
  1. Step 1
  2. Step 2
  3. Step 3
- **Operational Workaround (if any):** e.g. Lecturer used manual override with recorded justification
- **Root Cause Analysis:** Technical explanation
- **Remediation Commit:** Git commit SHA
- **Retest & Verification Date:** Verification timestamp and tester name
