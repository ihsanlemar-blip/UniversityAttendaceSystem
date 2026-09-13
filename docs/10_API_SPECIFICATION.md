# Digital Student Attendance System
## API Specification

**Version:** 1.0  
**Style:** REST  
**Base path:** `/api/v1`  
**Format:** JSON unless otherwise specified  
**Contract source:** FastAPI-generated OpenAPI

---

## 1. General Rules

- All endpoints require HTTPS.
- Authentication is required unless explicitly public.
- Authorization is server-side.
- IDs are UUIDs.
- Dates/times use ISO 8601.
- Server returns UTC timestamps.
- Client sends `Idempotency-Key` for retry-sensitive write operations.
- API responses include a request/correlation ID where practical.

---

## 2. Standard Error Format

```json
{
  "error": {
    "code": "ATTENDANCE_TOKEN_EXPIRED",
    "message": "The attendance token has expired.",
    "details": {},
    "request_id": "..."
  }
}
```

Do not expose internal stack traces.

---

## 3. Authentication

### POST `/auth/login`

Request:

```json
{
  "username": "2026-00123",
  "password": "..."
}
```

Response concept:

```json
{
  "user": {
    "id": "...",
    "display_name": "...",
    "roles": ["STUDENT"],
    "preferred_language": "ps"
  },
  "access_token": "...",
  "expires_in": 900,
  "refresh_context": "..."
}
```

For web/PWA, prefer secure HttpOnly cookie-based session/refresh handling where practical.

### POST `/auth/refresh`

Rotates refresh credential.

### POST `/auth/logout`

Revokes current refresh session.

### GET `/auth/me`

Returns authenticated identity, roles, scopes, and allowed client features.

---

## 4. Device Registration

### POST `/devices/registration-requests`

Creates initial/replacement registration request.

```json
{
  "request_type": "INITIAL",
  "public_key": "...",
  "public_key_fingerprint": "...",
  "platform": "ANDROID",
  "app_installation_id": "..."
}
```

### GET `/devices/me`

Returns current user's device registrations.

### POST `/devices/{device_id}/revoke`

Authorized revoke action.

### POST `/admin/device-registration-requests/{id}/approve`

Authorized approval.

### POST `/admin/device-registration-requests/{id}/reject`

Authorized rejection.

---

## 5. Academic Structure

### GET `/academic/units`
### POST `/academic/units`
### PATCH `/academic/units/{id}`

### GET `/academic-years`
### POST `/academic-years`

### GET `/semesters`
### POST `/semesters`

### GET `/courses`
### POST `/courses`
### PATCH `/courses/{id}`

### GET `/sections`
### POST `/sections`

### GET `/course-offerings`
### POST `/course-offerings`

### GET `/course-offerings/{id}/enrollments`

---

## 6. Students and Lecturers

### GET `/students`
Scoped admin listing.

### GET `/students/{id}`

### GET `/students/me`

### GET `/students/me/attendance`

Filters:

```text
semester_id
course_offering_id
from
to
```

### GET `/lecturers`

### GET `/lecturers/me/classes/today`

Returns class occurrences lecturer may operate today.

---

## 7. Scheduling

### GET `/schedule/today`

Role-aware schedule.

### GET `/class-occurrences/{id}`

### POST `/class-occurrences/{id}/cancel`

Requires reason.

### POST `/class-occurrences/{id}/reschedule`

### POST `/class-occurrences/{id}/assign-substitute`

Authorized only.

---

## 8. Attendance Session Lifecycle

### POST `/class-occurrences/{id}/attendance-session`

Creates/activates attendance session if allowed.

Must validate:

- class occurrence
- lecturer authorization
- time window
- cancellation state

### GET `/attendance-sessions/{id}`

### POST `/attendance-sessions/{id}/complete`

Completes session and calculates final records.

---

## 9. Checkpoint Lifecycle

### POST `/attendance-sessions/{id}/checkpoints/{checkpoint_id}/open`

Response concept:

```json
{
  "checkpoint_id": "...",
  "type": "START",
  "opened_at": "...",
  "closes_at": "...",
  "token_rotation_seconds": 30,
  "display_token": {
    "qr_payload": "...",
    "short_code": "482913"
  }
}
```

Short code may be omitted by policy.

### GET `/attendance-checkpoints/{id}/display-token`

Lecturer-only endpoint to obtain current display token.

### POST `/attendance-checkpoints/{id}/close`

### GET `/attendance-checkpoints/{id}/summary`

Lecturer/admin scoped.

---

## 10. Student Attendance Submission

### POST `/attendance-checkpoints/{id}/submit`

Headers:

```text
Authorization
Idempotency-Key
X-Device-Registration
```

Request concept:

```json
{
  "token": "...",
  "device_proof": {
    "signature": "...",
    "nonce": "..."
  },
  "presence": {
    "campus_network_proof": "...",
    "bluetooth_proof": "..."
  },
  "client_event_id": "...",
  "client_observed_at": "..."
}
```

Server validates:

1. Student authentication
2. Enrollment
3. Active checkpoint
4. Token
5. Device registration/signature
6. Campus network proof
7. Bluetooth proof according to policy
8. Duplicate request
9. Risk rules

Response:

```json
{
  "status": "CONFIRMED",
  "checkpoint_result": "PRESENT",
  "confidence": "HIGH",
  "server_received_at": "...",
  "receipt_id": "..."
}
```

Possible states:

- CONFIRMED
- PENDING_REVIEW
- REJECTED

---

## 11. Physical Card Fallback

### POST `/attendance-checkpoints/{id}/physical-card`

Lecturer/attendance officer only.

Request:

```json
{
  "card_credential": "...",
  "reason": "NO_SMARTPHONE"
}
```

Server verifies:

- active card
- enrolled student
- open checkpoint
- authorized scanner

---

## 12. Manual Attendance

### POST `/attendance-checkpoints/{id}/manual`

Request:

```json
{
  "student_id": "...",
  "status": "PRESENT",
  "reason": "Student phone battery failed"
}
```

Must create audit event.

---

## 13. Corrections

### POST `/attendance-records/{id}/correction-requests`

```json
{
  "requested_status": "PRESENT",
  "reason": "Attendance was incorrectly recorded."
}
```

### GET `/attendance-corrections`

Scoped queue.

### POST `/attendance-corrections/{id}/approve`

### POST `/attendance-corrections/{id}/reject`

### POST `/attendance-records/{id}/admin-override`

Authorized only; reason required.

---

## 14. Policies

### GET `/attendance-policies`

### POST `/attendance-policies`

### PATCH `/attendance-policies/{id}`

Policy change should not silently reinterpret historic records.

---

## 15. Reports

### GET `/reports/students/{student_id}/attendance`
### GET `/reports/course-offerings/{id}/attendance`
### GET `/reports/sections/{id}/attendance`
### GET `/reports/departments/{id}/attendance`
### GET `/reports/faculties/{id}/attendance`
### GET `/reports/low-attendance`
### GET `/reports/lecturer-activity`
### GET `/reports/suspicious-attendance`
### GET `/reports/manual-attendance`
### GET `/reports/corrections`

Exports may use:

```text
?format=csv
?format=xlsx
```

PDF may be added where required.

---

## 16. Audit

### GET `/audit/events`

Filters:

```text
actor_user_id
target_type
target_id
action
from
to
```

Access tightly scoped.

---

## 17. Risk Review

### GET `/risk-flags`

### GET `/risk-flags/{id}`

### POST `/risk-flags/{id}/resolve`

Requires resolution note.

---

## 18. Imports

### POST `/imports`

Multipart file upload.

Supported types:

- STUDENTS
- LECTURERS
- COURSES
- SECTIONS
- ENROLLMENTS
- TIMETABLE

### GET `/imports/{id}`

### GET `/imports/{id}/rows`

### POST `/imports/{id}/commit`

Import should support validation/preview before commit.

---

## 19. Notifications

### GET `/notifications`

### POST `/notifications/{id}/read`

---

## 20. Offline Session Permits

### POST `/attendance-sessions/{id}/offline-permit`

Lecturer device requests a signed offline permit while campus server is available.

### POST `/offline-sync/attendance-events`

Uploads signed offline-host events.

Request contains:

```json
{
  "permit": "...",
  "events": [...]
}
```

Server:

- verifies permit
- verifies device signatures
- deduplicates events
- identifies conflicts
- returns per-event result

---

## 21. Synchronization

Internal or authenticated system endpoints:

### POST `/sync/events`
### GET `/sync/status`

These should not be exposed to ordinary student clients.

---

## 22. Health

### GET `/health/live`

Process is alive.

### GET `/health/ready`

Required dependencies available.

### GET `/health/sync`

Authorized diagnostic endpoint.

---

## 23. Common HTTP Status Usage

```text
200 OK
201 Created
202 Accepted
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Validation Error
429 Too Many Requests
503 Service Unavailable
```

---

## 24. Important Error Codes

Examples:

```text
AUTH_INVALID_CREDENTIALS
AUTH_ACCOUNT_DISABLED
DEVICE_NOT_REGISTERED
DEVICE_REVOKED
DEVICE_SIGNATURE_INVALID
ATTENDANCE_SESSION_NOT_ACTIVE
ATTENDANCE_CHECKPOINT_CLOSED
ATTENDANCE_TOKEN_EXPIRED
ATTENDANCE_TOKEN_INVALID
ATTENDANCE_NOT_ENROLLED
ATTENDANCE_DUPLICATE
ATTENDANCE_OFF_CAMPUS
ATTENDANCE_BLUETOOTH_REQUIRED
ATTENDANCE_PENDING_REVIEW
CORRECTION_WINDOW_EXPIRED
OFFLINE_PERMIT_INVALID
OFFLINE_SYNC_CONFLICT
PERMISSION_DENIED
```

---

## 25. API Compatibility

- Breaking changes require `/api/v2` or an approved compatibility strategy.
- OpenAPI contract should be committed/snapshotted for client generation.
- Flutter and web clients should use generated or strongly typed API models where practical.
