# Digital Student Attendance System
## Offline and Synchronization Model

**Version:** 1.0  
**Primary goal:** Attendance must continue when internet is unavailable.

---

## 1. Core Principle

The system distinguishes three different connectivity states:

1. **Internet available**
2. **Internet unavailable, campus LAN/Wi-Fi available**
3. **Campus local server unavailable**

The university's local Wi-Fi does not need internet access for normal attendance.

---

## 2. Preferred Operating Mode

### Campus-local operation

Students and lecturers connect to the university Wi-Fi/LAN.

The local attendance server provides:

- Authentication/session validation
- Timetable
- Attendance sessions
- Token generation
- Token validation
- Attendance writes
- Reports needed locally
- Sync queue to cloud

External internet is optional.

---

## 3. Architecture Overview

```text
                    Optional Internet
                           |
                    Cloud / Backup
                           |
                     Sync Service
                           |
                 University Local Server
                 FastAPI + PostgreSQL
                           |
                    Campus LAN/Wi-Fi
              _____________|_____________
             |             |             |
        Lecturer Web   Mobile App     Admin PWA
             |             |
        Windows/Linux   Android/iOS
```

---

## 4. Connectivity Mode A
### Internet unavailable, local server available

This is a normal supported mode.

The system should continue:

- Login if local credentials/session policy permits
- Timetable access
- Attendance session start
- QR/token generation
- Bluetooth verification support
- Attendance submission
- Reporting
- Audit logging
- Local notifications

Cloud sync pauses and resumes later.

---

## 5. Connectivity Mode B
### Internet available, local server available

Normal local operation continues.

Additional functions:

- Cloud backup/sync
- Remote administration
- Remote reporting
- External integrations
- Software update checks
- Offsite disaster recovery replication

Attendance should still prefer local path for speed and resilience.

---

## 6. Connectivity Mode C
### Local server temporarily unavailable

This is a controlled fallback, not the primary mode.

An authorized lecturer mobile device may temporarily act as a local session authority.

Requirements:

- Lecturer authenticated before outage where possible
- Scheduled class data cached
- Device is authorized for the course/session
- Offline session has limited validity
- Offline token/session is signed
- Student attendance events are stored locally
- Events are immutable in local queue
- Events synchronize when local server returns
- All offline-originated records are flagged

---

## 7. Offline Lecturer Authority

The lecturer device must not gain unlimited authority.

It may only manage:

- Assigned class
- Allowed date/time window
- Specific attendance session
- Defined checkpoints

It may not:

- Create arbitrary students
- Change global policies
- Modify unrelated attendance
- Authorize itself for another course

---

## 8. Offline Student Behavior

Student mobile app may cache:

- User identity/session data
- Registered device credentials
- Current enrollment summary
- Today’s timetable where permitted
- Pending attendance submission receipts

Sensitive cached data should be minimized.

---

## 9. Synchronization Principles

Sync must be:

- Idempotent
- Auditable
- Conflict-aware
- Resumable
- Ordered where necessary
- Safe against duplicate submission

Every sync event should have a stable unique identifier.

---

## 10. Attendance Event Identity

Recommended event metadata:

- event_id
- student_id
- class_session_id
- checkpoint_id
- lecturer/session authority
- device registration ID
- creation time
- source mode
- token reference
- presence evidence summary
- signature/proof
- sync status
- server accepted time

---

## 11. Source Modes

Attendance event may be marked as:

- `LOCAL_SERVER`
- `LECTURER_OFFLINE_HOST`
- `PHYSICAL_CARD_FALLBACK`
- `MANUAL`
- `ADMIN_OVERRIDE`

Source mode must be preserved permanently.

---

## 12. Idempotency

Logical unique attendance constraint:

```text
student_id + class_session_id + checkpoint_id
```

If the same event is retried:

- It must not create duplicate credit.
- Server should return existing/accepted result where appropriate.

---

## 13. Conflict Examples

### Conflict A
Student submits same checkpoint twice.

