# Digital Student Attendance System
## Product Requirements Document (PRD)

**Version:** 1.0  
**Status:** Foundation requirements  
**Primary market:** Private university in Afghanistan  
**Initial capacity:** 2,000–3,000 students, 200–300 lecturers

---

## 1. Product Summary

The Digital Student Attendance System is an offline-capable university attendance platform designed to verify physical class presence through a combination of schedule validation, dynamic QR/token checks, campus network presence, registered-device checks, Bluetooth proximity, and three attendance checkpoints.

The system must continue functioning on the university's local network even when internet access is unavailable.

---

## 2. Primary Functional Areas

Version 1 includes:

1. Identity and authentication
2. Role-based access control
3. Academic structure
4. Student management
5. Lecturer management
6. Course and section management
7. Enrollment
8. Timetable management
9. Attendance session management
10. Three-checkpoint attendance
11. Dynamic QR/token generation and validation
12. Device registration
13. Campus-network validation
14. Bluetooth proximity verification
15. Physical QR-card fallback
16. Manual attendance fallback
17. Attendance correction workflow
18. Audit logging
19. Reporting and analytics
20. In-app notifications
21. Excel/CSV import
22. Offline/local-network operation
23. Synchronization with cloud/remote services
24. Multilingual interface
25. PWA/web administration
26. Mobile attendance application

---

## 3. User Roles

### 3.1 Super Admin
Responsible for platform-level configuration and the highest level of administration.

### 3.2 University Admin
Manages university-wide settings, academic structures, policies, users, and reports.

### 3.3 Faculty Admin
Manages data and operations within assigned faculty scope.

### 3.4 Department Admin
Manages assigned department records, schedules, sections, and attendance oversight.

### 3.5 Academic / Attendance Officer
Handles operational attendance monitoring, corrections, exceptions, imports, and reports.

### 3.6 Lecturer
Views assigned classes, starts attendance sessions, manages checkpoints, scans fallback cards, requests/carries out allowed corrections, and reviews class attendance.

### 3.7 Student
Views assigned classes and attendance records, completes attendance checkpoints, sees warnings, and manages permitted device-registration actions.

### 3.8 Read-only Management / Auditor
Views authorized reports and audit information without changing operational records.

---

## 4. Academic Structure Requirements

The system must support flexible academic structures.

Possible hierarchy:

University  
→ Faculty  
→ Department (optional where not used)  
→ Program (optional where not used)  
→ Academic Year  
→ Semester  
→ Section (optional where not used)  
→ Course  
→ Course Offering  
→ Lecturer Assignment  
→ Scheduled Class  
→ Attendance Session

The software must not require every level to be populated when the institution does not use it.

---

## 5. Student Requirements

The system must support:

- Permanent unique student ID
- Student number / username
- Name
- Academic assignment
- Enrollment status
- Course enrollment
- Registered primary device
- Physical QR-card identifier
- Attendance history
- Attendance percentage
- Notifications
- Device-change workflow

Students must only see their own attendance and permitted academic information.

---

## 6. Lecturer Requirements

Lecturers must be able to:

- Log in through mobile or web.
- View today's scheduled classes.
- View assigned courses and sections.
- Start attendance only within allowed scheduling rules.
- Open checkpoint 1, 2, and 3.
- Display dynamic QR/token.
- View live attendance submissions where permitted.
- Scan physical student QR cards as fallback.
- Manually mark attendance in emergency cases with mandatory reason.
- Review class attendance.
- Correct attendance within the configured correction window.
- See suspicious attendance flags relevant to their class.

A lecturer may teach multiple sections. Any institutional limit must be configurable and not hard-coded.

---

## 7. Timetable Requirements

Each scheduled class should support:

- Course
- Course offering
- Lecturer
- Section
- Classroom
- Day/date
- Start time
- End time
- Semester
- Recurrence
- Cancellation state
- Rescheduling
- Substitute lecturer
- Room change
- Make-up class
- Merged section handling

Attendance sessions should normally be generated from or linked to the timetable.

---

## 8. Three-Checkpoint Attendance Requirements

