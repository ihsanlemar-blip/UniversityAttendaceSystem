# Next Implementation Task: Milestone 18 — Security, Performance & Deployment Hardening

**Status:** Planned / Up Next (Do NOT implement in Milestone 17 task)  
**Applies to:** Next Coding Agent Milestone Handoff  
**Quality Standard:** [docs/26_DEFINITION_OF_DONE.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/26_DEFINITION_OF_DONE.md)  

---

## 1. Task Objective

Execute **Milestone 18: Security, Performance & Deployment Hardening** for the Digital Student Attendance System. Milestone 18 takes the fully localized, accessible, and verified MVP system delivered across Milestones 1 through 17 and hardens it for high-concurrency university campus production deployment.

---

## 2. Invariants & Guardrails (Mandatory)

1. **Do NOT Alter Domain Invariants**:
   - Client cannot mark itself present; authoritative UTC server clock sole authority.
   - Dual-factor token/BLE verification rules remain inviolable.
   - Append-only immutable audit ledgers and revision history remain protected.
2. **Preserve Database Schema Integrity**:
   - Zero unauthorized schema changes. Any indexing or performance tuning must use explicit, reversible Alembic migrations.
3. **Preserve Fast Testing & CI Matrix**:
   - Maintain 4-shard GitHub Actions test runner with real PostgreSQL 16 and Redis 7 service containers.
   - Zero real-world sleeps (`time.sleep` / `asyncio.sleep`).
4. **No Premature Architecture Redesign**:
   - Do NOT introduce microservices, GraphQL, MongoDB, or Firebase.
   - Adhere strictly to FastAPI + PostgreSQL + Redis + Next.js + Flutter.

---

## 3. Anticipated Milestone 18 Scope

1. **Security Hardening**:
   - Rate limiting and throttling across public and sensitive endpoints (`/api/v1/auth/*`, `/api/v1/attendance/checkin/*`).
   - Strict CORS policies and Content Security Policy (CSP) headers.
   - Penetration testing defenses against token replay, brute force, and session hijacking.
2. **Performance Benchmarking & Optimization**:
   - High-concurrency load testing for dynamic QR rotation (500+ simultaneous scans per second).
   - Database query optimization, connection pooling configurations (PgBouncer compatibility), and query plan validation.
   - Redis cache invalidation strategies and memory profiling.
3. **Mobile Offline Storage Migration**:
   - Safely migrate mobile offline storage from the current atomic JSON store (`apps/mobile/lib/core/offline/offline_storage.dart`) to **Drift/SQLite** with encrypted storage and database migrations prior to campus pilot.
4. **Production Infrastructure & Container Profiling**:
   - Production multi-stage Dockerfiles with non-root security profiles.
   - Docker Compose production configuration with health checks, log rotation, and automated volume backups.
   - SSL/TLS termination, reverse proxy configuration (Nginx / Caddy), and certificate management.
5. **Monitoring & Observability**:
   - Structured JSON logging with correlation IDs.
   - Prometheus metrics exporter and Grafana dashboard templates for attendance throughput and BLE verification ratios.
6. **Physical & Field Pilot Readiness Checklist**:
   - Pilot deployment runbook and checklist for campus IT administrators.
   - Preparation for the 6 outstanding physical/manual acceptance gates required before University Pilot (Milestone 19):
     1. M11 BLE physical-device acceptance
     2. M12 offline field/device acceptance
     3. M13 device registration/replacement acceptance
     4. M15 attendance operations workflow acceptance
     5. M16 import/report workflow acceptance
     6. M17 end-to-end MVP UX acceptance

---

> [!WARNING]
> Do NOT begin implementation of Milestone 18 in this session. Milestone 17 must first complete all verification gates, CI runs, merge to `main`, and achieve formal sign-off.
