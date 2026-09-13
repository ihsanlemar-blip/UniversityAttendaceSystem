# Digital Student Attendance System
## Anti-Cheating and Presence Model

**Version:** 1.0  
**Security objective:** Make ordinary proxy attendance materially difficult, detectable, and auditable without creating excessive friction.

---

## 1. Security Philosophy

The system must not trust one signal alone.

Attendance confidence is built by combining:

- Correct schedule
- Correct enrollment
- Valid signed token
- Correct checkpoint window
- Registered device
- Campus network presence
- Bluetooth proximity
- Duplicate/device-abuse checks
- Lecturer authorization
- Audit evidence

No single factor proves attendance by itself.

---

## 2. Threats

The system should consider:

1. Student shares QR screenshot.
2. Student sends numeric code through WhatsApp.
3. Student gives credentials to another student.
4. One phone is used for multiple accounts.
5. Student checks in from outside campus.
6. Student checks in and leaves immediately.
7. Student changes phone frequently to bypass controls.
8. Student replays old QR/token.
9. Student uses wrong class/section token.
10. Lecturer mass-marks attendance.
11. Lecturer opens fake/unscheduled class.
12. Lecturer changes attendance later without justification.
13. Physical QR card is photographed/copied.
14. Local clock is manipulated.
15. Offline data is modified before synchronization.
16. Duplicate attendance is submitted during sync.

---

## 3. Dynamic QR / Token Security

Each QR/token must:

- Be short-lived.
- Be signed.
- Be checkpoint-specific.
- Be class/session-specific.
- Include expiry.
- Include nonce/randomness.
- Be unusable after expiry.
- Be validated by trusted server/authorized offline host.
- Not expose sensitive personal data.

Default rotation: 20–30 seconds.

---

## 4. Numeric Fallback Code

If used:

- Same short lifetime as QR
- Bound to current checkpoint
- Rate-limited
- Cannot be static per course
- Must be combined with other presence checks

Numeric code alone must never be sufficient for high-confidence attendance.

---

## 5. Campus Network Presence

The system should verify that the student's device is connected to the university's trusted local network.

Possible techniques may include:

- Access through local-only endpoint
- Trusted LAN routing
- Internal DNS/service discovery
- Network-issued short-lived proof
- Authorized Wi-Fi infrastructure integration

Do not rely only on SSID name because SSIDs can be imitated.

---

## 6. Bluetooth Proximity

Bluetooth is a supporting signal.

Possible model:

- Lecturer-authorized device or classroom beacon advertises rotating proximity identifier.
- Student app detects identifier during checkpoint.
- App submits proof tied to checkpoint/session.
- Server validates allowed timing and nonce relationship.

Requirements:

- Rotating identifiers
- No permanent public Bluetooth identifier
- Time-bound proof
- Replay resistance
- Failure fallback

Bluetooth alone is not enough.

---

## 7. Device Registration

Use application-level cryptographic device registration.

Possible approach:

- App creates key pair.
- Public key registered to student account.
- Private key stored in secure OS storage.
- Attendance request is signed by registered device.
- Server verifies signature.

Benefits:

- Stronger than raw device ID
- Better privacy
- Detectable device changes
- Harder to impersonate remotely

---

## 8. One Account / One Primary Device

Default:

- One active primary student device.

Device change requires:

- Authenticated request
- Verification
- Admin or approved recovery workflow
- Old-device revocation
- Audit record

Frequent device changes should produce a risk flag.

---

## 9. One Device / Multiple Accounts

System should detect:

- Multiple student accounts using same registered device
- Rapid account switching
- Multiple device keys from same installation where detectable
- Repeated attendance submissions from one device for many students

Suspicious behavior should be flagged, not always automatically punished, because shared/family devices may create legitimate exceptions.

---

## 10. Three-Checkpoint Anti-Cheating Value

Three checkpoints reduce:

- Check-in-and-leave behavior
- Proxy check-in at class start only
- One-time code sharing
- Short physical presence used to obtain full credit

Patterns such as:

- Start only
- Start + no middle/end
- End only

may generate policy-specific status or risk flags.

---

## 11. Physical QR Card Security

Physical card:

- Must contain unique signed identifier.
- Should be revocable.
- Should not include secret credentials.
- Should normally be scanned by lecturer/authorized staff.
- Should produce fallback attendance flag.

Potential additional controls:

- Card photo/name displayed to lecturer
- Random manual identity check
- Repeated fallback frequency alert

---

## 12. Lecturer Fraud Controls

System should flag:

- Sessions started outside schedule
- Sessions started outside campus
- Excessive manual attendance
- Large batches of corrections
- Repeated cancellation patterns
- Unusually high fallback-card use
- Attendance recorded after allowed window
- Many students marked present without normal evidence

High-risk actions should require reason and be auditable.

---

## 13. Time Integrity

Server/local authorized host should be authoritative for checkpoint timing.

Student device clock should not determine token validity.

Offline lecturer-host mode should use:

- Trusted monotonic timing where possible
- Signed session start timestamp
- Restricted offline duration
- Sync validation

---

## 14. Replay Protection

Attendance requests should include:

- Session ID
- Checkpoint ID
- Token nonce
- Device signature
- Timestamp or server challenge
- Unique submission ID

Previously accepted token/submission combinations should not be reusable.

---

## 15. Duplicate Protection

Use idempotent attendance submission.

Unique logical constraint should prevent duplicate credit for:

```text
student + class_session + checkpoint
```

Duplicate network retries may return the same result without creating multiple records.

---

## 16. GPS Policy

GPS is not the primary signal.

Optional use:

- Secondary evidence
- Special investigation
- Configurable university policy

Do not continuously track student location.

Do not make indoor GPS accuracy a mandatory condition for normal attendance.

---

## 17. Risk Scoring

The system may assign a risk score based on:

- New device
- Frequent device reset
- Missing Bluetooth
- Unusual network
- Manual fallback
- Repeated late submissions
- Same device used by multiple accounts
- Repeated attendance corrections
- Offline-originated events
- Suspicious lecturer behavior

Risk score should support review and should not automatically accuse a user of cheating.

---

## 18. False Positive Principle

Anti-cheating mechanisms must tolerate real operational failures.

Examples:

- Bluetooth unavailable
- Student phone battery low
- Local network congestion
- Accessibility need
- Device lost
- Lecturer laptop failure

Fallback paths must exist and be auditable.

---

## 19. Privacy Principles

Avoid:

- Facial recognition in V1
- Continuous GPS
- Unnecessary device fingerprinting
- Storing raw Bluetooth history beyond operational need
- Sensitive personal data inside QR codes

Collect only what is necessary for attendance integrity and audit.

---

## 20. Presence Confidence Levels

Suggested internal model:

### High Confidence
- Valid token
- Registered device
- Campus network verified
- Bluetooth verified
- Correct time/enrollment

### Medium Confidence
- Valid token
- Registered device
- Campus network verified
- Bluetooth unavailable

### Fallback Confidence
- Physical card/manual verification
- Authorized lecturer action
- Mandatory reason/audit

The final attendance policy may use confidence levels for review.

---

## 21. Security Invariants

1. Expired token cannot grant attendance.
2. Wrong checkpoint token cannot grant attendance.
3. Student cannot receive duplicate checkpoint credit.
4. Unenrolled student cannot receive normal attendance.
5. Attendance correction cannot erase audit history.
6. Device reset cannot silently replace old registration.
7. Manual attendance must always be distinguishable from automated attendance.
8. Offline-created attendance must remain identifiable after sync.
