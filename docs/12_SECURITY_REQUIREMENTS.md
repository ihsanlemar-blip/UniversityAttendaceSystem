# Digital Student Attendance System
## Security Requirements

**Version:** 1.0  
**Security posture:** Defense in depth, local-first, privacy-aware

---

## 1. Security Objectives

Protect:

- User accounts
- Attendance integrity
- Student privacy
- Device registrations
- Audit history
- Local campus server
- Cloud backup/sync
- Administrative privileges

Prevent or reduce:

- Credential theft
- Proxy attendance
- Token replay
- Device sharing
- Unauthorized corrections
- Data exposure
- API abuse
- Offline tampering
- Privilege escalation

---

## 2. Authentication

### Passwords

- Use a modern password hashing algorithm such as Argon2id.
- Never store plaintext passwords.
- Support password reset through authorized university process.
- Rate-limit login attempts.
- Lock or slow repeated abusive attempts.

### Sessions

- Short-lived access credentials.
- Rotating refresh credentials.
- Refresh tokens stored only as hashes server-side.
- Revoke refresh family on suspicious reuse.

### Web

Prefer:

- Secure
- HttpOnly
- SameSite
- HTTPS-only cookies

where compatible with architecture.

### Mobile

Store sensitive credentials only in OS-protected secure storage where possible.

---

## 3. Authorization

Use RBAC plus organizational scope.

Every sensitive endpoint checks:

1. Authenticated user
2. Permission
3. Scope
4. Target resource ownership/relationship
5. Additional policy if required

Never trust role claims supplied by client.

---

## 4. Device Cryptographic Registration

Student mobile app generates key pair.

Private key:

- Never uploaded
- Stored in secure OS keystore where possible
- Used to sign attendance request challenges/payloads

Server stores public key.

Device registration lifecycle:

- Requested
- Approved/active
- Revoked
- Replaced

---

## 5. Dynamic Token Security

Attendance tokens must:

- Be signed
- Be short-lived
- Bind to checkpoint/session
- Have replay protection
- Avoid sensitive data
- Use strong randomness/nonces
- Use server-authoritative time

Do not use a static QR code per course/class.

---

## 6. Bluetooth Security

- Use ephemeral session identifiers.
- Rotate identifiers.
- Do not use Bluetooth MAC as student identity.
- Treat Bluetooth as supporting evidence.
- Avoid storing raw scan history beyond operational need.
- Validate timing server-side.

---

## 7. Campus Network Validation

Do not trust SSID string alone.

Use trusted local service reachability or stronger network proof.

Student network should only reach necessary services.

Database and Redis should never be directly exposed to student Wi-Fi.

---

## 8. TLS

All client-server traffic uses HTTPS/TLS.

Avoid disabling certificate validation in development code.

Do not ship a production client with "accept all certificates".

Recommended:

- University-controlled hostname
- Valid certificate
- Internal DNS resolving to local server

---

## 9. API Security

- Validate all inputs.
- Enforce content length limits.
- Rate-limit abuse-prone endpoints.
- Use idempotency keys.
- Protect against mass assignment.
- Apply pagination.
- Do not expose sequential sensitive identifiers.
- Return generic error messages for authentication failures.
- Use request correlation IDs.

---

## 10. Attendance Submission Security

Server verifies:

- Student identity
- Enrollment
- Checkpoint state
- Session state
- Token validity
- Device signature
- Presence signals
- Duplicate/idempotency state
- Risk policy

Client must not be able to directly set final attendance status.

---

## 11. Offline Permit Security

Offline permit:

- Issued by campus server
- Signed
- Bound to lecturer
- Bound to registered device
- Bound to one class occurrence/session
- Has validity window
- Has explicit permissions
- Revocable where connectivity exists

Offline device cannot create arbitrary session authority.

---

## 12. Offline Data Security

- App-private local storage
- Encryption for sensitive local data where feasible
- Signed offline events
- Tamper-evident queue
- No plaintext passwords
- No private signing keys in database

---

## 13. Audit Security

Sensitive changes generate audit events.

Examples:

- Attendance correction
- Admin override
- Device reset
- Role change
- Policy change
- Physical card reissue
- Offline sync conflict resolution

Audit records should be append-only through application logic.

Optional stronger integrity:

- Hash-chain audit batches/events
- Periodic signed audit checkpoints

---

## 14. Secrets Management

Never commit:

- Database passwords
- JWT signing keys
- Token HMAC keys
- Cloud credentials
- TLS private keys
- Device private keys

Use environment/secret management.

Separate:

- development secrets
- staging secrets
- production secrets

---

## 15. Database Security

- Application uses least-privilege DB account.
- Migration account may have elevated schema privileges.
- Database binds only to trusted network/interface.
- Backups encrypted when feasible.
- Restore access restricted.
- Audit destructive SQL operations operationally.

---

## 16. Redis Security

- Not exposed publicly.
- Restricted to private network.
- Authentication/configuration as appropriate.
- Do not store long-lived sensitive secrets in plaintext.

---

## 17. Web Security

Protect against:

- XSS
- CSRF
- clickjacking
- insecure CORS
- open redirects
- injection
- broken access control

Recommended headers:

- Content-Security-Policy
- X-Content-Type-Options
- Referrer-Policy
- frame restrictions
- HSTS where deployment permits

---

## 18. File Import Security

For Excel/CSV:

- Size limits
- Allowed extensions/content validation
- Store outside executable paths
- Sanitize filenames
- Validate data before commit
- Prevent formula injection in exported spreadsheets
- Audit importer and source file metadata

---

## 19. Privacy

V1 excludes:

- Face recognition
- Continuous GPS
- Biometric attendance

Collect minimum necessary data.

Do not expose:

- Device cryptographic material
- Sensitive identifiers
- Internal risk details to unauthorized users

---

## 20. Risk Detection

Security/risk flags may include:

- Shared device
- Frequent device replacement
- Unusual account switching
- Missing required presence signal
- Replayed token
- Mass manual attendance
- Excessive corrections
- Offline attendance anomalies
- Session opened outside policy

Flags require review and are not automatic guilt determinations.

---

## 21. Administrative Security

High-risk actions should require one or more:

- Reason
- Re-authentication
- Elevated permission
- Second approval
- Audit log

Examples:

- Attendance override after long delay
- Bulk attendance changes
- Role changes
- Device resets
- Policy changes

---

## 22. Backup Security

- Automated backups
- Access-restricted
- Encrypted where feasible
- Offsite copy when internet available
- Restore tested
- Retention policy
- Backup failures alert administrators

---

## 23. Logging Rules

Never log:

- Passwords
- Raw refresh tokens
- Private keys
- Full QR secrets
- Sensitive authorization headers

Mask:

- Personal identifiers where possible in operational logs

Security/audit logs may contain identifiers only where required and access-controlled.

---

## 24. Dependency Security

- Pin dependencies using lock files.
- Automated dependency scanning.
- Review critical vulnerabilities.
- Do not automatically upgrade production dependencies without tests.

---

## 25. CI Security Gates

Before merge:

- Lint
- Type checks
- Unit tests
- Integration tests
- Secret scan
- Dependency scan
- Migration validation

Before production release:

- Security review
- Backup verification
- Restore procedure tested
- High-severity findings resolved

---

## 26. Security Invariants

1. Client cannot directly assign itself Present.
2. Device private key never leaves device.
3. Student device clock is not authoritative.
4. Expired token cannot grant attendance.
5. Wrong-session token cannot grant attendance.
6. Manual attendance is always distinguishable.
7. Admin correction is always auditable.
8. Local DB is never directly reachable by student clients.
9. Internet outage does not justify disabling security checks globally.
10. No production secrets in source control.

---

## 27. Production Security Hardening (Milestone 18 Baseline)

