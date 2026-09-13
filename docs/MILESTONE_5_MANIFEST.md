# Digital Student Attendance System
## Milestone 5 Manifest — Identity, Authentication & Role-Based Access Control (Hardened)

**Generated At:** 2026-09-13  
**Feature Branch:** `feature/task-003-identity-auth-rbac`  
**Base Commit:** `81a04fd`  
**Milestones:** 5 (Core Implementation) & 5.1 (Authentication & RBAC Hardening)  

---

## 1. Inventory of Files Created / Modified

### 1.1 Core Configuration & System Constants (`backend/app/core/`)
- `backend/app/core/constants.py`: Extended with 8 canonical `SystemRole`s (`SUPER_ADMIN`, `UNIVERSITY_ADMIN`, `FACULTY_ADMIN`, `DEPARTMENT_ADMIN`, `ATTENDANCE_OFFICER`, `LECTURER`, `STUDENT`, `AUDITOR`), `ScopeType`, `UserStatus`, `RevocationReason`, `PermissionCode`.
- `backend/app/core/config.py`: Added `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_PASSWORD_MIN_LENGTH`, `AUTH_PASSWORD_MAX_LENGTH`, `AUTH_PASSWORD_REQUIRE_COMPOSITION`.
- `backend/app/common/pagination.py`: Reusable `PaginatedResponse.create()` factory method.

### 1.2 Data Models & Persistence (`backend/app/models/`)
- `backend/app/models/user.py`: `User` model with UUIDv7 PK, university binding, normalized unique email, password hash, failed attempt counter, lockout expiry, `must_change_password`, and `status`.
- `backend/app/models/role.py`: `Role` model with code, name, description, and `is_system` indicator.
- `backend/app/models/permission.py`: `Permission` model with code and description.
- `backend/app/models/role_permission.py`: `RolePermission` association table.
- `backend/app/models/role_assignment.py`: `RoleAssignment` model with tenant scope (`ScopeType.UNIVERSITY`, `scope_id`), assigned metadata, and soft revocation fields (`revoked_at`, `revoked_by`, `revocation_reason`).
- `backend/app/models/refresh_session.py`: `RefreshSession` model storing SHA-256 hashed refresh tokens, family UUIDs, replacement pointer (`replaced_by_id`), device/IP telemetry, and revocation status.
- `backend/app/models/login_attempt.py`: `LoginAttempt` model tracking historical login outcomes, internal failure reason, IP address, and user agent.
- `backend/app/models/audit_log.py`: `AuditLog` model for security event tracking.
- `backend/app/models/__init__.py`: Registered and re-exported all models.

### 1.3 Database Migration Pipeline (`backend/migrations/versions/`)
- `backend/migrations/versions/002_identity_users.py`: Alembic revision creating `users` table and indexes.
- `backend/migrations/versions/003_rbac.py`: Alembic revision creating `roles`, `permissions`, `role_permissions`, and `role_assignments` tables and indexes.
- `backend/migrations/versions/004_auth_sessions_attempts.py`: Alembic revision creating `refresh_sessions` (with self-referential FK) and `login_attempts` tables.

### 1.4 Cryptographic & Authentication Subsystem (`backend/app/auth/`)
- `backend/app/auth/passwords.py`: Argon2id hashing, verification, length-based policy validation (NIST SP 800-63B), whitespace rejection, optional composition checking, and automatic rehashing.
- `backend/app/auth/tokens.py`: Standards-compliant RFC 7519 JWT access token generation and decode with `sub`, `sid`, `university_id`, `roles`, `typ`, `jti`, `iat`, `nbf`, `exp`, `iss`, and `aud`.
- `backend/app/auth/security.py`: Secure random opaque refresh token generator and SHA-256 hash digest utility.
- `backend/app/auth/schemas.py`: Pydantic schemas for login, refresh, logout, password change, and current user profile.
- `backend/app/auth/service.py`: `AuthService` implementing authentication, brute-force lockout checks with generic anti-enumeration errors, rotating refresh session creation, reuse detection / family invalidation, logout, and password change.
- `backend/app/auth/dependencies.py`: FastAPI security dependencies `get_current_user` (authoritatively verifying backing session state and validity in PostgreSQL, rejecting revoked sessions instantly) and `get_current_active_user`.
- `backend/app/auth/router.py`: REST routes for `/api/v1/auth/login`, `/refresh`, `/logout`, `/logout-all`, `/change-password`, and `/me`.