Each class may contain:

### Checkpoint 1
Beginning of class

### Checkpoint 2
Middle of class

### Checkpoint 3
End of class

Each checkpoint must have:

- Open time
- Close time
- Configurable duration
- Dynamic token/QR
- Validation rules
- Attendance event records
- Audit evidence

Default checkpoint duration: **3–5 minutes**, configurable.

The system must not hard-code final attendance status from checkpoint combinations. University policy must define the mapping.

---

## 9. Attendance Statuses

Minimum supported statuses:

- Present
- Late
- Absent
- Excused
- Leave
- Pending / Unverified

Additional internal flags may include:

- Manual
- Fallback-card
- Suspicious
- Offline-created
- Corrected
- Synced
- Conflict-review

---

## 10. Late Attendance

Recommended default:

- First checkpoint attendance within the first 10 minutes may be considered normal.
- Attendance after the configured threshold may be marked Late.

The exact late threshold must be configurable.

---

## 11. Minimum Attendance Requirement

Default recommendation: **75%**

The threshold must be configurable at appropriate scopes, such as:

- University
- Faculty
- Program
- Course

The system should use a clear precedence rule when multiple policies exist.

---

## 12. Dynamic QR / Token Requirements

Each checkpoint should generate a short-lived signed token.

Requirements:

- Token rotates approximately every 20–30 seconds by default.
- Rotation interval is configurable.
- Token must be cryptographically verifiable.
- Expired tokens are invalid.
- Token must be bound to the specific session/checkpoint.
- Tokens must not contain sensitive student data.
- Optional numeric fallback code may exist.
- Numeric fallback must have equivalent expiry and session binding.

Sharing a screenshot or copied token must not be sufficient to establish attendance.

---

## 13. Device Registration Requirements

Each student account should normally be associated with one primary mobile device.

Requirements:

- Initial device registration
- Cryptographic device identity/registration
- Device-change request
- Lost-device workflow
- Admin approval where required
- Device history
- Suspicious device-switch detection

Do not rely solely on a raw hardware identifier.

---

## 14. Campus Network Requirements

Attendance should work on campus Wi-Fi/LAN without internet.

The system should verify campus network presence using one or more trusted network-level mechanisms.

The architecture must explicitly distinguish:

> **Campus network connectivity != Internet connectivity**

External internet must not be required for normal on-campus attendance.

---

## 15. Bluetooth Proximity Requirements

Bluetooth will be used as a supporting proximity signal.

Requirements:

- Bluetooth must not be the only proof of presence.
- Proximity checks should be time-bound to the current checkpoint.
- Bluetooth failures must not automatically cause permanent absence without fallback.
- Platform limitations must be considered.
- Sensitive raw Bluetooth identifiers should not be exposed unnecessarily.
- A native mobile implementation may be used where browser support is insufficient.

---

## 16. Physical QR-Card Fallback

For students without smartphones:

- University may issue physical ID card with unique signed QR.
- Lecturer or authorized staff scans the card.
- Student should not self-submit a photographed card remotely.
- Fallback attendance is flagged.
- Repeated fallback can be reviewed.
- Card revocation/reissue must be supported.

---

## 17. Offline Requirements

The system must support:

### Mode A: Internet unavailable, local campus server available
Normal attendance continues over LAN/Wi-Fi.

### Mode B: Local campus server temporarily unavailable
Authorized lecturer device may temporarily manage the session if offline fallback is enabled.

Offline-created events must:

- Be cryptographically tied to the authorized session/device.
- Use trusted local timing controls where possible.
- Be queued for later synchronization.
- Be marked as offline-originated.
- Be auditable.
- Be conflict-checked on sync.

---

## 18. Attendance Corrections

### Lecturer
Default allowed correction window: 24 hours.

Correction must:

- Require reason
- Preserve original value
- Record actor
- Record time
- Record old and new values
- Be auditable

### Administrator
Authorized admins may override records.

Sensitive corrections may optionally require higher-level approval.

---

## 19. Manual Emergency Attendance

When technology fails, lecturer may manually mark attendance.

