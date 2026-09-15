# Milestone 10 — Dynamic QR & Cryptographic Presence Tokens Specification

## 1. Executive Summary & Attendance Invariants

Milestone 10 establishes the real-time dynamic presence verification engine via rotating, cryptographically signed visual QR codes. Building upon the Milestone 9 core attendance engine, M10 allows authorized lecturers to display live, short-lived tokens in physical classrooms and enables enrolled students to check in securely using their mobile devices.

### Invariants Enforced

* **INV-01 (Client Cannot Mark Itself Present)**: The mobile application captures raw QR token evidence and submits it to the server. The server attendance engine cryptographically validates the token, evaluates active session status, enforces roster enrollment, and awards checkpoint credit. The client never provides its own status.
* **INV-03 (Authoritative University Clock)**: Token generation, rotation slots, and expiration checks rely strictly on the university server UTC clock. Device clock manipulations cannot extend token validity.
* **INV-04 (Zero Tolerance for Expired Tokens)**: Dynamic tokens expire at their rotation slot boundary (default 30 seconds) or when the checkpoint window closes. Expired tokens are rejected unconditionally with `QR_TOKEN_EXPIRED`.
* **INV-05 (No Duplicate Checkpoint Credit)**: Exactly one credit can be awarded per student per checkpoint per attendance session. Duplicate scans return an idempotent, non-destructive success response with `already_credited: true`.
* **Classroom Shared Token Model**: The rotating visual token is broadcast on the lecturer's projector screen. Multiple distinct students in the class can scan the exact same token within its valid rotation window.
* **Zero Student PII**: Displayed QR tokens contain strictly session, checkpoint, and rotation slot context; tokens never contain student identifiers, names, or device identifiers.
* **Cryptographic Isolation**: Dynamic QR signing uses `ATTENDANCE_QR_SIGNING_KEY`, which is strictly isolated from the authentication secret `AUTH_SIGNING_KEY`.

---

## 2. Cryptographic Token Specification

Presence tokens are compact JSON Web Tokens (JWT) signed using HMAC-SHA256 (`HS256`).

### 2.1 JWT Header
```json
{
  "alg": "HS256",
  "typ": "attendance_qr",
  "kid": "att-qr-k1"
}
```

### 2.2 JWT Payload Claims
```json
{
  "ver": 1,
  "typ": "attendance_qr",
  "iss": "digital-student-attendance-system",
  "aud": "attendance-checkpoint",
  "uid": "3f4a9b2c-8d1e-4f3a-9c2b-1a2b3c4d5e6f",
  "sid": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
  "cid": "9c0d1e2f-3a4b-5c6d-7e8f-9a0b1c2d3e4f",
  "cpt": "START",
  "slot": 59345210,
  "iat": 1789400000,
  "nbf": 1789400000,
  "exp": 1789400030,
  "jti": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
}
```

* `ver`: Token format version (integer, currently 1).
* `typ`: Token type, strictly `"attendance_qr"`.
* `iss`: Standardized system issuer (`settings.ATTENDANCE_QR_ISSUER`).
* `aud`: Standardized audience (`settings.ATTENDANCE_QR_AUDIENCE`).
* `uid`: University UUID (multi-tenant isolation boundary).
* `sid`: Attendance Session UUID.
* `cid`: Attendance Checkpoint UUID (`START`, `MIDDLE`, or `END`).
* `cpt`: Checkpoint type code.
* `slot`: Rotation slot index (`floor(now / rotation_seconds)`).
* `iat` / `nbf`: Issued-at and not-before UTC epoch seconds.
* `exp`: Authoritative expiration UTC epoch seconds.
* `jti`: Unique cryptographically random UUID per token emission.

---

## 3. Rotation Timing & Expiration Logic

Token rotation aligns to deterministic server clock intervals:

$$\text{rotation\_slot} = \left\lfloor \frac{\text{server\_time\_utc}}{\text{rotation\_seconds}} \right\rfloor$$

$$\text{slot\_end\_utc} = (\text{rotation\_slot} + 1) \times \text{rotation\_seconds}$$

$$\text{token\_exp} = \min(\text{slot\_end\_utc}, \text{checkpoint\_close\_utc})$$

* Default rotation interval: 30 seconds.
* Tokens are refreshed on the client before or at expiration.
* Token replay after 30 seconds is rejected automatically as expired.
* Fast tests inject fake clock times to verify rotation boundaries with zero execution delay.

---

## 4. API Endpoints

### 4.1 Lecturer Visual Token Emission
* **Route**: `GET /api/v1/attendance/checkpoints/{checkpoint_id}/qr-token`
* **Permission**: `attendance_checkpoints.manage` (with occurrence authority check)
* **Headers**: `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`
* **Response**: `StandardResponse[QrTokenResponse]`
```json
{
  "data": {
    "token": "<signed_dynamic_qr_presence_token>",
    "checkpoint_id": "9c0d1e2f-3a4b-5c6d-7e8f-9a0b1c2d3e4f",
    "checkpoint_type": "START",
    "issued_at": "2026-09-14T10:00:00Z",
    "expires_at": "2026-09-14T10:00:30Z",
    "rotation_seconds": 30,
    "server_time": "2026-09-14T10:00:00Z",
    "refresh_after_seconds": 30
  }
}
```

### 4.2 Student Dynamic QR Check-In
* **Route**: `POST /api/v1/attendance/qr/check-in`
* **Permission**: `attendance.self_read` (authenticated active student)
* **Payload**: `QrCheckInRequest`
```json
{
  "token": "<scanned_dynamic_qr_presence_token>"
}
```
* **Response**: `StandardResponse[QrCheckInResponse]`
```json
{
  "data": {
    "accepted": true,
    "checkpoint_type": "START",
    "already_credited": false,
    "verified_at": "2026-09-14T10:00:05Z",
    "attendance_record_id": "0192323e-6708-724a-a43b-8106daee86fa"
  },
  "meta": {
    "message": "Checkpoint 'START' credited successfully."
  }
}
```

---

## 5. Storage & Audit Architecture

Milestone 10 requires **zero database schema migrations**, leveraging the existing `AttendanceEvidence` model:

* `source_mode`: Set to `"ONLINE_DYNAMIC_QR"`.
* `evidence_metadata`:
  ```json
  {
    "token_hash": "<sha256_hex_digest>",
    "slot": 59345210,
    "jti": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "issued_at": 1789400000
  }
  ```
* `AttendanceRevision`: Appends audit ledger record documenting checkpoint credit.
