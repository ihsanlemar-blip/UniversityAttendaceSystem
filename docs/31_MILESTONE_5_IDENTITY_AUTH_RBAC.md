# Digital Student Attendance System
## 31. Milestone 5 — Identity, Authentication & Role-Based Access Control

**Document Version:** 1.0  
**Status:** Completed  
**Milestone:** 5 — Identity, Authentication & Role-Based Access Control  
**Git Feature Branch:** `feature/task-003-identity-auth-rbac`  
**Base Commit:** `81a04fd`  

---

## 1. Executive Summary

Milestone 5 implements the complete identity, authentication, session management, and role-based access control (RBAC) subsystem for the **Digital Student Attendance System**. In strict compliance with `AGENTS.md` and the system specifications, **zero academic structure** (no student enrollment, no lecturer assignments, no courses, no academic units) and **zero attendance engine logic** (no attendance sessions, no dynamic QR code rotation, no BLE beacon scanning, no device hardware fingerprinting) were introduced.

The identity and access foundation provides:
1. **Cryptographic Password Security**: Argon2id password hashing via `pwdlib[argon2]` and `argon2-cffi` configured with RFC 9106 recommended parameters (memory cost 65,536 KiB, time cost 3 iterations, parallelism 4 lanes).
2. **Stateless Access Tokens**: Standards-compliant RFC 7519 JSON Web Tokens (JWT) signed with HMAC-SHA256 (256-bit secret key), 15-minute expiration, and custom claims for tenant isolation (`university_id`), user identity (`sub`, `user_id`), assigned system roles (`roles`), and resolved permission strings (`permissions`).
3. **Rotating Refresh Sessions & Replay Detection**: Cryptographically random opaque 256-bit refresh tokens hashed with SHA-256 in the database, with automatic rotation upon use, replacement pointer chains (`replaced_by_id`), and family-based reuse detection that immediately revokes the entire token family if an already-rotated token is presented.
4. **Persistent Brute-Force Protection**: Database-backed attempt logging (`login_attempts`) tracking consecutive failures per normalized email and IP address. Accounts are automatically locked for 15 minutes upon 5 consecutive failed attempts, returning generic error envelopes to prevent username enumeration.
5. **Session Revocation & Mandatory Password Updates**: Full server-side session revocation (`POST /api/v1/auth/logout`, `POST /api/v1/auth/logout-all`), status verification (`ACTIVE`, `SUSPENDED`, `INACTIVE`, `PENDING_VERIFICATION`), and first-time login mandatory password reset enforcement (`must_change_password`).
6. **Hierarchical RBAC Engine**:
   - 7 canonical system roles (`SUPER_ADMIN`, `UNIVERSITY_ADMIN`, `FACULTY_DEAN`, `DEPARTMENT_HEAD`, `LECTURER`, `STUDENT`, `AUDITOR`).
   - 18 granular permissions categorized across users, courses, attendance, reports, audit, and system.
   - Declarative FastAPI dependency gates (`require_permission`, `require_role`) enforcing permission evaluation at route entry.
   - Scoped role assignments (`ScopeType.UNIVERSITY`, `scope_id`) supporting tenant separation and soft revocation with audit reasons.
7. **Idempotent RBAC Seeding & Super Admin Bootstrap**:
   - `seed_system_rbac`: Idempotent data seeding of standard roles, permissions, and role-permission matrices.
   - `python -m backend.app.cli.bootstrap_admin`: CLI command provisioning the root University (`Herat University - HU`) and the default Super Admin user account.
8. **Database Migration Pipeline**:
   - `002_identity_users.py`: `users` table with UUIDv7 PK, normalized unique email, password hash, status, and failed attempts tracking.
   - `003_rbac.py`: `roles`, `permissions`, `role_permissions`, and `role_assignments` tables.
   - `004_auth_sessions_attempts.py`: `refresh_sessions` (with family tracking and self-referential replacement FK) and `login_attempts` tables.

---

## 2. Invariant Compliance Verification