### 1.5 Role-Based Access Control Subsystem (`backend/app/rbac/`)
- `backend/app/rbac/seeding.py`: 8 canonical system roles, 15 identity/RBAC/session/audit permissions, and idempotent `seed_system_rbac()` database seeding logic.
- `backend/app/rbac/schemas.py`: Pydantic models for roles and permissions inspection.
- `backend/app/rbac/service.py`: `RbacService` for role/permission catalog retrieval and dynamic user permission resolution from active database assignments.
- `backend/app/rbac/dependencies.py`: Declarative permission gates `require_permission` and `require_role`.
- `backend/app/rbac/router.py`: REST routes for `/api/v1/rbac/roles` and `/api/v1/rbac/permissions`.

### 1.6 User Management Subsystem (`backend/app/users/`)
- `backend/app/users/schemas.py`: Schemas for user provisioning, updates, role assignment, and pagination.
- `backend/app/users/service.py`: `UserService` implementing user creation with initial role, paginated filtering, profile retrieval, updates, and role assignment/soft revocation.
- `backend/app/users/router.py`: REST routes for `/api/v1/users` (create, list, get by ID, patch, assign role, revoke role).

### 1.7 Hardened Administration CLI Bootstrap (`backend/app/cli/`)
- `backend/app/cli/bootstrap_admin.py`: CLI command requiring explicit university and admin parameters, ingesting passwords safely via stdin, env var, or `getpass`, and prohibiting passwords in `sys.argv`.
- `backend/app/cli/__init__.py`: Package init.

### 1.8 API v1 Router Integration (`backend/app/api/v1/`)
- `backend/app/api/v1/router.py`: Mounted `/auth`, `/users`, and `/rbac` routers alongside foundation endpoints.

### 1.9 Automated Test Suite (`backend/tests/`)
- `backend/tests/conftest.py`: Fixtures for test client, sessionmaker, RBAC seeding, and university fixtures.
- `backend/tests/test_config.py`: Verified typed configuration, default environments, and future secret optionality.
- `backend/tests/test_passwords.py`: Tests verifying Argon2id hashing, verification, length-based policy, whitespace rejection, and optional composition.
- `backend/tests/test_tokens.py`: Tests verifying JWT encoding with `sid`, `iss`, `aud`, `nbf`, expiration rejection, and claim integrity.
- `backend/tests/test_rbac.py`: Tests verifying 8 approved roles, absence of future attendance permissions, role assignments, and route gates.
- `backend/tests/test_auth.py`: Tests verifying login, anti-enumeration lockout returns generic errors, session rotation, replay detection, instant access token invalidation on logout and logout-all, and password changes.
- `backend/tests/test_users.py`: Tests verifying user creation, pagination, updates, and role assignment/revocation.
- `backend/tests/test_bootstrap.py`: Tests verifying Super Admin CLI required parameters, password rejection in argv, stdin, and env var ingestion.

---

## 2. Quantitative Verification Summary

- **Total Backend Tests**: 83 passed, 0 failed (100% pass rate).
- **Static Type Checking**: `mypy --strict` passed with 0 errors across 74 files.
- **Linter & Formatter**: `ruff check` and `ruff format --check` passed with 0 errors.
- **Web Build**: Next.js 16.3.3 + React 19 passed lint, type-check, and build.
- **Mobile Build**: Flutter / Dart analyze passed with 0 issues; 3 unit tests passed.
- **Secret Scan**: 0 exposed secrets found in repository.
- **Development Stack**: All 5 Docker containers healthy and operational.