Manual attendance must:

- Require reason
- Be flagged
- Record actor/time/device
- Appear in audit log
- Be available for review
- Be reportable separately

---

## 20. Cancellation and Exceptions

System must support:

- Cancelled classes
- Make-up classes
- Rescheduled classes
- Substitute lecturers
- Merged sections
- Holidays
- Room changes
- Exceptional attendance sessions with admin authorization

---

## 21. Reporting Requirements

Version 1 reports should include:

- Individual student attendance
- Course attendance
- Section attendance
- Daily attendance
- Lecturer activity
- Absent students
- Late students
- Students below threshold
- Department statistics
- Faculty statistics
- Semester reports
- Checkpoint analysis
- Suspicious attendance events
- Manual attendance corrections
- Device change history
- Attendance correction history

Reports should support filtering and export where appropriate.

---

## 22. Student Visibility

Students should see:

- Attendance history
- Present/Absent/Late/Excused/Leave status
- Checkpoint results
- Course percentage
- Corrections
- Warnings
- Relevant device-registration status

Students must not see other students' attendance.

---

## 23. Notifications

Version 1:

- In-app notifications

Examples:

- Attendance below warning threshold
- Missed class
- Attendance correction
- Risk of becoming ineligible
- Device change approval/rejection

Future:

- SMS
- Email
- WhatsApp, subject to policy and integration feasibility

---

## 24. Import Requirements

Excel/CSV import must support:

- Students
- Lecturers
- Faculties
- Departments
- Programs
- Courses
- Sections
- Enrollments
- Timetables

Imports must support:

- Validation
- Preview
- Error reporting
- Duplicate detection
- Rejection of invalid rows
- Import audit history

---

## 25. Language Requirements

Version 1:

- Pashto
- Dari
- English

Requirements:

- RTL for Pashto/Dari
- LTR for English
- Translatable UI strings
- Locale-aware dates/numbers where appropriate
- No hard-coded interface text

---

## 26. Client Applications

### PWA / Responsive Web
For:

- Admin
- Faculty/department administration
- Lecturer access
- Reports
- Timetable
- Imports
- Configuration
- General student access

### Flutter Mobile App
For:

- Student attendance
- Lecturer attendance
- QR scanning
- Device registration
- Bluetooth proximity
- Offline storage
- Android and iOS-capable architecture

---

## 27. Technology Direction

Current preferred stack:

- Flutter: mobile
- Next.js / React: responsive PWA/web
- FastAPI: backend
- PostgreSQL: primary database
- SQLite: mobile/offline local storage where appropriate
- Docker: infrastructure

This stack may change only through an explicit architecture decision record.

---

## 28. Security Requirements Summary

The system must:

- Enforce authorization server-side.
- Use strong password hashing.
- Use secure sessions/tokens.
- Protect sensitive data in transit.
- Avoid sensitive information in QR payloads.
- Log important security events.
- Detect suspicious device/account use.
- Rate-limit abuse-prone endpoints.
- Prevent cross-role data exposure.
- Provide tamper-evident audit history where practical.

---

## 29. Privacy Requirements Summary

Avoid unnecessary collection of:

- Continuous GPS
- Biometrics
- Excessive device fingerprinting
- Sensitive unrelated personal information

Store only data necessary for attendance, security, operations, and audit.

---

## 30. Integration Requirements

The university already has financial and examination systems.

Version 1 will not replace them.

Future integration should support:

- APIs where available
- Controlled database integration only where safe and approved
- Secure import/export
- Student/course identity mapping
- Event-based synchronization if later needed

A separate integration specification should be created before integration development.

---

## 31. Pilot Requirements

Initial pilot:

- One department
- 3–5 lecturers
- 100–200 students
- Several courses
- 2–4 weeks

Pilot must test technical reliability, user experience, anti-cheating behavior, offline operation, sync, and reporting.

---

## 32. Definition of Product Success

The product succeeds when it can provide trustworthy attendance evidence in the university's real operating environment without depending on constant internet connectivity and without creating excessive friction for lecturers or students.