| Invariant | Description | Milestone 5 Status | Verification Details |
|---|---|---|---|
| **INV-01** | Client Cannot Mark Itself Present | **PRESERVED / NOT YET IMPLEMENTED** | No attendance submission endpoint exists. Tokens issued identify the caller and permissions only. |
| **INV-02** | Attendance Depends on Server/Domain Validation | **PRESERVED / NOT YET IMPLEMENTED** | RBAC permission infrastructure ensures that only callers with `attendance:record` or `attendance:override` can interact with future attendance endpoints. |
| **INV-03** | Student Device Clock Is NOT Authoritative | **ENFORCED** | All JWT expirations (`exp`), refresh session expiries, lockout durations, and attempt timestamps are generated strictly using server UTC clock (`datetime.now(timezone.utc)`). |
| **INV-04** | Expired Dynamic QR/Tokens Cannot Grant Attendance | **PRESERVED / NOT YET IMPLEMENTED** | Attendance token verification deferred to Attendance Engine milestone. JWT tokens reject expired requests unconditionally via standard `exp` claim validation. |
| **INV-05** | No Duplicate Checkpoint Credit | **PRESERVED / NOT YET IMPLEMENTED** | Attendance domain deferred. Refresh token rotation enforces single-use replay detection. |
| **INV-06** | Corrections Cannot Erase History | **ENFORCED** | User and role assignments utilize soft revocation (`revoked_at`, `revoked_by`, `revocation_reason`). Refresh sessions preserve audit chains through replacement pointers. |
| **INV-07** | Offline Events Remain Identifiable | **PRESERVED / NOT YET IMPLEMENTED** | Offline token synchronization deferred to offline milestone. |
| **INV-08** | Manual Attendance Overrides Remain Identifiable | **ENFORCED (RBAC Level)** | Granular permissions `attendance:override` and `audit:read` are established and restricted to administrative and auditing roles. |

---

## 3. Implemented Subsystems & Endpoints

### 3.1 Authentication Subsystem (`/api/v1/auth`)

- `POST /api/v1/auth/login`: Authenticates credentials, evaluates brute-force lockouts, records attempts, generates access token and rotating refresh token session.
- `POST /api/v1/auth/refresh`: Validates opaque refresh token, performs reuse detection, invalidates token family upon replay, and issues fresh token pair.
- `POST /api/v1/auth/logout`: Revokes active refresh session.
- `POST /api/v1/auth/logout-all`: Revokes all active refresh sessions for the authenticated user.
- `POST /api/v1/auth/change-password`: Verifies current password, applies Argon2id hash to new password, clears `must_change_password`, and revokes other active sessions.
- `GET /api/v1/auth/me`: Returns identity profile, university context, assigned roles, and resolved permissions.

### 3.2 User Management Subsystem (`/api/v1/users`)

- `POST /api/v1/users`: Creates user account with university association, optional initial role, and temporary password (`require_permission("users:create")`).
- `GET /api/v1/users`: Paginated listing of users filtered by `university_id`, `role`, and `status` (`require_permission("users:read")`).
- `GET /api/v1/users/{id}`: Detailed user record including active role assignments and university info (`require_permission("users:read")`).
- `PATCH /api/v1/users/{id}`: Status and attribute updates (`require_permission("users:update")`).
- `POST /api/v1/users/{id}/roles`: Assigns role to user within university scope (`require_permission("users:assign_role")`).
- `DELETE /api/v1/users/{id}/roles/{role_id}`: Soft revokes role assignment with audit reason (`require_permission("users:assign_role")`).

### 3.3 RBAC Catalog Subsystem (`/api/v1/rbac`)

- `GET /api/v1/rbac/roles`: Lists all standard roles and associated permissions (`require_permission("system:roles:read")`).
- `GET /api/v1/rbac/permissions`: Lists all system permissions (`require_permission("system:roles:read")`).

### 3.4 CLI Administration Bootstrap

- `python -m backend.app.cli.bootstrap_admin`: Provision initial root university and Super Admin account.

---

## 4. Test Coverage & Quality Gates

- **Backend Pytest Suite**: 79 tests passing (100% pass rate).
- **Ruff Linter & Formatter**: Clean (0 errors, 0 format discrepancies).
- **Mypy Static Type Checking**: Clean (`strict = true`, 0 errors).
- **Next.js Web Application**: Clean TypeScript, ESLint, and Turbopack build.
- **Flutter Mobile Application**: Clean `dart analyze` and unit tests passing.
- **Repository Secret Scanner**: Clean (0 exposed secrets).
