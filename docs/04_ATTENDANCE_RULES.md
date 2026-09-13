# Digital Student Attendance System
## Attendance Rules

**Version:** 1.0  
**Purpose:** Define the official attendance behavior and configurable policy model.

---

## 1. Core Model

Each scheduled class uses up to three attendance checkpoints:

1. **Start**
2. **Middle**
3. **End**

These checkpoints help distinguish:

- Full attendance
- Late arrival
- Early departure
- Partial attendance
- Absence

The final result must be calculated through configurable policy rather than hard-coded logic.

---

## 2. Default Checkpoint Policy

Recommended initial policy:

- Start checkpoint: near class beginning
- Middle checkpoint: around the midpoint
- End checkpoint: near class end
- Each checkpoint window: 3–5 minutes
- Token rotation: 20–30 seconds
- All values configurable

---

## 3. Suggested Combination Interpretation

| Checkpoints | Suggested interpretation |
|---|---|
| Start + Middle + End | Full attendance |
| Any 2 of 3 | Partial/full attendance depending on policy |
| Start only | Possible early departure |
| Middle only | Late arrival / partial attendance |
| End only | Very late / normally insufficient |
| None | Absent |

The system must not hard-code this table as final policy.

---

## 4. Attendance Statuses

Supported statuses:

- Present
- Late
- Absent
- Excused
- Leave
- Pending / Unverified

Additional metadata flags:

- Manual
- Physical-card fallback
- Offline-created
- Corrected
- Suspicious
- Conflict-review

---

## 5. Late Rule

Default recommendation:

- A student who completes the first checkpoint within the first 10 minutes of class may receive normal first-checkpoint credit.
- After the late threshold, the student may be marked Late depending on policy.

Late threshold must be configurable.

---

## 6. Attendance Percentage

Recommended default minimum attendance requirement:

**75%**

It must be configurable at:

- University
- Faculty
- Program
- Course

Policy precedence should be deterministic.

Suggested precedence:

Course override  
→ Program override  
→ Faculty override  
→ University default

---

## 7. Checkpoint Credit

The system should support configurable checkpoint weights.

Example only:

- Start = 1 credit
- Middle = 1 credit
- End = 1 credit

Possible final score:

```text
completed_checkpoint_weight / total_checkpoint_weight
```

However, policy may choose categorical rules instead.

---

## 8. Present Rule

A student may receive Present only when:

- Student is enrolled in the course offering.
- Attendance checkpoint submission is valid.
- Required presence checks pass.
- Final checkpoint combination satisfies policy.

---

## 9. Absent Rule

Absent may be assigned when:

- No valid checkpoint is completed.
- Completed checkpoints do not satisfy minimum policy.
- Attendance was invalidated after review.
- Student did not have approved Excused/Leave status.

---

## 10. Excused Absence

Excused status should require:

- Authorized reason
- Supporting evidence if university policy requires
- Approval by permitted role
- Audit record

Excused attendance may or may not count toward attendance percentage according to policy.

---

## 11. Leave

Leave should be handled separately from Excused if university policy distinguishes them.

Configurable options:

- Counts as absence
- Excluded from denominator
- Counts as approved attendance category

---

## 12. Manual Attendance

Manual attendance is allowed only for exceptional cases.

Requirements:

- Lecturer/authorized staff
- Mandatory reason
- Audit event
- Manual flag
- Reviewable report
- Optional admin approval for high-risk cases

---

## 13. Physical QR Card Attendance

Rules:

- Student presents physical card.
- Authorized lecturer/officer scans card.
- System verifies enrollment and active card.
- Record is flagged as fallback.
- Frequent fallback use may be flagged.

A copied image of the card should not independently prove physical presence.

---

## 14. Correction Window

Default lecturer correction window:

**24 hours**

Configurable.

Every correction must preserve:

- Original value
- New value
- Actor
- Date/time
- Reason
- Related class/session
- Device/context where available

---

## 15. Administrator Override

Authorized admin may override attendance.

Requirements:

- Reason
- Permanent audit
- Original value preserved
- Scope authorization
- Optional second approval

---

## 16. Class Cancellation

Cancelled class should:

- Not count as absence
- Not create normal attendance expectation
- Preserve cancellation reason
- Record who cancelled
- Support replacement/make-up class

---

## 17. Rescheduled Class

Rescheduled class must have:

- New date/time
- New room where applicable
- Lecturer assignment
- Student visibility
- Fresh attendance sessions
- Audit history linking original and rescheduled class

---

## 18. Substitute Lecturer

Authorized substitute lecturer may:

- Access assigned temporary session
- Start checkpoints
- Record attendance
- Be clearly identified in audit history

---

## 19. Merged Sections

Merged classes must preserve:

- Original student enrollments
- Original section identity
- Shared physical session
- Correct per-course/per-section reporting

---

## 20. Duplicate Submission

A student may not receive duplicate credit for the same checkpoint.

Duplicate submissions should:

- Be rejected or idempotently accepted
- Be logged if suspicious
- Never create multiple attendance credits

---

## 21. Wrong Course/Section

Attendance must fail when:

- Student is not enrolled.
- Session belongs to another section.
- Token is from another checkpoint/class.
- Session is outside allowed time.

---

## 22. Attendance Outside Campus

Default policy:

Attendance should not be accepted if required campus-presence checks fail.

Possible exception:

- Authorized remote/online class
- Admin-approved special session

Such exceptions must be explicit and auditable.

---

## 23. Policy Configuration

The following should be configurable:

- Checkpoint count
- Checkpoint names
- Checkpoint timing
- Checkpoint duration
- Token rotation interval
- Late threshold
- Minimum attendance percentage
- Checkpoint weighting
- Final status mapping
- Correction window
- Required presence signals
- Manual fallback rules
- Physical card rules
- Exception approval rules

---

## 24. Example Policy

Example only:

```text
3/3 checkpoints -> Present
2/3 checkpoints -> Present with partial credit or Late, depending on which checkpoints
Start + Middle -> Early departure warning
Middle + End -> Late
Start only -> Partial / insufficient
Middle only -> Partial / insufficient
End only -> Insufficient
0/3 -> Absent
```

The university must be able to change these mappings without code changes.

---

## 25. Audit Invariant

No attendance correction or override may silently destroy the original attendance state.
