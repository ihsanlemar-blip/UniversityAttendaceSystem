# Digital Student Attendance System
## Milestone 18 Manifest — Security, Performance & Deployment Hardening

**Generated At:** 2026-09-17  
**Feature Branch:** `feature/task-016-security-performance-deployment-hardening`  
**Milestone:** 18 — Security, Performance & Deployment Hardening  

---

## 1. Inventory of Files Created / Modified

### 1.1 Backend Core & Security
- `backend/app/core/config.py`: Added fail-closed production validators, connection pool timeout/recycle settings, cryptographic key separation rules, and metrics protection (`METRICS_ACCESS_KEY`, `METRICS_ALLOWED_CIDRS`).
- `backend/app/core/database.py`: Integrated connection pool timeout (`DATABASE_POOL_TIMEOUT`) and recycle (`DATABASE_POOL_RECYCLE`) into engine creation.
- `backend/app/core/security_headers.py`: Injected OWASP security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Cache-Control).
- `backend/app/security/rate_limiter.py`: Implemented Redis-backed sliding-window rate limiter with in-memory fallback and standard `Retry-After` HTTP headers.
- `backend/app/security/resolver.py`: Right-to-left reverse proxy IP resolution with CIDR whitelist verification and anti-spoofing protection.
- `backend/app/attendance/service.py`: Wrapped checkpoint credit writes in `try ... except IntegrityError:` with rollback and safe idempotency return under burst concurrency races.
- `backend/app/health/router.py` & `schemas.py`: Added `/health/metrics` and `/metrics` observability probes reporting uptime and database connection pool statistics, protected with `verify_metrics_access` authentication and CIDR subnet restrictions.
- `backend/app/models/attendance_checkpoint.py`, `attendance_evidence.py`, `attendance_record.py`, `class_occurrence.py`, `course_offering.py`, `enrollment.py`: Updated `__table_args__` with composite performance indexes matching Migration 014.
- `backend/migrations/versions/014_security_performance_deployment_hardening.py`: Alembic migration `014_perf_hardening` adding 6 composite indexes.

### 1.2 Mobile Offline Storage & Drift/SQLite Migration
- `apps/mobile/pubspec.yaml` & `pubspec.lock`: Added `sqlite3: ^3.5.2` and `path: ^1.9.0`.
- `apps/mobile/lib/core/offline/sqlite_offline_storage.dart`: Implemented SQLite offline database with typed tables (`storage_metadata`, `offline_permits`, `offline_host_events`, `offline_student_claims`, `sync_outbox`, `sync_conflicts`), account isolation by `user_id`, transactional outbox state machine, and zero-data-loss legacy JSON migration.
- `apps/mobile/lib/core/offline/offline_storage.dart`: Refactored to delegate cleanly to `SqliteOfflineStorage`.
- `apps/mobile/test/offline_attendance_test.dart`: Added 18 comprehensive tests covering SQLite tables, JSON migration, corrupt file quarantine, restart durability, crash simulations, and response-loss retry idempotency.

### 1.3 Web Client
- `apps/web/next.config.js`: Added security headers middleware and CSP configuration.
- Verified Next.js 16.3.3 standalone production build generation with 0 errors.

### 1.4 Production Infrastructure & Deployment
- `infra/docker/Dockerfile.backend.prod`: Multi-stage Dockerfile running non-root user `appuser:appgroup` (UID 10001), 4 Uvicorn workers, and container healthcheck.
- `infra/docker/Dockerfile.web.prod`: Multi-stage Next.js standalone Dockerfile running non-root user `nextjs:nodejs` (UID 1001).
- `docker-compose.prod.yml`: Production topology with network segregation (`internal_net` vs `public_net`), restart policies, resource limits, and health dependencies.
- `deploy/caddy/Caddyfile`: Reverse proxy configuration with automatic HTTPS, HSTS, security headers, 15MB upload body ceiling, and restricted access for `/metrics` and `/health/metrics` on public ingress.
- `docs/DEPLOYMENT_RUNBOOK.md`: Controlled upgrade and rollback procedures (maintenance window).
- `.env.production.example`: Complete environment variable template for production deployments.

