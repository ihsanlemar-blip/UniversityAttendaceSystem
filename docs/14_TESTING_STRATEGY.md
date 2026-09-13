# Digital Student Attendance System
## Testing Strategy

**Version:** 1.0  
**Goal:** Prove correctness, security, offline resilience, and usability before university-wide rollout.

---

## 1. Testing Layers

```text
Unit
  ↓
Domain / Service
  ↓
Database Integration
  ↓
API Integration
  ↓
Client Integration
  ↓
End-to-End
  ↓
Offline / Sync
  ↓
Security
  ↓
Load / Reliability
  ↓
Pilot UAT
```

---

## 2. Backend Unit Tests

Framework:

- pytest

Test:

- Attendance policy calculations
- Checkpoint status logic
- Late rules
- Percentage calculations
- Scope/role decisions
- Token generation/validation
- Risk scoring
- Correction-window logic

---

## 3. Database Integration Tests

Use real PostgreSQL test instance/container.

Test:

- Unique enrollment
- Unique student/checkpoint result
- Unique student/session attendance record
- Transaction rollback
- Migration upgrade
- Referential integrity
- Concurrent attendance submission

SQLite must not substitute for PostgreSQL in backend integration tests.

---

## 4. API Tests

Test:

- Authentication
- Authorization
- Scope enforcement
- Validation
- Error codes
- Idempotency
- Pagination
- Token expiry
- Duplicate request
- Wrong device
- Wrong class
- Closed checkpoint

---

## 5. Web Tests

Recommended:

- Vitest for unit/component tests
- Playwright for E2E

Test:

- Admin login
- Role-based navigation
- Academic structure CRUD
- Timetable
- Policy configuration
- Corrections
- Reports
- Imports
- RTL layouts
- Permission denial

---

## 6. Flutter Tests

Use:

- Dart unit tests
- Widget tests
- Integration tests

Test:

- Login/session
- Device registration
- Attendance flow
- QR scanning abstraction
- Bluetooth abstraction
- Local DB
- Offline receipt
- Reconnect/sync
- Lecturer checkpoint control
- Physical-card scan
- Language/RTL UI

---

## 7. Attendance Critical Test Matrix

### Valid attendance

- Correct student
- Enrolled
- Open checkpoint
- Valid token
- Registered device
- Campus network
- Bluetooth valid

Expected: Confirmed.

### Expired QR

Expected: Rejected.

### QR screenshot shared outside campus

Expected: Presence validation fails or record enters review according to policy.

### Same student submits twice

Expected: One logical result only.

### One device signs for another account

Expected: Reject/flag.

### Student not enrolled

Expected: Reject.

### Wrong section

Expected: Reject.

### Checkpoint closed

Expected: Reject normal submission.

### Lecturer manual override

Expected: Accepted only with permission + reason + audit.

---

## 8. Three-Checkpoint Tests

Test all combinations:

```text
111
110
101
011
100
010
001
000
```

Where:

```text
1 = valid checkpoint
0 = missing/invalid
```

Run each against configurable policy mapping.

Do not assume 2/3 always means Present.

---

## 9. Offline Tests

### Internet outage

Campus server available.

Expected:

- Attendance continues normally.

### Cloud unavailable

Expected:

- Local attendance continues.
- Outbox grows.
- Sync resumes later.

### Local server unavailable

Expected:

- Authorized lecturer offline-host mode only.
- Permit limits enforced.
- Events queued.
- Events synchronize later.

### Duplicate sync

Expected:

- No duplicate attendance credit.

### Conflict sync

Expected:

- Conflict detected.
- No silent overwrite.

---

## 10. Time Manipulation Tests

- Student clock 2 hours ahead
- Student clock 1 day behind
- Lecturer phone clock incorrect
- Server clock corrected after drift

Expected:

- Student clock cannot make expired token valid.
- Server/offline permit timing remains authoritative.

---

## 11. Device Security Tests

- Revoked device submits
- Replaced device submits
- Invalid signature
- Modified request after signature
- Frequent device reset
- Same key reused across accounts

Expected:

- Reject or flag according to policy.

---

## 12. Permission Tests

Create automated matrix.

For each role, test:

- Allowed action succeeds.
- Disallowed action returns 403.
- Cross-faculty/department access denied.
- Lecturer cannot edit another lecturer's class.
- Student cannot see another student's attendance.

---

## 13. Audit Tests

For sensitive actions verify:

- Audit row created.
- Correct actor.
- Correct before/after.
- Reason stored.
- Timestamp stored.
- Original history remains.

---

## 14. Import Tests

- Valid file
- Missing column
- Duplicate student number
- Invalid course
- Invalid date
- 1,000+ rows
- Partial errors
- Preview before commit
- Re-run same file

---

## 15. Load Testing

Recommended tool:

- k6 or equivalent

Scenarios:

### Burst checkpoint

Simulate:

- 100 students submitting within 30 seconds
- Multiple classes simultaneously

### University burst

Simulate several concurrent classes across departments.

Measure:

- p50/p95/p99 latency
- Error rate
- DB connections
- CPU
- memory
- lock contention

---

## 16. Reliability Tests

- Restart backend during non-critical period
- Restart worker
- Redis outage
- Cloud sync outage
- Local network packet loss
- Duplicate client retries
- Low mobile connectivity
- Disk-near-full warning

---

## 17. Security Testing

At minimum:

- Secret scan
- Dependency scan
- Authorization abuse tests
- Input fuzzing for critical endpoints
- Rate-limit tests
- CSRF tests for web if relevant
- XSS tests
- SQL injection verification
- Token replay tests
- Privilege escalation tests

Optional tooling:

- OWASP ZAP
- dependency scanners
- static analysis

---

## 18. Backup / Restore Test

Before production:

1. Create backup.
2. Restore to clean environment.
3. Verify users.
4. Verify academic structure.
5. Verify attendance history.
6. Verify audit history.
7. Document restore duration.

Backup without tested restore is not accepted.

---

## 19. Pilot UAT

Pilot:

- 100–200 students
- 3–5 lecturers
- 2–4 weeks

Collect:

- Checkpoint completion time
- Failure rate
- Bluetooth failure rate
- Manual fallback rate
- QR-sharing attempts
- Device-reset requests
- Lecturer feedback
- Student feedback
- Sync incidents

---

## 20. Exit Criteria

Before full rollout:

- No unresolved critical security issue.
- No known data-loss bug.
- No duplicate-credit bug.
- Permission matrix passes.
- Offline mode validated.
- Sync conflict process validated.
- Backup restore validated.
- Load test meets agreed target.
- Pilot users can complete attendance reliably.
- Major false-positive anti-cheating issues resolved.
