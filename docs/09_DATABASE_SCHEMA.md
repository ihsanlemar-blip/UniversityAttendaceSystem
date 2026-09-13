# Digital Student Attendance System
## Database Schema Specification

**Version:** 1.0  
**Database:** PostgreSQL  
**Time policy:** Store timestamps in UTC; render in configured university timezone  
**ID policy:** UUID identifiers, UUIDv7 preferred where supported by the application stack

---

## 1. General Conventions

All primary tables should normally contain:

```text
id UUID PRIMARY KEY
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

Where relevant:

```text
created_by UUID
updated_by UUID
deleted_at TIMESTAMPTZ NULL
```

Use soft deletion only where historical references matter. Attendance/audit records should not be casually deleted.

Naming:

- snake_case
- plural table names
- explicit foreign keys
- database constraints for critical invariants

---

## 2. Core Identity Tables

### users

```text
id
university_id
username
password_hash
email nullable
phone nullable
preferred_language
status
last_login_at nullable
created_at
updated_at
```

Constraints:

- unique `(university_id, username)`

### roles

```text
id
code
name
is_system
```

### permissions

```text
id
code
description
```

### role_permissions

```text
role_id
permission_id
```

Unique:

- `(role_id, permission_id)`

### role_assignments

```text
id
user_id
role_id
scope_type
scope_id nullable
starts_at nullable
ends_at nullable
created_at
```

---

## 3. University Structure

### universities

```text
id
name
code
timezone
default_language
status
created_at
updated_at
```

### academic_units

Flexible hierarchy.

```text
id
university_id
parent_id nullable
unit_type
code
name
status
created_at
updated_at
```

Indexes:

- `(university_id, parent_id)`
- `(university_id, unit_type)`

### academic_years

```text
id
university_id
name
start_date
end_date
status
```

### semesters

```text
id
academic_year_id
name
sequence_no
start_date
end_date
status
```

### sections

```text
id
university_id
academic_unit_id nullable
semester_id nullable
code
name
status
```

---

## 4. People

### students

```text
id
user_id UNIQUE
university_id
student_number
academic_unit_id nullable
section_id nullable
status
admission_date nullable
created_at
updated_at
```

Unique:

- `(university_id, student_number)`

### lecturers

```text
id
user_id UNIQUE
university_id
employee_code
academic_unit_id nullable
status
created_at
updated_at
```

Unique:

- `(university_id, employee_code)`

### staff_profiles

Optional.

```text
id
user_id UNIQUE
university_id
employee_code nullable
academic_unit_id nullable
status
```

---

## 5. Courses and Offerings

### courses

```text
id
university_id
academic_unit_id nullable
code
title
credit_hours nullable
status
created_at
updated_at
```

Unique:

- `(university_id, code)`

### course_offerings

```text
id
course_id
semester_id
section_id nullable
academic_unit_id nullable
attendance_policy_id nullable
status
created_at
updated_at
```

### lecturer_assignments

```text
id
course_offering_id
lecturer_id
assignment_type
starts_at nullable
ends_at nullable
status
```

Unique active assignment rules should be handled through application validation plus targeted indexes.

### enrollments

```text
id
course_offering_id
student_id
status
enrolled_at
ended_at nullable
```

Unique:

- `(course_offering_id, student_id)`

---

## 6. Rooms and Scheduling

### rooms

```text
id
university_id
code
name
building nullable
floor nullable
capacity nullable
status
```

### timetable_rules

```text
id
course_offering_id
room_id nullable
weekday
start_time
end_time
valid_from
valid_to
recurrence_rule nullable
status
```

### class_occurrences

```text
id
timetable_rule_id nullable
course_offering_id
room_id nullable
scheduled_start
scheduled_end
actual_start nullable
actual_end nullable
status
cancellation_reason nullable
rescheduled_from_id nullable
substitute_lecturer_id nullable
created_at
updated_at
```

Indexes:

- `(course_offering_id, scheduled_start)`
- `(scheduled_start, status)`

---

## 7. Attendance Policy

### attendance_policies

```text
id
university_id
name
scope_type
scope_id nullable
minimum_percentage
late_threshold_minutes
lecturer_correction_hours
required_checkpoint_count
token_rotation_seconds
default_checkpoint_duration_seconds
required_presence_signals JSONB
status_mapping JSONB
checkpoint_weights JSONB
effective_from nullable
effective_to nullable
created_at
updated_at
```

Policies are versioned through new records or explicit policy versioning; avoid silently changing historical semantics.

---

## 8. Attendance Session Tables

### attendance_sessions

```text
id
class_occurrence_id UNIQUE
attendance_policy_id
state
host_type
host_device_id nullable
started_by_user_id nullable
started_at nullable
completed_at nullable
cancelled_at nullable
created_at
updated_at
```

Host types:

```text
LOCAL_SERVER
LECTURER_OFFLINE_HOST
```

### attendance_checkpoints

```text
id
attendance_session_id
checkpoint_type
sequence_no
planned_open_at
planned_close_at
opened_at nullable
closed_at nullable
state
token_epoch_anchor nullable
created_at
updated_at
```

Unique:

- `(attendance_session_id, sequence_no)`

Indexes:

- `(attendance_session_id, state)`

---

## 9. Attendance Evidence and Results

### attendance_evidence

Append-oriented evidence table.

```text
id
attendance_checkpoint_id
student_id
submitted_by_user_id
registered_device_id nullable
source_mode
submitted_at
server_received_at
token_time_step nullable
token_nonce_hash nullable
network_verified boolean
bluetooth_verified boolean
device_signature_verified boolean
manual_verified boolean
physical_card_id nullable
offline_permit_id nullable
risk_score nullable
evidence_summary JSONB
request_id
created_at
```

Unique:

- `request_id`

Indexes:

- `(attendance_checkpoint_id, student_id)`
- `(student_id, submitted_at)`
- `(source_mode, submitted_at)`

Do not store raw secrets.

### attendance_checkpoint_results

```text
id
attendance_checkpoint_id
student_id
status
confidence_level
accepted_evidence_id nullable
is_manual
is_fallback
is_offline
risk_state
calculated_at
created_at
updated_at
```

Critical unique constraint:

```text
UNIQUE(attendance_checkpoint_id, student_id)
```

### attendance_records

Final class-level result.

```text
id
attendance_session_id
student_id
final_status
attendance_credit
percentage_value nullable
calculation_snapshot JSONB
calculated_at
version_no
created_at
updated_at
```

Critical unique:

```text
UNIQUE(attendance_session_id, student_id)
```

---

## 10. Corrections

### attendance_corrections

```text
id
attendance_record_id nullable
attendance_checkpoint_result_id nullable
requested_by_user_id
approved_by_user_id nullable
correction_type
before_snapshot JSONB
after_snapshot JSONB
reason
status
requested_at
approved_at nullable
applied_at nullable
created_at
```

Constraints:

- Must reference at least one target.
- Reason not empty.

---

## 11. Device Trust

### registered_devices

```text
id
user_id
device_type
platform
public_key
public_key_fingerprint
app_installation_id
status
registered_at
revoked_at nullable
revocation_reason nullable
last_seen_at nullable
created_at
updated_at
```

Indexes:

- `(user_id, status)`
- `(public_key_fingerprint)`

Policy should enforce one active primary student device at the service layer.

### device_registration_requests

```text
id
user_id
request_type
old_device_id nullable
new_public_key
new_public_key_fingerprint
reason nullable
status
requested_at
reviewed_by_user_id nullable
reviewed_at nullable
```

---

## 12. Physical Cards

### physical_cards

```text
id
student_id
credential_id
credential_public_reference
status
issued_at
revoked_at nullable
revocation_reason nullable
created_at
```

Unique:

- `credential_id`

Do not put sensitive student data directly in QR.

---

## 13. Offline Permits

### offline_session_permits

```text
id
attendance_session_id
lecturer_id
registered_device_id
permit_payload_hash
issued_at
valid_from
valid_until
status
revoked_at nullable
server_signature
created_at
```

Unique:

- active permit per `(attendance_session_id, registered_device_id)` where policy requires

---

## 14. Risk and Security Events

### risk_flags

```text
id
university_id
user_id nullable
student_id nullable
lecturer_id nullable
attendance_session_id nullable
flag_type
severity
score nullable
details JSONB
status
created_at
reviewed_by_user_id nullable
reviewed_at nullable
resolution nullable
```

Indexes:

- `(status, severity, created_at)`
- `(student_id, created_at)`
- `(lecturer_id, created_at)`

---

## 15. Audit

### audit_events

Append-only from application perspective.

```text
id
university_id
actor_user_id nullable
actor_role_code nullable
action
target_type
target_id nullable
before_data JSONB nullable
after_data JSONB nullable
reason nullable
device_id nullable
attendance_session_id nullable
request_id nullable
ip_address nullable
created_at
hash_prev nullable
hash_current nullable
```

Indexes:

- `(target_type, target_id, created_at)`
- `(actor_user_id, created_at)`
- `(action, created_at)`

Optional hash chaining may be used for stronger tamper evidence.

---

## 16. Notifications

### notifications

```text
id
user_id
type
title_key
body_key
payload JSONB
status
created_at
read_at nullable
```

---

## 17. Imports

### import_jobs

```text
id
university_id
import_type
file_name
started_by_user_id
status
total_rows
valid_rows
invalid_rows
created_rows
updated_rows
started_at
completed_at nullable
summary JSONB
```

### import_row_results

```text
id
import_job_id
row_number
status
entity_type nullable
entity_id nullable
errors JSONB nullable
normalized_data JSONB nullable
```

---

## 18. Synchronization

### outbox_events

```text
id
event_type
aggregate_type
aggregate_id
payload JSONB
created_at
published_at nullable
attempt_count
last_error nullable
```

Indexes:

- `(published_at, created_at)`

### sync_inbox_records

```text
id
source_system
event_id
received_at
processed_at nullable
status
error nullable
```

Unique:

- `(source_system, event_id)`

### sync_conflicts

```text
id
entity_type
entity_id
local_snapshot JSONB
remote_snapshot JSONB
conflict_type
status
created_at
resolved_by_user_id nullable
resolved_at nullable
resolution nullable
```

---

## 19. Authentication Support Tables

Recommended implementation may include:

### refresh_sessions

```text
id
user_id
device_id nullable
token_family_id
refresh_token_hash
expires_at
revoked_at nullable
created_at
last_used_at nullable
```

Never store raw refresh tokens.

### login_attempts

```text
id
username_hash_or_identifier
success
ip_address nullable
device_context nullable
created_at
```

Retention should be limited by security policy.

---

## 20. Critical Database Constraints

At minimum:

1. Enrollment unique per student/course offering.
2. Attendance session unique per class occurrence.
3. Checkpoint sequence unique per attendance session.
4. Checkpoint result unique per student/checkpoint.
5. Attendance record unique per student/session.
6. Evidence request ID unique.
7. Physical card credential unique.
8. Username unique within university.
9. Student number unique within university.
10. Course code unique within university.

---

## 21. Index Strategy

High-value indexes include:

```text
enrollments(course_offering_id, student_id)
class_occurrences(course_offering_id, scheduled_start)
attendance_checkpoints(attendance_session_id, state)
attendance_checkpoint_results(attendance_checkpoint_id, student_id)
attendance_records(attendance_session_id, student_id)
attendance_evidence(student_id, submitted_at)
risk_flags(status, severity, created_at)
audit_events(target_type, target_id, created_at)
outbox_events(published_at, created_at)
```

Actual indexes must be validated using query plans and load testing.

---

## 22. Data Retention

Attendance and audit records should be retained according to university/legal policy.

V1 recommendation:

- Do not automatically delete academic attendance history.
- Keep audit history at least as long as attendance records.
- Security telemetry may have shorter configurable retention.
- Raw transient Bluetooth/network data should be minimized.

---

## 23. Migration Rules

All schema changes require:

- Alembic migration
- Forward migration test
- Upgrade from previous schema
- Backup before production migration
- Review for destructive operations
- Rollback/repair strategy

Never allow an AI agent to edit production tables manually as a substitute for a migration.