### 1.5 Disaster Recovery & Performance Profiling
- `scripts/backup_db.py`: Gzip-compressed automated database backup with SHA-256 integrity checksum generation and 30-day retention pruning.
- `scripts/restore_db.py`: Database restoration script with pre-execution SHA-256 checksum verification and candidate Docker container detection.
- `backend/scripts/profile_workloads.py`: Database query benchmark across 6 core composite indexed query patterns.
- `backend/scripts/profile_representative_ops.py`: Empirical profiler measuring p50, p95, and max latencies across 10 representative university operations.

### 1.6 CI Sharding & Governance
- `.github/workflows/ci.yml`: Sharded 74 backend test suites across 4 parallel jobs with real PostgreSQL 16 and Redis 7 service containers (Shard 1: 21 suites, Shard 2: 17 suites, Shard 3: 12 suites, Shard 4: 24 suites).
- `scripts/audit_ci_shards.py`: Test partition auditor enforcing 0 missing and 0 duplicate test files across CI matrix.

---

## 2. Test Verification Summary

| Area | Test Suite / Check | Result |
| :--- | :--- | :--- |
| **Backend Security** | `test_security_hardening.py` (19 tests) | **PASSED** |
| **Burst Concurrency** | `test_performance_burst.py` (2 tests, 100 concurrent submissions) | **PASSED** (INV-05 verified) |
| **Backend Health** | `test_health.py` (6 tests) | **PASSED** |
| **Focused Regression** | M5, M9, M12, M13, M14, M15, M16 suites (44 tests) | **PASSED** |
| **Backend Linter** | `ruff check backend` | **PASSED** (0 issues) |
| **Backend Formatter** | `ruff format --check backend` | **PASSED** (247 files formatted) |
| **Backend Types** | `mypy backend` | **PASSED** (0 issues in 247 source files) |
| **Database Migration** | `alembic downgrade`, `upgrade`, `check` | **PASSED** (Head: 014_perf_hardening, Zero drift) |
| **Web Linter & Types** | `npm run lint` & `npm run type-check` | **PASSED** (0 errors) |
| **Web Build** | `npm run build` | **PASSED** (Next.js standalone build clean) |
| **Mobile Tests** | `flutter test` (all 87 tests) | **PASSED** (87 / 87) |
| **Mobile Linter** | `flutter analyze` & `dart format` | **PASSED** (0 issues) |
| **Backup / Restore** | `backup_db.py` & `restore_db.py` | **PASSED** (100% record fidelity verified) |
| **Python Audit** | `pip-audit` (68 backend packages) | **PASSED** (0 known vulnerabilities) |
| **Web Audit** | `npm audit` (apps/web) | **PASSED** (0 vulnerabilities) |
| **Mobile Dependency Audit**| `flutter pub outdated` (apps/mobile) | **PASSED** (0 security advisories, pinned) |
| **Secret Scan** | `python scripts/check_secrets.py` | **PASSED** (0 secrets found) |
| **CI Sharding Audit** | `python scripts/audit_ci_shards.py` | **PASSED** (74/74 sharded, 0 missing, 0 dupes) |

---

## 3. Commits on Feature Branch

1. `bed7abd`: `feat(m18): Milestone 18 Part 1 - production security hardening`
2. `83a9d27`: `feat(m18): migrate offline storage to Drift and harden performance and deployment`
3. `b7059c2`: `feat(m18): Milestone 18 Part 3 - final hardening, security verification, load validation, deployment acceptance, CI, documentation & sign-off`

---

## 4. Known Limitations & Milestone 19 Boundary

All software implementation for security, performance, offline storage, observability, and deployment is complete. However, the 6 physical acceptance gates cannot be completed without real physical classroom hardware and university pilot cohorts. They are carried over into **Milestone 19 — University Pilot & Acceptance**:
1. Physical BLE broadcaster field acceptance.
2. Physical offline device low-cost hardware field acceptance.
3. Student device biometric / passkey enrolment field acceptance.
4. Real lecture room attendance operations field acceptance.
5. Live registrar CSV/Excel import field acceptance.
6. Real cohort end-to-end UX usability acceptance.
