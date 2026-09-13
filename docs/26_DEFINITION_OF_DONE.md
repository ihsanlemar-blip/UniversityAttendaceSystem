# Digital Student Attendance System
## Definition of Done (DoD)

**Document Version:** 1.0  
**Status:** Approved Quality Standard  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Quality Principle

> [!IMPORTANT]
> A feature is **NOT** done merely because the user interface renders or a happy-path test passes.
> In a mission-critical university attendance system, "Done" means the feature is secure, auditable, performant, resilient to offline conditions, localized, and architecturally compliant.

---

## 2. The 14-Point Definition of Done Checklist

Every feature, enhancement, or bug fix must satisfy all applicable criteria before being merged into `main`:

### 1. Requirements & Acceptance Criteria
- [ ] All functional requirements specified in the task description and PRD are fully implemented.
- [ ] Acceptance criteria defined in the Epic backlog are demonstrably satisfied.

### 2. Architectural Preservation
- [ ] Conforms strictly to the approved baseline: Modular monolith, FastAPI, PostgreSQL, Redis, Celery, Next.js, Flutter.
- [ ] Zero unapproved architectural changes introduced (no microservices, no GraphQL, no cloud-mandatory services).
- [ ] Server remains the sole operational authority; client never marks itself "Present".

### 3. Automated Tests Added
- [ ] Unit tests added for all new business logic and service methods.
- [ ] API integration tests added covering happy path, validation errors, and unauthorized access.
- [ ] Negative and edge cases tested (e.g., token expiration, duplicate submissions, network dropouts).

### 4. Tests Passing & Coverage
- [ ] 100% of automated tests pass in the local development environment and CI.
- [ ] Backend test coverage meets or exceeds the project threshold (minimum 85% branch coverage).

### 5. Server-Side Authorization Enforced
- [ ] Endpoints verify caller identity via JWT access token.
- [ ] Granular permission checks enforced server-side (`require_permission(...)`).
- [ ] Scoped access verified (e.g., Lecturer can only access assigned sections; Dean can only access faculty data).

### 6. Strict Input Validation & Schemas
- [ ] All request bodies, query parameters, and headers validated with Pydantic v2 schemas.
- [ ] Standard API response envelope `{"data": ..., "error": null}` used consistently.
- [ ] No unhandled exceptions; business errors mapped to domain error codes.

### 7. Database Migration & Schema Integrity
- [ ] Schema changes implemented via versioned Alembic migration script.
- [ ] Both `upgrade()` and `downgrade()` functions tested and verified.
- [ ] Appropriate database constraints (foreign keys, uniqueness, check constraints, indexes) in place.
- [ ] Zero manual SQL modifications applied to production or test environments.

### 8. Audit Logging Integrated
- [ ] State-changing actions (session start/close, manual attendance overrides, corrections) emit audit events.
- [ ] Audit payload records actor ID, timestamp in UTC, entity affected, before state, and after state.
- [ ] Historical records and audit logs remain immutable.

### 9. Offline Resilience Considered
- [ ] Network interruption handled gracefully without application crash.
- [ ] Idempotency keys used for retry-sensitive API writes.
- [ ] Offline evidence labeled appropriately (`OFFLINE_CAPTURED`, `SYNC_PENDING`).

### 10. Comprehensive Error Handling
- [ ] User-facing error messages are clear, constructive, and free of raw stack traces or database errors.
- [ ] Retry logic implemented where appropriate with exponential backoff.

### 11. Localization & RTL Layout Support
- [ ] Web and mobile UI strings externalized into localization files.
- [ ] RTL (Right-to-Left) layout verified for Dari and Pashto translations.
- [ ] Numbers and dates formatted using university timezone and locale conventions.

### 12. Documentation & API Contracts Updated
- [ ] OpenAPI specification updated (`contracts/openapi.json`).
- [ ] Architectural docs in `docs/` updated if domain rules or flows were refined.
- [ ] Inline code docstrings provided for public service functions and domain models.

### 13. CI & Static Analysis Green
- [ ] Code formatting clean (`ruff format`, `Prettier`, `dart format`).
- [ ] Linters clean (`ruff check`, `ESLint`, `flutter analyze`).
- [ ] Type checkers clean (`mypy`, TypeScript strict mode).
- [ ] GitHub Actions CI workflow passes with zero warnings.

### 14. Zero Security & Secret Issues
- [ ] Automated secret scan detects zero committed credentials, tokens, or private keys.
- [ ] OWASP Top 10 vulnerabilities (injection, broken access control, SSRF) verified absent.
- [ ] No debug endpoints or sensitive data exposed in public responses.
