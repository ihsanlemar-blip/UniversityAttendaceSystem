# Milestone 19 — University Pilot Execution Evidence

- **Execution Date:** 2026-09-17T11:37:31.938268+00:00
- **Total Tests:** 54
- **PASS:** 42
- **FAIL:** 0
- **BLOCKED:** 12 (Zero Fabrication: awaiting physical campus hardware)
- **NOT RUN:** 0

| Test ID | Group | Title | Status | Evidence Summary |
| :--- | :--- | :--- | :--- | :--- |
| **G-E01** | IMPORTS | Registrar Courses Catalog CSV Import & Commit | `PASS` | 5 courses staged, preview non-mutation verified, committed to database |
| **G-E02** | IMPORTS | Registrar Lecturers Profiles CSV Import & Commit | `PASS` | 4 lecturers created with default accounts, department linkage verified |
| **G-E03** | IMPORTS | Registrar 60-Student Cohort CSV Import & Dari/Pashto Script | `PASS` | 60 students committed; authentic Afghan Unicode names preserved without corruption |
| **G-E04** | IMPORTS | Course Offerings & 60-Student Class Roster Enrollments | `PASS` | 5 offerings committed; 60 enrollments assigned across FALL-2026 courses |
| **G-E05** | IMPORTS | Weekly Recurring Timetable Schedule Import | `PASS` | 5 recurring timetable schedules committed for Rooms A, B, and C |
| **G-E06** | IMPORTS | Malformed CSV & Extension Validation Defense | `PASS` | Malformed schema and missing mandatory headers detected; production protected |
| **G-E07** | IMPORTS | CSV Spreadsheet Formula Injection Sanitization | `PASS` | Dangerous payload sanitized to: '=cmd|' /C calc'!A0 |
| **G-E08** | IMPORTS | Official Attendance Report Export (CSV/XLSX) | `PASS` | Official department roster CSV generated (434 bytes) with UTF-8 BOM |
| **G-C01** | DEVICE_TRUST | First Mobile Device Hardware Binding & Key Generation | `PASS` | Device ID e97e52de-4919-4176-92c1-f7f1c6af1010 registered; status=ACTIVE; bound to student STU-2026-001 |
| **G-C02** | DEVICE_TRUST | Single-Device Binding Enforcement (Reject Unregistered) | `PASS` | Secondary unverified device fingerprint rejected; single-device invariant upheld |
| **G-C03** | DEVICE_TRUST | Device Replacement Request with Justification | `PASS` | Replacement request e60b882c-589f-4b38-be5b-db885becbda3 queued with status PENDING |
| **G-C04** | DEVICE_TRUST | Administrator Device Replacement Approval & Old Key Revocation | `PASS` | Old device e97e52de-4919-4176-92c1-f7f1c6af1010 REVOKED; replacement request marked APPROVED |
| **G-C05** | DEVICE_TRUST | Post-Approval Replacement Device Binding | `PASS` | Replacement device 3c0919f7-4ff1-4e3c-809b-f3ab57e44d65 bound and ACTIVE; student ready for attendance |
| **G-C06** | DEVICE_TRUST | Device Replacement Frequency Rate Limit & Anti-Cheat Flag | `PASS` | Replacement velocity monitored; threshold limit (2 per 30 days) enforced |
| **G-D01** | OPERATIONS | Lecturer Live Session Start & Class Occurrence Lifecycle | `PASS` | Attendance session 01a0af28-5019-75ef-ae50-391fe9716ecf ACTIVE; frozen roster initialized |
| **G-D02** | OPERATIONS | Dynamic QR Scan & Real-Time Verified Attendance Credit | `PASS` | Check-in verified; evidence_id=01a0af28-5109-7421-bbeb-90a26c974fd0; factor=QR; student STU-2026-001 credited |
| **G-D03** | OPERATIONS | Manual Roll-Call Override with Audit Justification (INV-08) | `PASS` | Student STU-2026-002 marked PRESENT via MANUAL override; actor=lec_001 |
| **G-D04** | OPERATIONS | Student Absence Excuse Submission & Medical Attachment | `PASS` | Medical excuse 01a0af28-5235-750c-8819-68b764e59ce4 submitted for occurrence 01a0af28-4f82-764a-9893-9e7a6e9d4b06 |
| **G-D05** | OPERATIONS | Attendance Officer Excuse Review & Status Approval | `PASS` | Excuse approved by officer.maryam; occurrence status converted to EXCUSED |
| **G-D06** | OPERATIONS | Attendance Officer Excuse Rejection Workflow | `PASS` | Excuse 01a0af28-527b-7273-90ce-2c9e7494e046 rejected with documented explanation; absence maintained |
| **G-D07** | OPERATIONS | Post-Session Attendance History & Audit Trail Immutability (INV-06) | `PASS` | 6 immutable audit ledger events recorded; historical entries intact |
| **G-B01** | OFFLINE | Lecturer Cryptographic Offline Permit Issuance | `PASS` | Permit 2d448b9c-d185-4ad4-ba7c-7b848f9ba880 issued with Ed25519 digital signature; validity=8h |
| **G-B02** | OFFLINE | Offline Host Session Activation & QR Hash Chain | `PASS` | Offline host session 804736ad-e996-4e5d-b537-3edf7faeba8e activated; rotating offline QR enabled |
| **G-B03** | OFFLINE | Student Offline Claim Capture in SQLite Outbox | `PASS` | Claim captured into mobile SQLite sync outbox with status PENDING |
| **G-B04** | OFFLINE | Mobile SQLite Crash / Restart Durability | `PASS` | Claim survived simulated OS kill and database connection reopen |
| **G-B05** | OFFLINE | Device Reboot Durability & Persistent Storage | `PASS` | SQLite file persistence preserved all pending claim payloads across reboot cycle |
| **G-B06** | OFFLINE | Campus Network Reconnection & Batch Serialization | `PASS` | Offline claims aggregated into JSON sync batch (180 bytes) |
| **G-B07** | OFFLINE | Server Offline Reconciliation & Roster Evaluation | `PASS` | Offline claim e00f5b42-fb1c-47a5-bf97-b32bcbd6f111 reconciled against permit 2d448b9c-d185-4ad4-ba7c-7b848f9ba880; status=VERIFIED |
| **G-B08** | OFFLINE | Offline Reconciliation Dropped-ACK Idempotency (INV-05) | `PASS` | Reconciliation retry returned existing attendance credit without duplicate evidence insert |
| **G-B09** | OFFLINE | Tampered Claim Signature Rejection Defense | `PASS` | Tampered signature detected and rejected with cryptographic validation error |
| **G-B10** | OFFLINE | Expired Offline Permit Rejection Defense | `PASS` | Stale permit (>24h past expiration) rejected by offline verification engine |
| **G-F01** | UX | Student Mobile Onboarding & Password Reset Flow | `PASS` | Initial student credentials require mandatory first-login password change |
| **G-F02** | UX | Lecturer Web Session Flow & Dynamic QR Display | `PASS` | Lecturer console starts session, opens checkpoint, displays 20s rotating QR code |
| **G-F03** | UX | Dari (fa-AF) Localization Dictionary Integrity | `PASS` | Authentic Afghan Dari terminology verified in mobile and web translation sets |
| **G-F04** | UX | Pashto (ps) Localization Dictionary Integrity | `PASS` | Authentic Afghan Pashto terminology verified in mobile and web translation sets |
| **G-F05** | UX | RTL Layout Direction & Mirroring Validation | `PASS` | RTL layout direction enabled across Dari/Pashto locales; proper right-to-left UI alignment |
| **G-F06** | UX | Alphanumeric LTR Code Isolation in RTL UI | `PASS` | Course codes ('CS-101') and student IDs ('STU-2026-001') render in LTR without reversal |
| **G-F07** | SECURITY | Compliance Auditor Read-Only Enforcement (Zero Mutation) | `PASS` | Auditor mutation attempt rejected with HTTP 401 Forbidden |
| **G-M02** | SECURITY | External Subnet Rejection (Cellular / Non-Campus) | `PASS` | External client IP 198.51.100.77 identified; campus presence verification rejects non-campus range |
| **G-M03** | SECURITY | Direct Client Source IP Anti-Spoofing Defense | `PASS` | Spoofed header 10.100.1.50 ignored; direct peer IP 198.51.100.77 pinned; spoof_detected=True |
| **G-M07** | SECURITY | Internal Operational Metrics Endpoint Protection (/metrics) | `PASS` | Untrusted request rejected with HTTP 403; metrics protected |
| **G-M08** | INFRASTRUCTURE | Controlled Server Restart Recovery & State Durability | `PASS` | Active session and frozen roster state verified durable in PostgreSQL and Redis |
| **G-A01** | RADIO | Physical BLE Beacon Broadcast | `BLOCKED` | Requires physical classroom BLE broadcaster hardware |
| **G-A02** | RADIO | Student Mobile BLE Discovery | `BLOCKED` | Requires physical mobile devices in classroom |
| **G-A03** | RADIO | Multi-Device Bluetooth Compatibility | `BLOCKED` | Requires physical device models cohort |
| **G-A04** | RADIO | RSSI Boundary Calibration | `BLOCKED` | Requires physical distance markers & RF measurement |
| **G-A05** | RADIO | Concrete Wall RF Attenuation | `BLOCKED` | Requires physical 25cm reinforced concrete wall RF measurement |
| **G-A06** | RADIO | Adjacent-Room Isolation | `BLOCKED` | Requires physical adjacent rooms and transmitters |
| **G-A07** | RADIO | High-Density 100+ RF Congestion | `BLOCKED` | Requires 60-100 physical students and phones |
| **G-F08** | UX | Low-Cost Android UX & Contrast under Sunlight | `BLOCKED` | Requires physical phone screen testing under campus sunlight |
| **G-M01** | INFRASTRUCTURE | Campus Wi-Fi Subnet Verification | `BLOCKED` | Requires physical device associated with campus AP 10.100.1.50 |
| **G-M04** | OPTICS | QR Projector Low-Light Readability | `BLOCKED` | Requires physical 1080p classroom projector at 6m |
| **G-M05** | OPTICS | QR Projector Bright-Light Readability | `BLOCKED` | Requires physical classroom projector in sunlight |
| **G-M06** | INFRASTRUCTURE | Campus Local DNS Resolution | `BLOCKED` | Requires physical mobile device connected to campus Wi-Fi DHCP/DNS |
