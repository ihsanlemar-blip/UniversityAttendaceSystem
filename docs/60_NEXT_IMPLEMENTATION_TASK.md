# Next Implementation Task: Milestone 20 — MVP / Production v1.0 Release

**Task Identifier:** `TASK-018`  
**Milestone:** 20 — MVP / Production v1.0 Release  
**Status:** Ready for Execution  
**Pre-requisite:** Milestone 19 (University Pilot & Acceptance) completed, conditionally accepted, and merged to `main`.  
**Applies to:** Release Engineers, DevSecOps, Campus IT Administrators, and System Architects.  

---

## 1. Milestone Vision & Release Objective

Milestone 20 represents the final phase of the Digital Student Attendance System implementation: the **MVP / Production v1.0 Release**.

Having completed full software implementation (M1–M17), hardened production security, offline persistence, and deployment topology (M18), and successfully verified all domain workflows, registrar pipelines, and administrative operations in the university pilot (M19), Milestone 20 executes the formal go-live process:

> [!IMPORTANT]
> **Milestone 20 Scope Boundary:**
> 1. Complete production release packaging and configuration.
> 2. Execute on-site physical hardware commissioning to review and resolve the 12 non-critical pilot limitations.
> 3. Perform production deployment rehearsal under live university network infrastructure.
> 4. Author formal release notes, operator runbooks, and disaster recovery sign-off.
> 5. Apply the official `v1.0.0` release tag upon final quality gate closure.

---

## 2. Milestone 20 Implementation Workstreams

### Workstream 1: Release Packaging & Configuration
- **Production Environment Hardening:**
  - Enforce all production environment variables defined in `.env.production.example`.
  - Configure university-issued production cryptographic keys (JWT signing, Ed25519 root keys) via secure vault/secrets management.
  - Pin trusted reverse proxy CIDRs (`TRUSTED_PROXY_CIDRS`) and metrics monitoring CIDRs (`METRICS_ALLOWED_CIDRS`).
- **Domain & TLS Binding:**
  - Provision and install official university X.509 TLS certificate for `attendance.university.edu.af`.
  - Configure Caddy 2 ingress with strict HSTS, CSP, and reverse proxy timeouts.

### Workstream 2: Physical Hardware Commissioning (Review 12 Blocked Tests)
- **Classroom BLE Beacons (Group A):**
  - Install physical BLE transmitter beacons in Rooms A, B, and C.
  - Validate mobile app BLE advertisement detection within classroom boundaries (tests `G-A01` through `G-A07`).
  - Confirm -85 dBm signal boundary and concrete wall RF attenuation.
- **Optical Projection & Usability (Groups F & M):**
  - Verify projector scanning at 4m and 6m distances under varied classroom ambient lighting (tests `G-M04`, `G-M05`, `G-F08`).
  - Verify physical campus Wi-Fi AP subnet detection (`G-M01`) and local split-horizon DNS resolution (`G-M06`).

### Workstream 3: Production Deployment Rehearsal & Smoke Testing
- **Deployment Execution:**
  - Deploy full production composition via `docker-compose.prod.yml` on the official university host.
  - Verify container healthchecks, non-root user execution (`appuser:10001`, `nextjs:1001`), and network segregation.
- **Automated Smoke Tests:**
  - Execute end-to-end HTTP smoke tests against public and internal endpoints:
    - `GET /health/live` -> HTTP 200 OK
    - `GET /health/ready` -> HTTP 200 OK (PostgreSQL & Redis connected)
    - `GET /metrics` -> HTTP 403 Forbidden (from untrusted ingress)
    - `POST /api/v1/auth/login` -> Authenticates and returns JWT
    - Mobile & Web static asset delivery over HTTPS.

### Workstream 4: Documentation, Runbooks & Stakeholder Sign-Off
- **Documentation Deliverables:**
  - `docs/RELEASE_NOTES_v1.0.md`: Release notes highlighting features, architecture, and security properties.
  - `docs/OPERATOR_RUNBOOK.md`: Day-2 operations guide (backup/restore, user provisioning, rotation procedures, log inspection).
  - `docs/INCIDENT_RESPONSE_PLAYBOOK.md`: Disaster recovery, rollback procedures, and emergency override protocols.
- **Sign-off Criteria:**
  - All CI shards passing on `main`.
  - Static analysis clean across Python, TypeScript, and Dart.
  - University registrar and IT administrator acceptance signatures.
  - Creation and verification of signed Git release tag: `v1.0.0`.

---

## 3. Pre-Requisite Baseline State

Prior to initiating Milestone 20 tasks, verify that the repository state matches:
- **Git Branch Baseline:** `main` updated with Milestone 19 merge.
- **Database Schema Head:** `014_perf_hardening` with zero schema drift.
- **Post-Pilot Verified Backup:** `backups/attendance_backup_20260917_114045Z.sql.gz`.
- **CI Status:** 9/9 parallel GitHub Actions jobs green.
