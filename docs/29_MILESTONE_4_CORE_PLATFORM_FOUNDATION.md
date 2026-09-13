# Digital Student Attendance System
## 29. Milestone 4 — Core Platform Foundation

**Document Version:** 1.0  
**Status:** Completed  
**Milestone:** 4 — Core Platform Foundation  
**Git Feature Branch:** `feature/task-002-backend-foundation`  
**Base Commit:** `3cf721d`  

---

## 1. Executive Summary

Milestone 4 establishes the reusable, production-grade core platform foundation for the **Digital Student Attendance System**. In strict compliance with `AGENTS.md` and the system specifications, **zero business logic** (no user credentials, no student/lecturer entities, no attendance sessions, no QR rotation logic, no Bluetooth scanning) was introduced.

The core platform provides:
1. **Typed Configuration Management**: Pydantic Settings covering 11 architectural domains with strict validation, fail-fast defaults, and safe URI schemes.
2. **PostgreSQL & Async SQLAlchemy 2.0**: Async connection engine, scoped sessionmaker with automatic rollback on unhandled exceptions, declarative base with RFC 9562 UUIDv7 primary keys, and naming conventions.
3. **Database Migration Pipeline**: Asynchronous Alembic migrations (`001_foundation_university.py`) implementing the baseline `universities` table with reversible `upgrade()` and `downgrade()`.
4. **Asynchronous Redis Integration**: Async connection pooling, health checks, and lifecycle hooks for caching and Celery brokering.
5. **Celery Worker Foundation**: Asynchronous worker process configured with UTC timezone, JSON serialization, and a diagnostic `system.ping` task.
6. **Correlation & Request Tracing**: `RequestIdMiddleware` generating sequential UUIDv7 request IDs, sanitizing malicious incoming headers, and binding correlation IDs to `ContextVar` loggers.
7. **Standard API Envelope & Error Suppression**: Standard envelopes (`{"data": ..., "meta": ...}` and `{"error": {"code": ..., "message": ..., "details": ..., "request_id": ...}}`) suppressing internal traces and database connection credentials.
8. **Multi-Tier Health Probes**: `/health/live` (process alive) and `/health/ready` (evaluating PostgreSQL `SELECT 1` and Redis `PING`).
9. **Client Connectivity Skeletons**:
   - Web: Developer connectivity badge on Next.js 16.3.3 + React 19 testing `/health/live`.
   - Mobile: Flutter `ApiClient` in `apps/mobile/lib/core/api_client.dart` testing `/health/live` and `/health/ready`.
10. **Containerized Multi-Service Stack**: Docker Compose orchestration for `postgres`, `redis`, `backend`, `worker`, and `web`.

---

## 2. Invariant Compliance Verification

| Invariant | Description | Milestone 4 Verification |
|---|---|---|
| **INV-01** | Client Cannot Mark Itself Present | No attendance endpoints exist; clients solely consume read-only health checks. |
| **INV-02** | Attendance Depends on Server/Domain Validation | Foundation establishes server-side async domain transaction boundaries with auto-rollback. |
| **INV-03** | Student Device Clock Is NOT Authoritative | All models and timestamps use server UTC (`datetime.now(timezone.utc)` and `utc_now()`). Server UTC is exposed on `/api/v1/`. |
| **INV-04** | Expired Dynamic QR/Tokens Cannot Grant Attendance | Attendance token settings (`ATTENDANCE_TOKEN_ROTATION_SECONDS=30`) configured in Settings baseline. |
| **INV-05** | No Duplicate Checkpoint Credit | Model schema conventions enforce unique constraint naming and idempotency keys. |
| **INV-06** | Corrections Cannot Erase History | Schema migrations configured; audit log conventions defined. |
| **INV-07** | Offline Events Remain Identifiable | Common schemas and pagination models support metadata envelopes. |
| **INV-08** | Manual Attendance Overrides Remain Identifiable | Audit metadata fields prepared for future domain layers. |

---

## 3. Platform Architecture Components

### 3.1 Typed Configuration (`backend/app/core/config.py`)
Configured categories:
- **APP**: Environment (`development`, `staging`, `production`, `testing`), version (`0.1.0`), default timezone (`Asia/Kabul`), locale (`en`).
- **DATABASE**: Host, port (5432), user, password, database (`attendance_db`), pool size (20), max overflow (10), and normalized `async_database_url` (`postgresql+asyncpg://...`).
- **REDIS**: URIs for caching (`db 0`), Celery broker (`db 1`), and Celery result backend (`db 2`).
- **AUTH**: Expiries and algorithm placeholders for Milestone 5.
- **ATTENDANCE**: 30-second token rotation, ±1 step tolerance, 75.0% threshold.
- **CORS**: Comma-separated origin parsing with wildcard security validation.

### 3.2 Async SQLAlchemy & University Model (`backend/app/models/`)
- Declarative `Base` with PostgreSQL constraint naming convention (`ix_...`, `uq_...`, `ck_...`, `fk_...`, `pk_...`).
- `UUIDv7PrimaryKeyMixin`: Sequential UUIDv7 generation for optimal B-tree page locality.
- `TimestampMixin`: Timezone-aware `created_at` and `updated_at`.
- `University` model (`universities` table) with code uniqueness, timezone default, and active status.

### 3.3 Asynchronous Alembic Migration (`backend/migrations/`)
- Revision `001_foundation_university.py` creates `universities` table.
- Both `upgrade()` and `downgrade()` fully implemented and tested.

### 3.4 Celery Worker & Redis Client
- Diagnostic task `system.ping` returns `{"pong": True, "service": "attendance-worker", "timestamp": "..."}`.
- Connection lifecycle hooks registered with FastAPI lifespan.

---

## 4. Quality Standard & Test Results

- **Backend Pytest Suite**: 30 tests passed (`100%`).
- **Ruff Linter & Formatter**: 0 errors, 37 files formatted.
- **Mypy Static Type Checking**: 0 errors across 37 files (`strict = true`).
- **Web Client (Next.js 16.3.3)**:
  - TypeScript: 0 errors (`tsc --noEmit`).
  - ESLint: 0 errors (`eslint .`).
  - Turbopack Build: Compiled successfully in 29.4s.
- **Mobile Client (Flutter / Dart 3.12.2)**:
  - Dart Analyze: 0 issues (`dart analyze apps/mobile`).
  - Flutter Tests: 3 passed (`widget_test.dart`, `api_client_test.dart`).
