# Digital Student Attendance System
## First Implementation Task — Milestone 4 Handoff

**Document Version:** 1.0  
**Status:** Ready for Milestone 4 Execution  
**Task ID:** `TASK-002 — Backend Application Foundation`  
**Milestone:** 4 (Preparation & Scope Boundary)  

---

> [!WARNING]
> **HANDOFF BOUNDARY**: This task specification is prepared as the formal entry point for Milestone 4.
> **DO NOT EXECUTE THIS TASK DURING MILESTONE 3.**
> Only prepare and review this task definition. Implementation begins only upon explicit approval to initiate Milestone 4.

---

## 1. Task Objective

Establish the foundational backend architecture for the FastAPI modular monolith application, including:
1. Pydantic v2 application settings loaded from `.env`.
2. Async SQLAlchemy 2.0 database engine and scoped sessionmaker connected to PostgreSQL.
3. Asynchronous Alembic database migration environment with initial foundation migration (`001_foundation_university`).
4. Redis connection pool manager and caching client.
5. Standard API response envelope (`{"data": ..., "error": null}`) and global exception handlers.
6. Structured JSON logger with request correlation IDs.
7. Pytest test suite with async test database fixtures.

---

## 2. Mandatory Reading Before Implementation

The engineer or AI agent implementing this task must read:
- `docs/07_SYSTEM_ARCHITECTURE.md`
- `docs/08_DOMAIN_MODEL.md`
- `docs/09_DATABASE_SCHEMA.md`
- `docs/13_AGENT_DEVELOPMENT_RULES.md`
- `docs/15_ARCHITECTURE_DECISIONS.md` (specifically ADR-001, ADR-004, ADR-005, ADR-006, ADR-019)
- `docs/20_ENVIRONMENT_CONFIGURATION.md`
- `docs/23_DATABASE_MIGRATION_PLAN.md`
- `docs/25_AGENT_TASK_PLAYBOOK.md` (Template 2.1 & 2.2)
- `docs/26_DEFINITION_OF_DONE.md`

---

## 3. Allowed Files to Change

The agent or engineer implementing this task may **only** create or modify files within:
```text
backend/app/core/
backend/app/common/
backend/app/main.py
backend/migrations/
backend/tests/
backend/requirements.txt
backend/pyproject.toml
```

**Forbidden Modifications:**
- Do not modify `apps/web/` or `apps/mobile/`.
- Do not implement authentication, user models, attendance models, or business logic.
- Do not modify files in `docs/` or `archive/`.

---

## 4. Detailed Acceptance Criteria

1. **Settings Management**:
   - Strongly typed `Settings` class in `backend/app/core/config.py` inheriting from `pydantic_settings.BaseSettings`.
   - Validates database URL, Redis URL, application environment, and timezone (`Asia/Kabul` default).
2. **Database Engine**:
   - Async engine configured using `asyncpg` driver in `backend/app/core/database.py`.
   - Reusable `get_db_session` dependency providing scoped async sessions.
3. **Migration Infrastructure**:
   - Alembic initialized in `backend/migrations/` configured for async SQLAlchemy models.
   - Initial migration `001_foundation_university.py` creates `universities` table matching `docs/09_DATABASE_SCHEMA.md`.
   - Migration successfully executes `upgrade()` and `downgrade()` in PostgreSQL.
4. **Redis Integration**:
   - Connection pool initialized on application startup and closed gracefully on shutdown lifespan hook.
   - Ping check integrated into readiness probe `/health/ready`.
5. **Standard API Envelope**:
   - Standard response structure `{"data": ..., "error": null}` and error structure `{"data": null, "error": {"code": "...", "message": "...", "details": ...}}`.
   - Global exception handler maps `DomainException` to appropriate HTTP status codes without exposing internal tracebacks.
6. **Logging**:
   - Structured JSON logs emitted to `stdout` containing timestamp (UTC), log level, message, and `request_id`.

---

## 5. Required Automated Tests

1. `test_settings_loading`: Verify configuration correctly loads defaults and environment overrides.
2. `test_database_connection`: Verify async session executes `SELECT 1` against PostgreSQL test database.
3. `test_redis_connection`: Verify Redis client performs `set` and `get` operations.
4. `test_health_readiness_probe`: Verify `/health/ready` returns HTTP 200 with component statuses (`database: "ok"`, `redis: "ok"`).
5. `test_migration_up_and_down`: Automated test applying Alembic migration up and down cleanly.
6. `test_exception_envelope`: Verify uncaught domain exception formats into standard error envelope.

---

## 6. Security Invariants & Restrictions

- No hardcoded passwords, tokens, or private keys in settings or test files.
- Database passwords must be loaded strictly from environment variables.
- Raw SQL queries are prohibited; use SQLAlchemy 2.0 select statements.
- Stack traces must never be exposed to API callers in production mode.

---

## 7. Definition of Done Checklist for TASK-002

- [ ] Requirements 1 through 6 demonstrably satisfied.
- [ ] Alembic migration `001_foundation_university` runs cleanly up and down.
- [ ] All unit and integration tests pass (`pytest backend/tests`).
- [ ] Code formatted with `ruff format`.
- [ ] Linter passing with zero warnings (`ruff check`).
- [ ] MyPy static type checking passing with zero errors.
- [ ] No unrelated files modified.