**Resolution:** Keep one logical attendance result; preserve duplicate attempt log if relevant.

### Conflict B
Lecturer offline host marks Present, server already has Absent.

**Resolution:** Do not silently overwrite. Apply attendance conflict policy and require review if states cannot be automatically reconciled.

### Conflict C
Admin corrected record before delayed offline sync arrives.

**Resolution:** Admin correction should not be silently overwritten. Delayed event is attached to history and conflict review.

### Conflict D
Two offline lecturer devices attempt to host same class.

**Resolution:** Prevent where possible through pre-authorized session ownership. Otherwise require conflict review and choose authoritative session based on signed assignment/authorization.

---

## 14. Session Ownership

Each attendance session should have one authoritative host at a time.

Possible hosts:

- Local server
- Authorized lecturer device in fallback mode

Host transition must be logged.

---

## 15. Clock Handling

Student device clock is not authoritative.

Preferred timing:

- Local server time
- Signed local session time
- Monotonic elapsed time during offline lecturer-host mode

On sync, extreme clock drift should be flagged.

---

## 16. Offline Queue Security

Offline queue should:

- Use app-private storage
- Encrypt sensitive data where feasible
- Include tamper detection/signature
- Prevent casual editing
- Preserve original event IDs
- Track retry count and status

---

## 17. Sync States

Recommended states:

- Pending
- Sending
- Accepted
- Rejected
- Conflict
- Review Required
- Failed Retryable
- Failed Permanent

---

## 18. Cloud Synchronization

Cloud should receive:

- Attendance records
- Audit records
- Configuration snapshots where needed
- Backup data
- Aggregate reporting data

Local campus operation must not depend on immediate cloud acknowledgment.

---

## 19. Cloud Failure

If cloud is unavailable:

- Campus attendance continues.
- Local records remain authoritative for local operation.
- Sync backlog is monitored.
- Admin sees sync health warning.

---

## 20. Local Server Failure

If local server fails:

- Lecturer fallback mode may be enabled.
- Existing cached class assignments control authorization.
- Fallback is time-limited.
- Admin is notified when service returns.
- Sync reconciliation is mandatory.

---

## 21. Network Congestion

System should support:

- Short request payloads
- Retry with backoff
- Idempotent submission
- Local receipt to student
- Queueing where safe
- High concurrency during 3–5 minute checkpoint

---

## 22. Student Receipt

After successful attendance submission, student should receive a local/confirmed receipt showing:

- Course
- Checkpoint
- Status
- Time
- Confirmation state

Possible states:

- Confirmed by local server
- Pending sync
- Accepted after sync
- Rejected/review

---

## 23. Data Authority

Recommended order:

1. Valid admin-approved correction
2. Valid local-server record
3. Valid signed offline lecturer-host record
4. Manual/fallback record subject to policy

However, automatic precedence must never destroy conflicting historical evidence.

---

## 24. Recovery

After outage:

1. Local server becomes available.
2. Lecturer device reconnects.
3. Pending events are uploaded.
4. Server validates signatures/session ownership.
5. Duplicate events are deduplicated.
6. Conflicts are detected.
7. Accepted events are committed.
8. Review-required events enter admin queue.
9. Lecturer/student receipts are updated.
10. Audit log records recovery.

---

## 25. Backup and Restore Expectations

Local database must have:

- Automated backups
- Tested restore process
- Offsite/cloud copy when internet available
- Retention policy
- Backup monitoring

A backup that has never been tested for restore is not considered sufficient.

---

## 26. Offline Invariants

1. Internet outage must not stop campus attendance.
2. Student device clock cannot grant attendance.
3. Offline events must remain identifiable.
4. Offline events must be signed/tamper-evident where possible.
5. Sync must be idempotent.
6. Conflicts must not be silently overwritten.
7. One logical checkpoint cannot create duplicate credit.
8. Lecturer offline authority is limited to assigned sessions.
9. Cloud unavailability must not block local attendance.
10. Audit history must survive synchronization.
