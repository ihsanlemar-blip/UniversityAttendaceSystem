# Milestone 19 — University Pilot & Acceptance Plan

**Document ID:** `59_MILESTONE_19_UNIVERSITY_PILOT_ACCEPTANCE`  
**Status:** Part 1 Complete — Ready for Field Execution  
**Task Identifier:** `TASK-017`  
**Applies to:** Field Engineers, Campus IT Administrators, Registrars, Lecturers, Students, and Quality Evaluators.  
**Authoritative Reference:** [`docs/58_NEXT_IMPLEMENTATION_TASK.md`](file:///e:/01_Projects/UniversityAttendaceSystem/docs/58_NEXT_IMPLEMENTATION_TASK.md)  
**Quality Baseline:** [`docs/26_DEFINITION_OF_DONE.md`](file:///e:/01_Projects/UniversityAttendaceSystem/docs/26_DEFINITION_OF_DONE.md)  
**Security Baseline:** [`docs/12_SECURITY_REQUIREMENTS.md`](file:///e:/01_Projects/UniversityAttendaceSystem/docs/12_SECURITY_REQUIREMENTS.md)  

---

## 1. Executive Summary & Non-Fabrication Invariant

Milestone 19 transitions the Digital Student Attendance System from lab/automated testing to **empirical physical validation** in a real university campus environment.

> [!CAUTION]
> **Strict Invariant — Zero Physical Acceptance Fabrication:**
> Milestone 19 is fundamentally NOT an automated feature milestone. It exists to evaluate behavior on real mobile hardware, physical Bluetooth beacons, live lecture displays, and actual campus Wi-Fi infrastructure.
> **No manual field acceptance test may be marked `PASSED` during Part 1.**
> In this preparation artifact, all test gates are formally initialized to `PLANNED`, `NOT RUN`, or `BLOCKED` (if hardware is inaccessible). Results will only be updated in Part 2 upon verifiable field execution with concrete, recorded evidence.

---

## 2. University Pilot Scope & Organizational Topology

The pilot is sized to represent a realistic cross-section of university operations while isolating pilot activities from general production systems:

- **Institution:** Kabul University (پوهنتون کابل)
- **Academic Unit (Faculty):** Faculty of Computer Science (پوهنځی کمپیوټر ساینس)
- **Departments (2):**
  1. Software Engineering (څانګه انجنیري سافټویر)
  2. Information Systems (څانګه سیستم‌های معلوماتی)
- **Academic Semester:** Fall 2026 (`FALL-2026`)
- **Active Course Offerings (5):**
  - `CS-101`: Fundamentals of Computer Science (اساسات کمپیوټر ساینس) — Section A
  - `CS-201`: Data Structures and Algorithms (ساختمان داده‌ها و الگوریتم‌ها) — Section A
  - `CS-305`: Database Management Systems (سیستم‌های مدیریت پایگاه داده) — Section B
  - `SE-302`: Software Engineering Principles (انجنیري سافټویر) — Section A
  - `IS-401`: Computer Networks and Security (شبکه‌های کمپیوتری) — Section A
- **Participant Cohort:**
  - **University Administrators / Registrars:** 2 staff members
  - **Attendance Officer:** 1 designated reviewer
  - **Compliance Auditor:** 1 read-only auditor
  - **Lecturers / Instructors:** 4 active faculty members (`LEC-001` through `LEC-004`)
  - **Student Cohort:** 60 enrolled students (`STU-2026-001` through `STU-2026-060`) across morning and afternoon shifts.
- **High-Density Concurrency Target:** 100+ simultaneous scan test planned in Lecture Hall C.

---

## 3. Physical Classroom Selection & Environmental Conditions

Classrooms were selected to evaluate diverse radio-frequency (RF), optical, and spatial characteristics:

| Classroom ID | Room Name / Type | Capacity | Display Equipment | RF / Network Environment | Evaluation Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ROOM-A** | Seminar Room 102 | 30 | 65-inch 4K Wall Monitor | Direct line-of-sight, dedicated AP (`10.100.1.0/24`) | Baseline optical scanning, clean BLE containment |
| **ROOM-B** | Lecture Room 204 | 60 | Overhead HD Projector (1080p) | Standard classroom, shared hallway AP | Projection contrast, ambient sunlight, mid-density |
| **ROOM-C** | Auditorium 1 | 120 | High-lumen dual auditorium projectors | High ceiling, concrete pillars, dense Wi-Fi | **High-density burst (100+ students)**, long-distance QR |
| **CORRIDOR-1** | Outside Room B / C | N/A | None (Hallway barrier) | Concrete wall barrier (25cm reinforced) | BLE anti-proxy attenuation and adjacent-room bleed |

---

## 4. Mobile Device Hardware Matrix

To ensure realistic validation without assuming high-end hardware, the pilot device matrix emphasizes low-cost Android smartphones commonly used by students in Afghanistan, alongside standard reference units:

| Tier | Manufacturer & Model | OS Version | Hardware Specs | BLE Scanning | BLE Advertise | Keystore / Keychain | Role in Pilot |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Budget Android** | Samsung Galaxy A14 | Android 13 | 4GB RAM, Exynos 850 | BLE 5.0 Supported | BLE 5.0 Supported | Android Keystore (StrongBox) | Student primary cohort |
| **Budget Android** | Xiaomi Redmi 10C / 12C | Android 12 / 13 | 3GB/4GB RAM, Snapdragon 680 | BLE 5.0 Supported | Not Required | Android Keystore (TEE) | Student primary cohort |
| **Entry Android** | Tecno Spark 10 / Infinix Hot 30| Android 12 | 4GB RAM, Helio G37 | BLE 5.0 Supported | Not Required | Android Keystore (Software TEE) | Low-cost edge testing |
| **Reference Android**| Google Pixel 6a / 7 | Android 14 | 6GB/8GB RAM, Tensor | BLE 5.2 Supported | BLE 5.2 Supported | Android Keystore (StrongBox) | Baseline test reference |
| **iOS Baseline** | Apple iPhone 11 / 12 | iOS 16 / 17 | 4GB RAM, A13 / A14 | CoreBluetooth | CoreBluetooth | iOS Secure Enclave | Multi-platform verification* |
| **Lecturer Laptop** | Lenovo ThinkPad / Dell XPS | Windows 11 / Ubuntu | 16GB RAM, Intel Core i5/i7 | Integrated Bluetooth 5.1 | N/A | N/A | Lecturer Web Console |

*\*Note on iOS Policy:* If physical iOS hardware cannot be procured for on-site execution during the pilot window, all iOS-specific rows in the acceptance matrix will be marked `BLOCKED / NOT RUN`. They will NEVER be fabricated.

---

## 5. Campus Server, Network & Infrastructure Architecture

### 5.1 Deployment Topology
The pilot server operates the production-hardened Docker composition (`docker-compose.prod.yml`) behind Caddy 2 reverse proxy:

```
[Student / Lecturer Devices]
            │ (HTTPS 443)
            ▼
[Campus Ingress: Caddy 2 Reverse Proxy]
    ├── Public Routes: /api/*, /health/live, /health/ready, / (Next.js Web)
    └── Restricted Routes: /metrics, /health/metrics (Internal CIDRs only)
            │
    ┌───────┴───────────────────────┐
    ▼                               ▼
[FastAPI Backend (4 Workers)]   [Next.js Web Console]
    │                               │
    ├──────────────┬────────────────┘
    ▼              ▼
[PostgreSQL 16] [Redis 7] ◄── [Celery Worker]
```

### 5.2 Campus Hostname & DNS Scope
- **Approved Pilot Hostname:** `attendance.university.edu.af` (resolving internally to `10.101.0.10`).
- **Split-Horizon DNS:** Campus DNS servers resolve `attendance.university.edu.af` directly to the Caddy ingress IP on the academic backbone.
- **TLS Certificate:** X.509 certificate issued by the University Private CA (or Let's Encrypt with automated HTTP-01 challenge).
- **Certificate Trust:** University root CA certificate distributed to managed test devices via MDM or manual profile installation. Zero `verify=False` exceptions permitted.

### 5.3 Campus Network Survey & Subnet Mapping
The physical survey mapped the following official subnets:
- **Academic Wi-Fi (Students & Staff):** `10.100.0.0/16`
- **Lecturer / Faculty LAN:** `10.101.0.0/16`
- **Campus Management & Ingress Subnet:** `10.101.0.0/24`
- **Guest / Non-Campus Subnet:** `192.168.10.0/24` (Configured as untrusted; presence verification must reject).
- **Trusted Reverse Proxy CIDRs:** `TRUSTED_PROXY_CIDRS="127.0.0.1/32,10.101.0.10/32"`

---

## 6. Comprehensive Field Acceptance Matrix

Every test is assigned a unique tracking identifier, explicit preconditions, execution steps, expected outcomes, and an initial status of `PLANNED` or `NOT RUN`.

### GROUP A — BLE / Classroom Radio Presence (7 Tests)

| Test ID | Origin | Test Title | Preconditions | Execution Steps | Expected Outcome | Status | Actual Result & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G-A01** | M11 | Physical BLE Beacon Broadcast | Lecturer starts session in Room A; BLE enabled | Start checkpoint; observe BLE broadcaster via RF analyzer | Beacons emit rotating BLE tokens every 20-30s on specified Service UUID | `PLANNED` | Pending Field Run |
| **G-A02** | M11 | Student Mobile BLE Discovery | Student in Room A; Bluetooth permission granted | Student opens scanner; holds phone within Room A | App detects BLE beacon within 5 seconds; dual-factor badge green | `PLANNED` | Pending Field Run |
| **G-A03** | M11 | Multi-Device Bluetooth Compatibility | Diverse devices (Samsung, Xiaomi, Tecno, iPhone) | All devices scan concurrently in Room B | 100% of supported models detect advertisement packet | `PLANNED` | Pending Field Run |
| **G-A04** | M11 | RSSI Boundary Calibration | Calibrated distance markers at 2m, 5m, 10m, 15m | Record RSSI values across 10 sample devices per marker | RSSI degrades smoothly; -85 dBm cutoff excludes out-of-room | `PLANNED` | Pending Field Run |
| **G-A05** | M11 | Concrete Wall RF Attenuation | Transmitter in Room B; receiver in adjacent Corridor | Measure RSSI through 25cm reinforced concrete wall | Signal drops below -90 dBm; check-in fails with `BLE_OUT_OF_RANGE` | `PLANNED` | Pending Field Run |
| **G-A06** | M11 | Adjacent-Room Isolation | Active session in Room A; inactive class in Room B | Student sitting in Room B scans QR from Room A | Server rejects check-in due to mismatched room beacon | `PLANNED` | Pending Field Run |
| **G-A07** | M11 / M18 | High-Density 100+ RF Congestion | 60-100 students in Room C scanning simultaneously | Lecturer opens 60s checkpoint window; all scan | BLE packets received without stack crash or radio freeze | `PLANNED` | Pending Field Run |

### GROUP B — Offline Attendance & Network Disconnect (10 Tests)

| Test ID | Origin | Test Title | Preconditions | Execution Steps | Expected Outcome | Status | Actual Result & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G-B01** | M12 / M18 | Lecturer Offline Permit Issuance | Lecturer authenticated online prior to session | Disconnect lecturer laptop; request offline permit | Ed25519 cryptographic permit generated and stored locally | `PLANNED` | Pending Field Run |
| **G-B02** | M12 | Offline Host Session Activation | Offline permit stored on lecturer device | Start offline class occurrence without Internet access | Host event hash chain initialized; offline dynamic QR rotates | `PLANNED` | Pending Field Run |
| **G-B03** | M12 / M18 | Student Offline Claim Capture | Student mobile device in airplane mode | Scan lecturer's rotating offline QR code | Claim written to SQLite `sync_outbox` with status `PENDING` | `PLANNED` | Pending Field Run |
| **G-B04** | M18 | Crash / Restart Durability (Mobile) | Pending claim in SQLite outbox | Force kill Flutter app via OS task manager; restart | App restarts cleanly; pending claim intact in SQLite outbox | `PLANNED` | Pending Field Run |
| **G-B05** | M18 | Device Reboot Durability | Pending claim in SQLite outbox | Full phone power reboot; relaunch attendance application | Claim preserved across device reboot without data corruption | `PLANNED` | Pending Field Run |
| **G-B06** | M12 | Campus Network Reconnection | Device has 3 offline claims in SQLite | Disable airplane mode; connect to campus Wi-Fi | Background sync triggers automatically; claims sent to server | `PLANNED` | Pending Field Run |
| **G-B07** | M12 | Server Offline Reconciliation | Server online; receives synchronized batch | Server processes claims using lecturer host hash chain | Valid claims transition to `PRESENT`; attendance records created | `PLANNED` | Pending Field Run |
| **G-B08** | M18 | Offline Dropped-ACK Retry (INV-05) | Server credited claim, but mobile dropped ACK | Mobile client retries sync for already-credited claim | Server returns success idempotently; 0 duplicate credits | `PLANNED` | Pending Field Run |
| **G-B09** | M12 | Tampered Claim Rejection | Student tampers with local claim monotonic counter | Submit tampered claim to server reconciliation API | Server detects invalid Ed25519 signature; rejects claim with 422 | `PLANNED` | Pending Field Run |
| **G-B10** | M12 | Expired Permit Rejection | Offline permit validity window expired (>24 hours) | Lecturer attempts to start session with stale permit | Application blocks session start; requires fresh online permit | `PLANNED` | Pending Field Run |

### GROUP C — Device Registration & Replacement Workflows (6 Tests)

| Test ID | Origin | Test Title | Preconditions | Execution Steps | Expected Outcome | Status | Actual Result & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G-C01** | M13 | First Device Enrolment | Student logged into mobile app on new phone | Navigate to Device Binding; tap Register This Device | Ed25519 keypair generated in Keystore/Keychain; registered on server | `PLANNED` | Pending Field Run |
| **G-C02** | M13 | Single-Device Enforcement | Student device registered | Log into second phone with same student credentials | Check-in from second phone rejected: `DEVICE_NOT_REGISTERED` | `PLANNED` | Pending Field Run |
| **G-C03** | M13 | Device Replacement Request | Student lost phone; logs into web portal | Submit replacement request with documented reason | Request appears in Admin Review Queue; status `PENDING` | `PLANNED` | Pending Field Run |
| **G-C04** | M13 | Administrator Review & Approval | Admin logged into Web Console | Review replacement justification; click Approve | Old device public key revoked; student status reset for re-binding | `PLANNED` | Pending Field Run |
| **G-C05** | M13 | Post-Approval Re-Enrolment | Approved student logs in on replacement phone | Execute device registration on new hardware | New device bound successfully; old device permanently blocked | `PLANNED` | Pending Field Run |
| **G-C06** | M13 / M14 | Replacement Frequency Rate Limit | 2 replacements in 30 days (anti-cheat limit) | Student submits 3rd replacement request in 10 days | Anti-cheat flag raised; automated approval blocked; audit alerted | `PLANNED` | Pending Field Run |

### GROUP D — Attendance Operations & Operational Workflows (7 Tests)

| Test ID | Origin | Test Title | Preconditions | Execution Steps | Expected Outcome | Status | Actual Result & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G-D01** | M10 / M17 | Live Session Roster Transitions | Occurrence active; 20 students checking in | Observe Lecturer Live Roster screen in real time | Students dynamically shift from `ABSENT` to `PRESENT` in UI | `PLANNED` | Pending Field Run |
| **G-D02** | M10 / M17 | Late Threshold Enforcement | Checkpoint opened 15m after scheduled start | Student checks in after late threshold (default 10m) | Status recorded as `LATE`; factor badge shows QR + timestamp | `PLANNED` | Pending Field Run |
| **G-D03** | M10 / M17 | Manual Roll-Call Override (INV-08)| Student phone battery dead in classroom | Lecturer opens manual override; types mandatory reason | Student marked `PRESENT`; justification logged in audit ledger | `PLANNED` | Pending Field Run |
| **G-D04** | M15 / M17 | Student Absence Excuse Submission | Student marked absent for past occurrence | Student submits medical excuse via mobile app with photo | Excuse status `SUBMITTED`; visible in Admin Review Queue | `PLANNED` | Pending Field Run |
| **G-D05** | M15 / M17 | Admin Excuse Approval Workflow | Attendance Officer opens Review Queue | Review medical note; approve excuse | Occurrence status updates to `EXCUSED`; denominator adjusted | `PLANNED` | Pending Field Run |
| **G-D06** | M15 / M17 | Admin Excuse Rejection Workflow | Review Queue item pending | Review invalid excuse note; enter reason; reject | Occurrence remains `ABSENT`; student notified with rejection note | `PLANNED` | Pending Field Run |
| **G-D07** | M15 / M18 | Immutable Audit History Check | Manual override and excuse approved | Query audit logs for student attendance record | Full historical ledger intact; original record preserved (INV-06)| `PLANNED` | Pending Field Run |

### GROUP E — Registrar Data Import & Reporting Validation (8 Tests)

| Test ID | Origin | Test Title | Preconditions | Execution Steps | Expected Outcome | Status | Actual Result & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G-E01** | M16 | Registrar Courses CSV Import | Admin in Web Console -> Imports Wizard | Upload `pilot/data/01_courses.csv`; preview | 5 rows valid; 0 errors; database not mutated in preview | `PLANNED` | Pending Field Run |
| **G-E02** | M16 | Registrar Lecturers CSV Import | Admin in Web Console -> Imports Wizard | Upload `pilot/data/02_lecturers.csv`; preview & commit | 4 lecturers created with default accounts and `must_change_password` | `PLANNED` | Pending Field Run |
| **G-E03** | M16 | Registrar Students CSV Import | Admin in Web Console -> Imports Wizard | Upload `pilot/data/03_students.csv` (60 students); commit | 60 students created; Dari/Pashto Unicode text preserved exactly | `PLANNED` | Pending Field Run |
| **G-E04** | M16 | Course Offerings & Enrollments | Courses and students committed | Upload `04_course_offerings.csv` and `05_enrollments.csv` | Offerings created; 60 enrollments assigned to active semester | `PLANNED` | Pending Field Run |
| **G-E05** | M16 | Timetable Schedule Import | Offerings committed | Upload `06_timetables.csv` with rooms and timeslots | Schedules committed; occurrences generated for pilot week | `PLANNED` | Pending Field Run |
| **G-E06** | M16 / M18 | Malformed CSV & Error Isolation | File contains missing headers & invalid time | Upload malformed CSV in strict mode | Import rejected in preview; specific line numbers flagged | `PLANNED` | Pending Field Run |
| **G-E07** | M16 / M18 | Formula Injection Sanitization | CSV contains `=cmd\|' /C calc'!A0` in name | Upload file; export staged rows report | Cell value prepended with single quote (`'`); formula neutralized | `PLANNED` | Pending Field Run |
| **G-E08** | M17 | Official Attendance Report Export | Attendance recorded for pilot sessions | Export Department Attendance Summary as CSV & Excel | Report generated with correct totals, thresholds, and Afghan dates | `PLANNED` | Pending Field Run |

### GROUP F — End-to-End MVP User Experience (8 Tests)

| Test ID | Origin | Test Title | Preconditions | Execution Steps | Expected Outcome | Status | Actual Result & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G-F01** | M17 | Student Mobile Onboarding | First-time student login with temporary credentials| Log in; complete mandatory password change | User forced to update password; redirected to home dashboard | `PLANNED` | Pending Field Run |
| **G-F02** | M17 | Lecturer Web Session Flow | Lecturer logs in; opens today's timetable | Tap "Start Session" -> Open Checkpoint -> Display QR | Dynamic QR renders immediately; timer circle rotates every 20s | `PLANNED` | Pending Field Run |
| **G-F03** | M17 | Dari (`fa-AF`) Localization | Language switched to Dari in Web & Mobile | Inspect labels across home, roster, reports, excuses | Authentic Afghan terminology (پوهنځی, څانګه, تایم, حاضر, معذور) | `PLANNED` | Pending Field Run |
| **G-F04** | M17 | Pashto (`ps`) Localization | Language switched to Pashto in Web & Mobile | Inspect labels across home, scanner, settings, review | Authentic Afghan Pashto terminology (پوهنتون, رخصتي, ناوخته) | `PLANNED` | Pending Field Run |
| **G-F05** | M17 | RTL Layout Mirroring | Active language set to Dari or Pashto | Verify layout direction on mobile and web | Proper RTL mirroring: sidebars on right, text aligned right | `PLANNED` | Pending Field Run |
| **G-F06** | M17 | Alphanumeric LTR Isolation | In RTL mode, view student numbers and course codes | Inspect codes: `CS-101`, `STU-2026-001` | English codes rendered in LTR direction without character reversal| `PLANNED` | Pending Field Run |
| **G-F07** | M17 | Auditor Role Read-Only Enforcement | User logged in with `AUDITOR` role | Attempt to open checkpoint or approve review item | UI buttons disabled; API calls return 403 Forbidden | `PLANNED` | Pending Field Run |
| **G-F08** | M17 | Low-Cost Android UX & Contrast | Testing on Tecno Spark 10 / Samsung Galaxy A14 | Navigate full check-in flow under classroom daylight | Fonts legible (min 14sp); contrast ratio meets WCAG AA (4.5:1) | `PLANNED` | Pending Field Run |

### ADDITIONAL M18 PHYSICAL VALIDATION (8 Tests)

| Test ID | Origin | Test Title | Preconditions | Execution Steps | Expected Outcome | Status | Actual Result & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G-M01** | M18 | Campus Wi-Fi Subnet Verification | Student connected to `10.100.1.50` (Academic AP)| Scan QR code during open checkpoint | Network challenge succeeds; campus IP verified by server | `PLANNED` | Pending Field Run |
| **G-M02** | M18 | External Subnet Rejection | Student connected to cellular 4G or Guest Wi-Fi | Attempt check-in during active class occurrence | Rejected: `CAMPUS_NETWORK_NOT_DETECTED` (when policy enforced) | `PLANNED` | Pending Field Run |
| **G-M03** | M18 | Trusted Proxy Source-IP Anti-Spoof | External client sends `X-Forwarded-For: 10.100.1.5` | Send request directly to Caddy ingress | Caddy/server ignores spoofed header; pins to direct peer IP | `PLANNED` | Pending Field Run |
| **G-M04** | M18 | QR Projector Low-Light Readability | Room B with blinds closed; projector at 1080p | Student scans from row 5 (approx. 6 meters away) | Camera preview locks on QR within 2s; token validates | `PLANNED` | Pending Field Run |
| **G-M05** | M18 | QR Projector Bright-Light Readability| Room B with blinds open; sunlight on screen | Student scans from row 3 (approx. 4 meters away) | Camera exposure adjusts; QR successfully parsed | `PLANNED` | Pending Field Run |
| **G-M06** | M18 | Campus Local DNS Resolution | Connect mobile device to campus Wi-Fi | Resolve `attendance.university.edu.af` in mobile browser | Resolves to internal ingress IP without public DNS lookup | `PLANNED` | Pending Field Run |
| **G-M07** | M18 | Internal Operational Metrics Protection | Query `https://attendance.university.edu.af/metrics`| Send HTTP GET from untrusted external device | Ingress rejects with HTTP 403 Forbidden; metrics not exposed | `PLANNED` | Pending Field Run |
| **G-M08** | M18 | Controlled Server Restart Recovery | Active class occurrence running | Restart backend container: `docker compose restart backend`| Uvicorn restarts; sessions resume cleanly; no state corruption | `PLANNED` | Pending Field Run |

---

## 7. Operational Roles & Participant Directory

All pilot participants are assigned identifiable, authenticated accounts to ensure full audit attribution:

| Role Identifier | Assigned Pilot Participant | System Username | Email Address | Assigned Faculty / Department |
| :--- | :--- | :--- | :--- | :--- |
| **University Admin** | Dr. Farhad Zahir | `admin.zahir` | `f.zahir@university.edu.af` | University Administration |
| **Registrar Admin** | Ahmad Fawad | `registrar.fawad` | `a.fawad@university.edu.af` | University Registrar Office |
| **Attendance Officer**| Maryam Haidari | `officer.maryam` | `m.haidari@university.edu.af` | Academic Affairs |
| **Compliance Auditor**| Sayed Mustafa | `auditor.mustafa` | `s.mustafa@university.edu.af` | Internal Audit Board |
| **Lecturer 1** | Prof. Ahmad Wali Ahmadzai | `lec.wali` | `ahmad.wali@university.edu.af` | Software Engineering |
| **Lecturer 2** | Dr. Mohammad Osman Hakimi | `lec.osman` | `m.osman@university.edu.af` | Software Engineering |
| **Lecturer 3** | Ms. Farida Sediqi | `lec.farida` | `farida.sediqi@university.edu.af` | Information Systems |
| **Lecturer 4** | Mr. Hekmatullah Popal | `lec.hekmat` | `hekmat.popal@university.edu.af` | Information Systems |
| **Student Cohort** | 60 Enrolled Students | `stu.2026.001` .. `060` | `stu2026XXX@university.edu.af` | Computer Science Cohort |

---

## 8. Pre-Pilot Backup & Controlled Rollback Runbook

### 8.1 Pre-Pilot Baseline Backup Execution
Before uploading any pilot data or initiating physical sessions, a verified database snapshot must be created:

```bash
# 1. Generate compressed, timestamped database snapshot
python scripts/backup_db.py

# Expected Output:
# [+] Backup completed successfully: backups/attendance_backup_20260917_104920Z.sql.gz
# [+] SHA256 Checksum: 460399e8ea26288056f36a4892e7cfb92a194dc27b6a1835b5b48d3fbbfe4b49
```

### 8.2 Controlled Maintenance-Window Rollback Procedure
If a blocker occurs during pilot execution requiring service restoration:
1. **Halt Intake:** Announce a temporary maintenance window; stop Caddy or block ingress.
2. **Preserve State:** Execute an immediate diagnostic dump of PostgreSQL, Redis keys, and container log files.
3. **Rollback Application:** Revert containers to the pre-pilot baseline image tags.
4. **Database Rollback / Restore:**
   ```bash
   # Option A: Versioned Alembic Downgrade (if clean schema rollback)
   docker compose -f docker-compose.prod.yml run --rm backend alembic -c backend/migrations/alembic.ini downgrade -1

   # Option B: Complete Database Restore (if data corruption occurred)
   python scripts/restore_db.py backups/attendance_backup_20260917_104920Z.sql.gz
   ```
5. **Health Verification:** Validate `/health/live` and `/health/ready` return HTTP 200 before reopening.

---

## 9. Pilot Stop Conditions

Field testing must immediately halt for the affected workflow if any of the following conditions arise:
1. **Attendance Record Corruption:** Any inconsistency between recorded evidence and finalized attendance records.
2. **Duplicate Checkpoint Credit:** Any student receiving more than one successful credit for a single checkpoint (INV-05 violation).
3. **Cross-Tenant Data Exposure:** Any tenant or department accessing records belonging to another academic unit.
4. **Cryptographic Key Leakage:** Exposure of signing keys in client logs, web responses, or URLs.
5. **Authentication Bypass:** Any route granting unauthorized access without valid bearer tokens.
6. **Fatal Mobile Crash Loops:** Unhandled exceptions preventing app launch across a device family.

*Preservation Mandate:* Under stop conditions, testers must NOT reinstall or clear application storage before diagnostic logs are captured.

---

## 10. Role Quick-Start & Practical Training Guides

### 10.1 University Administrator Quick-Start
1. **Login:** Navigate to `https://attendance.university.edu.af` and log in.
2. **Imports:** Navigate to **Administration -> Data Imports**.
3. **Batch Import:** Follow the 6-step sequential wizard: Courses -> Lecturers -> Students -> Offerings -> Enrollments -> Timetable.
4. **Review:** Ensure all staged rows show `VALID` before clicking **Commit Import**.
5. **Monitor:** Review real-time system status under **System Health**.

### 10.2 Lecturer Quick-Start
1. **Login:** Access console via web browser or mobile tablet.
2. **Today's Classes:** View assigned classes for the day on your dashboard.
3. **Start Session:** Select the active class occurrence and click **Start Attendance Session**.
4. **Display QR:** Click **Open Checkpoint**; project the rotating QR code onto the classroom screen.
5. **BLE Broadcast:** Verify the Bluetooth broadcasting indicator shows "Active".
6. **Live Roster:** Monitor student check-ins updating in real time.
7. **Manual Override:** For students unable to scan, tap their name, enter a brief justification (e.g. "Phone dead in room"), and submit.
8. **Close Session:** Tap **Close Checkpoint** and **End Session**. View the finalized attendance summary.

### 10.3 Student Quick-Start
1. **Install App:** Open the Attendance App on your Android device.
2. **Login & Password Change:** Log in with your temporary student credentials; choose a new secure password.
3. **Register Device:** Tap **Register Device** to bind your phone's secure hardware to your profile.
4. **Check In:** Point your camera at the lecturer's screen to scan the QR code.
5. **Confirm Presence:** Verify the screen displays "حاضر / Attendance Confirmed".
6. **Absence Excuse:** If absent due to illness, open **My Attendance**, tap the missed session, attach your medical note, and submit.

### 10.4 Attendance Officer Quick-Start
1. **Login:** Navigate to **Attendance Review Center**.
2. **Review Queue:** Review pending absence excuses and device replacement requests.
3. **Document Inspection:** Inspect student-submitted medical certificates or letters.
4. **Approve / Reject:** Enter review comments and click **Approve** (updates to `EXCUSED`) or **Reject**.
5. **Audit Ledger:** View the immutable timeline to verify actor attribution.

---

## 11. Privacy & Surveillance Transparency Briefing

To foster trust among students and faculty, the pilot briefing explicitly clarifies system boundaries:
- **No Continuous GPS Tracking:** The system NEVER captures, stores, or queries GPS coordinates.
- **No Biometric Photo Harvesting:** No facial recognition, fingerprint scanning, or camera feeds are sent to the server.
- **No Permanent Hardware MAC / IMEI Tracking:** The system does NOT use hardware MAC addresses or IMEI numbers for identity.
- **Cryptographic Device Binding:** Devices are identified solely via an application-generated Ed25519 public key in hardware-backed storage.
- **Local Network Verification:** Presence is validated by server-observed campus IP address and local Bluetooth beacon broadcast.
- **Transparent Audit:** All manual overrides and status changes are permanently attributed and visible to auditors.

---

## 12. Measurement & Data Collection Protocol

During Part 2 execution, the following metrics will be empirically collected and recorded in `pilot/evidence/`:
1. **Scan Latency:** Time in milliseconds from camera focus to server attendance confirmation.
2. **BLE Detection Range & RSSI:** Measured decibels (-dBm) at 2m, 5m, 10m, and 15m intervals across rooms.
3. **High-Density Throughput:** Successful check-ins per second during 100+ student burst windows.
4. **Offline Synchronization Duration:** Time required to reconcile an offline batch upon Wi-Fi reconnection.
5. **Incident Resolution Time:** Mean time to identify, mitigate, and retest pilot-discovered issues.

---

## 13. Baseline Software Check & Verification

Prior to Part 1 completion, the following software baselines were validated:
- **Git Commit Baseline:** `29c68ce` (Known green `main` with 9/9 GitHub Actions CI jobs passing, Run ID: `35210532701`).
- **Database Schema Migration:** Head `014_perf_hardening` with zero schema drift.
- **Pre-Pilot Backup Archive:** `attendance_backup_20260917_104920Z.sql.gz` (SHA256: `460399e8ea26288056f36a4892e7cfb92a194dc27b6a1835b5b48d3fbbfe4b49`).
- **Automated Test Matrix:** Fast-testing suite passes 100% across backend, web, and mobile.