### 27.1 Cryptographic Key Separation
To prevent cross-protocol key compromise, four isolated cryptographic keys are enforced:
1. **AUTH_SIGNING_KEY**: Dedicated HMAC key (>= 32 chars) for JWT access tokens.
2. **ATTENDANCE_QR_SIGNING_KEY**: Dedicated HMAC key (>= 32 chars, `kid="att-qr-k1"`) for dynamic rotating QR check-in tokens.
3. **ATTENDANCE_BLE_SIGNING_KEY**: Dedicated HMAC key (>= 32 chars) for BLE classroom presence advertisements.
4. **OFFLINE_PERMIT_SIGNING_PRIVATE_KEY**: Dedicated asymmetric Ed25519 private key in PEM format (`kid="att-off-k1"`) for signing offline student permits.

Cross-field validation in `backend/app/core/config.py` raises startup exceptions if any of these keys share values.

### 27.2 Production Fail-Closed Startup
When `APP_ENV=production`, the application refuses to start if:
- `DEBUG=True`
- Wildcard CORS (`*`) is present in `CORS_ALLOWED_ORIGINS`
- `DATABASE_PASSWORD` matches default or dictionary passwords
- Any signing key contains development markers (`dev-`, `test`, `default`) or has fewer than 32 characters
- OpenAPI / Swagger documentation is enabled without explicit operational approval (`DOCS_ENABLED` defaults to `False` in production)

### 27.3 Web Security Headers & Sensitive Cache Control
FastAPI and Next.js enforce OWASP defense-in-depth response headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(self), microphone=(), geolocation=(), bluetooth=(self)`
- `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self';`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (enforced in production HTTPS)
- `Cache-Control: no-store, no-cache, must-revalidate, private` on all `/api/*` endpoints

### 27.4 Observable Rate Limiting & HTTP 429
Endpoints subject to automated abuse are rate-limited via Redis sliding windows (with in-memory fallback):
- `POST /api/v1/auth/login`: 5 requests / 60s per client IP
- `POST /api/v1/auth/change-password`: 5 requests / 60s per user
- `POST /api/v1/devices/registration/challenge`: 10 requests / 60s per client IP
- `POST /api/v1/attendance/qr/check-in`: 30 requests / 60s per client IP
- `POST /api/v1/attendance/presence/check-in`: 30 requests / 60s per client IP
- `POST /api/v1/attendance/network-presence/challenge`: 20 requests / 60s per client IP
- `POST /api/v1/imports/preview`: 10 requests / 60s per user / tenant

Exceeded limits return HTTP 429 with standard JSON envelope and `Retry-After: <seconds>` response header.

### 27.5 Reverse Proxy Trust & Anti-Spoofing
`ClientNetworkResolver` enforces that forwarding headers (`X-Forwarded-For`, `X-Real-IP`) are processed **only** when the immediate socket peer address matches `TRUSTED_PROXY_CIDRS`. Hops are evaluated right-to-left. Untrusted direct peers attempting to spoof client IP headers are pinned strictly to their physical socket address.

### 27.6 Multi-Factor Authentication (MFA) Decision
> [!NOTE]
> **MFA/passkey support is not part of v1.0 unless subsequently approved.**  
> Administrative accounts are protected by Argon2id hashing, strict rate limiting, mandatory first-login password changes, and immediate server-side session revocation upon credential rotation or account suspension.

### 27.7 Device Private Key Storage Claims
Device private keys are managed on student mobile devices strictly using **"OS-protected secure storage"** (`FlutterSecureStorage` utilizing Android Keystore and iOS Keychain). The system does not claim certified hardware-backed Secure Enclave or StrongBox key protection.

### 27.8 Operational Key Rotation Procedures
1. **JWT Access Tokens**: Change `AUTH_SIGNING_KEY` during scheduled maintenance window. Active sessions rotate smoothly via refresh token re-issuance.
2. **Attendance QR Tokens**: Supports key identifier `ATTENDANCE_QR_SIGNING_KID`. Update key and kid; scanners gracefully accept previous step tokens during tolerance window (±1 step).
3. **BLE Presence Tokens**: Update `ATTENDANCE_BLE_SIGNING_KEY` concurrently on server and lecturer broadcast devices.
4. **Offline Permits**: Update `OFFLINE_PERMIT_SIGNING_PRIVATE_KEY` with new `OFFLINE_PERMIT_SIGNING_KID`. Previous permits expire within max validity window (24h).

