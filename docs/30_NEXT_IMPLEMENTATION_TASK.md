# Digital Student Attendance System
## 30. Next Implementation Task — Milestone 5 Handoff

**Document Version:** 1.0  
**Status:** Ready for Milestone 5 Execution  
**Task ID:** `TASK-003 — Identity, Authentication & Role-Based Access Control`  
**Milestone:** 5 (Preparation & Scope Boundary)  

---

> [!WARNING]
> **HANDOFF BOUNDARY**: This task specification is prepared as the formal entry point for Milestone 5.
> **DO NOT EXECUTE THIS TASK DURING MILESTONE 4.**
> Implementation begins only upon explicit human approval to initiate Milestone 5.

---

## 1. Task Objective

Implement the complete user identity, authentication, session management, and role-based access control (RBAC) foundation for the Digital Student Attendance System, including:

1. **User and Credential Data Models**:
   - `users` (id, university_id, email, password_hash, full_name, role, status, failed_login_attempts, locked_until, created_at, updated_at).
   - `user_roles` (`SYSTEM_ADMIN`, `UNIVERSITY_ADMIN`, `FACULTY_DEAN`, `DEPARTMENT_HEAD`, `LECTURER`, `STUDENT`, `AUDITOR`).
   - `sessions` / `refresh_tokens` (revocation, device binding, expiry).
2. **Cryptographic Authentication**:
   - Argon2id password hashing via `passlib[argon2]`.
   - EdDSA or RS256/HS256 JWT access tokens (15-minute validity).
   - Refresh token rotation with reuse detection.
3. **RBAC Authorization Engine**:
   - Declarative permission dependencies (`require_permission`, `require_role`).
   - Tenant isolation ensuring users cannot query across `university_id` boundaries.
4. **Audit Logging**:
   - Immutable audit logging on login, failed attempts, and password modifications.
5. **Database Migration**:
   - Alembic migration `002_identity_auth_rbac.py` creating user and role tables.
6. **Integration Tests**:
   - End-to-end token issuance, verification, expiration, brute-force rate-limiting, and RBAC gate tests.

---

## 2. Mandatory Reading Before Implementation

The engineer or AI agent implementing Milestone 5 must inspect:
- `docs/01_PRODUCT_REQUIREMENTS_PRD.md` (Section 4 — User Roles & Permissions)
- `docs/08_DOMAIN_MODEL.md` (Section 3 — Identity & Access Subdomain)
- `docs/09_DATABASE_SCHEMA.md` (Section 2 — Authentication & Users Tables)
- `docs/10_API_SPECIFICATION.md` (Authentication Endpoints `/api/v1/auth/*`)
- `docs/13_AGENT_DEVELOPMENT_RULES.md`
- `docs/15_ARCHITECTURE_DECISIONS.md` (ADR-005, ADR-006, ADR-011, ADR-019)
- `docs/20_ENVIRONMENT_CONFIGURATION.md`
- `docs/26_DEFINITION_OF_DONE.md`

---

## 3. Allowed Files to Change in Milestone 5

```text
backend/app/auth/
backend/app/models/user.py
backend/app/models/session.py
backend/migrations/versions/002_identity_auth_rbac.py
backend/tests/test_auth.py
backend/tests/test_rbac.py
contracts/openapi/
```

**Forbidden Modifications in Milestone 5:**
- Do not implement academic structure (departments, courses, schedules).
- Do not implement attendance sessions, QR codes, or Bluetooth scanning.
- Do not alter the immutable audit ledger structure.
