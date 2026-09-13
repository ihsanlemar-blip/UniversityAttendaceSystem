# Digital Student Attendance System
## 31. Milestone 5 & 5.1 — Identity, Authentication & Role-Based Access Control (Hardened)

**Document Version:** 1.1  
**Status:** Completed & Hardened  
**Milestones:** 5 (Core Implementation) & 5.1 (Authentication & RBAC Hardening)  
**Git Feature Branch:** `feature/task-003-identity-auth-rbac`  
**Base Commit:** `81a04fd`  

---

## 1. Executive Summary

Milestone 5 and 5.1 establish the complete, hardened identity, authentication, session management, and role-based access control (RBAC) subsystem for the **Digital Student Attendance System**. In strict compliance with `AGENTS.md` and the system specifications, **zero academic structure** (no student enrollment, no lecturer assignments, no courses, no academic units) and **zero attendance engine logic** (no attendance sessions, no dynamic QR code rotation, no BLE beacon scanning, no device hardware fingerprinting) were introduced.

The hardened identity and access foundation provides:
1. **Cryptographic Password Security (NIST SP 800-63B)**: Argon2id password hashing via `pwdlib[argon2]` and `argon2-cffi` configured with RFC 9106 recommended parameters (memory cost 65,536 KiB, time cost 3 iterations, parallelism 4 lanes). The password policy is primarily length-based (configurable minimum length default 8, maximum 128) without arbitrary character composition requirements, and rejects empty or whitespace-only inputs.
2. **Authoritative Session Verification & Enhanced JWT Claims**: Standards-compliant RFC 7519 JSON Web Tokens (JWT) signed with HMAC-SHA256 (256-bit secret key), 15-minute expiration, and explicit claims: `sub` (user UUID), `sid` (session UUID), `university_id`, `roles`, `typ="access"`, `jti` (UUIDv7), `iat`, `nbf`, `exp`, `iss`, and `aud`. In `get_current_user`, every protected request authoritatively verifies in PostgreSQL that the backing session (`sid`) exists, has not expired, and has not been revoked (`revoked_at is None`). Calling `/logout` or `/logout-all` immediately invalidates access tokens across all clients.
3. **Rotating Refresh Sessions & Replay Detection**: Cryptographically random opaque 256-bit refresh tokens hashed with SHA-256 in the database, with automatic rotation upon use, replacement pointer chains (`replaced_by_id`), and family-based reuse detection that immediately revokes the entire token family if an already-rotated token is presented.
4. **Persistent Brute-Force Protection with Anti-Enumeration**: Database-backed attempt logging (`login_attempts`) tracking consecutive failures per normalized email and IP address. Accounts are automatically locked for 15 minutes upon 5 consecutive failed attempts. All authentication failures—including locked accounts, disabled accounts, and nonexistent users—return identical generic error envelopes (`AUTH_INVALID_CREDENTIALS` / `"Invalid credentials."`) with HTTP 401, completely preventing username and account state enumeration.
5. **Authoritative Server-Side RBAC Engine**:
   - 8 canonical system roles aligned with `docs/03_USER_ROLES_AND_PERMISSIONS.md`: `SUPER_ADMIN`, `UNIVERSITY_ADMIN`, `FACULTY_ADMIN`, `DEPARTMENT_ADMIN`, `ATTENDANCE_OFFICER`, `LECTURER`, `STUDENT`, `AUDITOR`.
   - Pruned permission catalog containing strictly identity, user management, role assignments, sessions, and audit permissions (zero premature future attendance permissions).
   - Roles and permissions resolved authoritatively server-side via PostgreSQL queries rather than trusting stale JWT claims.
   - Declarative FastAPI dependency gates (`require_permission`, `require_role`) enforcing deny-by-default permission checks at route entry.
   - Scoped role assignments (`ScopeType.UNIVERSITY`, `scope_id`) supporting tenant separation and soft revocation with audit reasons.
6. **Hardened Production CLI Bootstrap**:
   - `python -m backend.app.cli.bootstrap_admin` requires explicit university code, university name, and username parameters.
   - Prohibits password passing via command-line arguments to prevent leakage in OS process tables (`ps`, `Get-Process`) and shell histories.
   - Ingests passwords securely via interactive hidden prompt (`getpass`), stdin (`--password-stdin`), or `BOOTSTRAP_ADMIN_PASSWORD` environment variable.
7. **Database Migration Pipeline**:
   - `002_identity_users.py`: `users` table with UUIDv7 PK, normalized unique email, password hash, status, and failed attempts tracking.
   - `003_rbac.py`: `roles`, `permissions`, `role_permissions`, and `role_assignments` tables.
   - `004_auth_sessions_attempts.py`: `refresh_sessions` (with family tracking and self-referential replacement FK) and `login_attempts` tables.

