# Next Implementation Task: Milestone 19 — University Pilot & Acceptance

**Task Identifier:** `TASK-017`  
**Milestone:** 19 — University Pilot & Acceptance  
**Status:** Ready for Execution  
**Pre-requisite:** Milestone 18 (Security, Performance & Deployment Hardening) completed, fully tested, and merged to `main`.  
**Applies to:** Field engineers, QA leads, pilot coordinators, campus IT staff, and human evaluators.  

---

## 1. Milestone Vision & Objective

Milestone 19 transitions the Digital Student Attendance System from software readiness to **empirical operational validation** inside a live university environment.  

> [!IMPORTANT]
> Milestone 19 strictly focuses on **real-world physical validation, stakeholder acceptance, and operational stability**.  
> **NO new large software features or architectural deviations may be introduced during this milestone.**

---

## 2. The Six Mandatory Manual Field Acceptance Gates

Software implementations completed in Milestones 10 through 18 are subject to formal on-site sign-off via these six physical gates:

### Gate 1: BLE Device & Physical Field Acceptance
- Deploy physical BLE broadcaster beacons (or dedicated instructor broadcast units) across representative lecture halls.
- Verify that student mobile devices successfully discover broadcast packets, validate rotating BLE tokens, and record verified attendance within physical classroom bounds.
- Measure signal attenuation across concrete barriers and classroom perimeters to confirm anti-proxy containment.

### Gate 2: Offline Field & Network Partition Acceptance
- Conduct live lectures in lecture halls with zero Wi-Fi or cellular connectivity.
- Verify lecturer issuance of offline permits and local event hash chains.
- Verify students successfully scan offline dynamic tokens and write claims to local SQLite outbox.
- Reconnect devices to campus Wi-Fi and verify automatic, conflict-free server reconciliation with zero duplicate credits.

### Gate 3: Student Device Registration & Replacement Acceptance
- Enrol pilot student cohort (at least 50 students) across diverse Android hardware (Android 10 through 14) and iOS devices.
- Verify hardware cryptographic keypair generation and secure key storage in Keystore/Keychain.
- Execute controlled device replacement workflows (lost device simulation, admin approval, old key revocation, new device binding).

### Gate 4: Attendance Operations & Real-Time Monitoring Acceptance
- Conduct full-scale live lecture sessions with assigned course offerings and enrolled student rosters.
- Verify real-time roster state transitions (`PRESENT`, `LATE`, `ABSENT`).
- Execute manual roll-call overrides with mandatory audit justifications.
- Process absence excuse requests and administrative review queue workflows.

### Gate 5: Registrar Batch Import & Reporting Acceptance
- Registrar staff uploads real semester CSV/Excel schedules, courses, rooms, lecturers, and student rosters via the administrative import wizard.
- Verify preview validation catches formatting errors without mutating production data.
- Verify atomic batch commit and check-in readiness.
- Generate aggregated attendance reports and export official compliance spreadsheets.

### Gate 6: End-to-End MVP User Experience Acceptance
- Usability evaluation with native Dari, Pashto, and English speakers.
- Verify full RTL/LTR UI parity, typography rendering, accessibility contrast, and intuitive workflows across mobile and web consoles.

---

## 3. Pilot Deployment & Logistics Checklist

1. **Test Environment**:
   - Production Docker topology (`docker-compose.prod.yml`) deployed on university pilot server.
   - Caddy reverse proxy configured with university subdomain and valid SSL/TLS certificate.
   - Database initialized and migrated to latest head (`014_perf_hardening`).
2. **Participant Cohorts**:
   - Representative Students: Minimum 50-100 enrolled students across multiple faculties.
   - Representative Lecturers: Minimum 3-5 active instructors.
   - Administrative Staff: Minimum 2 registrars and department chairs.
3. **Hardware & Facilities**:
   - At least 2 real lecture rooms equipped with campus Wi-Fi access points and BLE broadcaster units.
   - Diversity of low-cost Android smartphones and iOS devices.
4. **Operational Artifacts**:
   - Pilot Incident Log: Tracking any connectivity drops, Bluetooth permission issues, or scan failures.
   - Stakeholder Feedback Log: Capturing user sentiment, UI clarity, and onboarding friction.
   - Daily automated backup verification (`scripts/backup_db.py`).

---

## 4. Acceptance Criteria for Milestone 19 Completion

1. All six manual field acceptance gates successfully executed and documented with sign-off records.
2. Zero data loss during offline operations or server restart.
3. Zero duplicate attendance credits granted under real classroom burst scans.
4. Pilot incident log resolved with zero high-severity open issues.
5. Formal pilot sign-off report authored and reviewed by university stakeholders.
