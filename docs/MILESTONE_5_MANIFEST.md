# Digital Student Attendance System
## Milestone 5 Manifest — Identity, Authentication & Role-Based Access Control

**Generated At:** 2026-09-13  
**Feature Branch:** `feature/task-003-identity-auth-rbac`  
**Base Commit:** `81a04fd`  
**Milestone:** 5 — Identity, Authentication & Role-Based Access Control  

---

## 1. Inventory of Files Created / Modified

### 1.1 Core Configuration & System Constants (`backend/app/core/`)
- `backend/app/core/constants.py`: Extended with `UserStatus`, `SystemRole`, `ScopeType`, `AuthTokenType`.
- `backend/app/common/pagination.py`: Added `create()` factory method to `PaginatedResponse`.

### 1.2 Data Models & Persistence (`backend/app/models/`)
- `backend/app/models/user.py`: `User` model (`users` table) with UUIDv7 PK, university binding, normalized unique email, password hash, failed attempt counter, lockout expiry, `must_change_password`, and `status`.
- `backend/app/models/role.py`: `Role` model (`roles` table) with role name, code, description, and `is_system` indicator.
- `backend/app/models/permission.py`: `Permission` model (`permissions` table) with permission code, description, and module category.
- `backend/app/models/role_permission.py`: `RolePermission` association model (`role_permissions` table) with composite PK (`role_id`, `permission_id`).
- `backend/app/models/role_assignment.py`: `RoleAssignment` model (`role_assignments` table) with tenant scope (`ScopeType.UNIVERSITY`, `scope_id`), assigned metadata, and soft revocation fields (`revoked_at`, `revoked_by`, `revocation_reason`).
- `backend/app/models/refresh_session.py`: `RefreshSession` model (`refresh_sessions` table) storing SHA-256 hashed refresh tokens, family UUIDs, self-referential replacement pointer (`replaced_by_id`), device/IP telemetry, and revocation status.
- `backend/app/models/login_attempt.py`: `LoginAttempt` model (`login_attempts` table) tracking historical login outcomes, IP address, and user agent.
- `backend/app/models/audit_log.py`: `AuditLog` model (`audit_logs` table) for security event tracking.
- `backend/app/models/__init__.py`: Registered and re-exported all models.

### 1.3 Database Migration Pipeline (`backend/migrations/versions/`)
- `backend/migrations/versions/002_identity_users.py`: Alembic revision creating `users` table and indexes.
- `backend/migrations/versions/003_rbac.py`: Alembic revision creating `roles`, `permissions`, `role_permissions`, and `role_assignments` tables and indexes.
- `backend/migrations/versions/004_auth_sessions_attempts.py`: Alembic revision creating `refresh_sessions` (with self-referential FK) and `login_attempts` tables.

### 1.4 Cryptographic & Authentication Subsystem (`backend/app/auth/`)
- `backend/app/auth/passwords.py`: Argon2id hashing, verification, parameter verification, and validation rules.
- `backend/app/auth/tokens.py`: Standards-compliant RFC 7519 JWT access token generation, decode, and claims validation.
- `backend/app/auth/security.py`: Secure random opaque refresh token generator and SHA-256 hash digest utility.
- `backend/app/auth/schemas.py`: Pydantic request/response schemas for login, refresh, logout, password change, and current user profile.
- `backend/app/auth/service.py`: `AuthService` implementing authentication, brute-force lockout checks, rotating refresh session creation, reuse detection / family invalidation, logout, and password change.
- `backend/app/auth/dependencies.py`: FastAPI security dependencies `get_current_user` and `get_current_active_user`.
- `backend/app/auth/router.py`: REST routes for `/api/v1/auth/login`, `/refresh`, `/logout`, `/logout-all`, `/change-password`, and `/me`.

### 1.5 Role-Based Access Control Subsystem (`backend/app/rbac/`)
- `backend/app/rbac/seeding.py`: 7 canonical system roles, 18 permissions, and idempotent `seed_system_rbac()` database seeding logic.
- `backend/app/rbac/schemas.py`: Pydantic models for roles and permissions inspection.
- `backend/app/rbac/service.py`: `RBACService` for role/permission catalog retrieval and user permission resolution.
- `backend/app/rbac/dependencies.py`: Declarative permission gates `require_permission` and `require_role`.
- `backend/app/rbac/router.py`: REST routes for `/api/v1/rbac/roles` and `/api/v1/rbac/permissions`.

### 1.6 User Management Subsystem (`backend/app/users/`)
- `backend/app/users/schemas.py`: Schemas for user provisioning, updates, role assignment, and pagination.
- `backend/app/users/service.py`: `UserService` implementing user creation with initial role, paginated filtering, profile retrieval, updates, and role assignment/soft revocation.
- `backend/app/users/router.py`: REST routes for `/api/v1/users` (create, list, get by ID, patch, assign role, revoke role).

### 1.7 Administration CLI Bootstrap (`backend/app/cli/`)
- `backend/app/cli/bootstrap_admin.py`: CLI command for initializing Herat University and default Super Admin user.
- `backend/app/cli/__init__.py`: Package init.

### 1.8 API v1 Router Integration (`backend/app/api/v1/`)
- `backend/app/api/v1/router.py`: Mounted `/auth`, `/users`, and `/rbac` routers alongside foundation endpoints.

### 1.9 Dependencies & Pytest Configuration
- `backend/pyproject.toml`: Added `pwdlib[argon2]==0.3.1`, `argon2-cffi==25.1.0`, `pyjwt==2.14.0`, `cryptography==50.0.1`. Configured asyncio session scopes for testing.
- `backend/requirements.txt`: Updated lock pinned dependencies.

### 1.10 Automated Test Suite (`backend/tests/`)
- `backend/tests/conftest.py`: Added test client, sessionmaker, RBAC seeding, and university fixtures.
- `backend/tests/test_config.py`: Verified typed configuration and default environments.
- `backend/tests/test_passwords.py`: 8 tests verifying Argon2id hashing, verification, strength enforcement, and rehashing.
- `backend/tests/test_tokens.py`: 7 tests verifying JWT encoding, decoding, expiration rejection, and claim integrity.
- `backend/tests/test_rbac.py`: 6 tests verifying role assignments, permission resolution, and declarative route gates.
- `backend/tests/test_auth.py`: 11 tests verifying login, lockout after 5 failed attempts, refresh rotation, family reuse detection, logout, logout-all, and password change.
- `backend/tests/test_users.py`: 8 tests verifying user creation, pagination, updates, and role assignment/revocation.
- `backend/tests/test_bootstrap.py`: 3 tests verifying Super Admin CLI idempotency and error handling.

---

## 2. Quantitative Verification Summary

- **Total Backend Tests**: 79 passed, 0 failed (100% pass rate).
- **Static Type Checking**: `mypy --strict` passed with 0 errors.
- **Linter & Formatter**: `ruff check` and `ruff format --check` passed with 0 errors.
- **Web Build**: Next.js 16.3.3 + React 19 passed lint, type-check, and build.
- **Mobile Build**: Flutter / Dart analyze passed with 0 issues; 3 unit tests passed.
- **Secret Scan**: 0 exposed secrets found in repository.