---

## 2. Invariant Compliance Verification

| Invariant | Description | Milestone 5 / 5.1 Status | Verification Details |
|---|---|---|---|
| **INV-01** | Client Cannot Mark Itself Present | **PRESERVED / NOT YET IMPLEMENTED** | No attendance submission endpoint exists. Tokens issued identify caller identity and permissions only. |
| **INV-02** | Attendance Depends on Server/Domain Validation | **PRESERVED / NOT YET IMPLEMENTED** | RBAC permission infrastructure ensures that future attendance operations will be strictly validated server-side. |
| **INV-03** | Student Device Clock Is NOT Authoritative | **ENFORCED** | All JWT expirations (`exp`), refresh session expiries, lockout durations, and attempt timestamps are generated strictly using server UTC clock (`datetime.now(timezone.utc)`). |
| **INV-04** | Expired Dynamic QR/Tokens Cannot Grant Attendance | **PRESERVED / NOT YET IMPLEMENTED** | Attendance token verification deferred to Attendance Engine milestone. JWT tokens reject expired requests unconditionally via standard `exp` claim validation. |
| **INV-05** | No Duplicate Checkpoint Credit | **PRESERVED / NOT YET IMPLEMENTED** | Attendance domain deferred. Refresh token rotation enforces single-use replay detection. |
| **INV-06** | Corrections Cannot Erase History | **PRESERVED / NOT YET IMPLEMENTED** | Attendance correction revision history deferred to Attendance Engine and Audit milestones. |
| **INV-07** | Offline Events Remain Identifiable | **PRESERVED / NOT YET IMPLEMENTED** | Offline token synchronization deferred to offline milestone. |
| **INV-08** | Manual Attendance Overrides Remain Identifiable | **PRESERVED / NOT YET IMPLEMENTED** | Manual attendance override workflow and audit actor logging deferred to Attendance Engine milestone. |

---

## 3. Implemented Subsystems & Endpoints

### 3.1 Authentication Subsystem (`/api/v1/auth`)

- `POST /api/v1/auth/login`: Authenticates credentials, evaluates brute-force lockouts, records attempts, returns generic errors for anti-enumeration, generates access token with `sid` and rotating refresh token session.
- `POST /api/v1/auth/refresh`: Validates opaque refresh token, performs reuse detection, invalidates token family upon replay, and issues fresh token pair.
- `POST /api/v1/auth/logout`: Revokes active refresh session. The associated access token is instantly rejected on subsequent requests.
- `POST /api/v1/auth/logout-all`: Revokes all active refresh sessions for the authenticated user, immediately invalidating all user access tokens.
- `POST /api/v1/auth/change-password`: Verifies current password, applies Argon2id hash to new password, clears `must_change_password`, and revokes other active sessions.
- `GET /api/v1/auth/me`: Returns identity profile, university context, assigned roles, and resolved permissions authoritatively fetched from the database.

### 3.2 User Management Subsystem (`/api/v1/users`)

- `POST /api/v1/users`: Creates user account with university association, optional initial role, and temporary password (`require_permission("users.create")`).
- `GET /api/v1/users`: Paginated listing of users filtered by `university_id`, `role`, and `status` (`require_permission("users.read")`).
- `GET /api/v1/users/{id}`: Detailed user record including active role assignments and university info (`require_permission("users.read")`).
- `PATCH /api/v1/users/{id}`: Status and attribute updates (`require_permission("users.update")`).
- `POST /api/v1/users/{id}/roles`: Assigns role to user within university scope (`require_permission("role_assignments.manage")`).
- `DELETE /api/v1/users/{id}/roles/{role_id}`: Soft revokes role assignment with audit reason (`require_permission("role_assignments.manage")`).

### 3.3 RBAC Catalog Subsystem (`/api/v1/rbac`)

- `GET /api/v1/rbac/roles`: Lists all standard roles and associated permissions (`require_permission("roles.read")`).
- `GET /api/v1/rbac/permissions`: Lists all system permissions (`require_permission("permissions.read")`).

### 3.4 Hardened CLI Administration Bootstrap

- `python -m backend.app.cli.bootstrap_admin --username <USER> --university-code <CODE> --university-name <NAME>`: Secure provisioning of root university and Super Admin account.

---

## 4. Test Coverage & Quality Gates

- **Backend Pytest Suite**: 83 tests passing (100% pass rate).
- **Ruff Linter & Formatter**: Clean (0 errors, 0 format discrepancies).
- **Mypy Static Type Checking**: Clean (`strict = true`, 0 errors).
- **Next.js Web Application**: Clean TypeScript, ESLint, and Turbopack build.
- **Flutter Mobile Application**: Clean `dart analyze` and unit tests passing.
- **Repository Secret Scanner**: Clean (0 exposed secrets).
