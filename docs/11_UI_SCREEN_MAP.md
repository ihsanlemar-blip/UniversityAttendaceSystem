# Digital Student Attendance System
## UI Screen Map

**Version:** 1.0  
**Clients:** Responsive PWA + Flutter mobile app  
**Languages:** Pashto, Dari, English  
**Directions:** RTL + LTR

---

## 1. UX Principles

1. Attendance actions must be fast.
2. Students should need minimal typing during class.
3. Lecturer should reach today's class in very few taps/clicks.
4. Important states must be visually obvious.
5. Offline/local-server state must be clearly shown.
6. Manual/fallback attendance must be distinguishable.
7. RTL support is first-class, not an afterthought.
8. Error messages should explain what the user can do next.
9. Anti-cheating checks should not expose security implementation details.
10. Accessibility should be considered from the first release.

---

# PART A — Flutter Mobile App

## 2. Shared Mobile Screens

### M-001 Splash / Startup
- App initialization
- Local configuration
- Network/local-server discovery
- Session restoration

### M-002 Login
- Student number/username
- Password/PIN
- Language selection
- Local-server availability indicator

### M-003 Device Registration
- Explain device binding
- Generate/register device key
- Show approval state if required

### M-004 Device Replacement Request
- Lost phone / changed phone / reset
- Submit reason
- Show review status

### M-005 Notifications
- Attendance warning
- Correction
- Device status
- System notice

### M-006 Profile / Settings
- Language
- Security/session info
- Logout
- Device registration status

---

## 3. Student Mobile Screens

### S-001 Student Home

Shows:

- Today's classes
- Next class
- Current attendance opportunity
- Attendance warning summary
- Network state

### S-002 Today's Classes

Each card:

- Course
- Section
- Lecturer
- Time
- Room
- Attendance state

### S-003 Class Detail

Shows:

- Class information
- Checkpoint status
- Student's current checkpoint results
- Final attendance status when available

### S-004 Attendance Checkpoint

Core attendance screen.

Steps:

1. Detect active class/checkpoint.
2. Scan/read dynamic QR/token if required.
3. Verify registered device.
4. Verify campus network.
5. Obtain Bluetooth proximity proof.
6. Submit.
7. Show confirmed/pending/rejected receipt.

### S-005 Attendance Receipt

Shows:

- Course
- Checkpoint
- Server confirmation time
- Result
- Confirmation status
- Receipt identifier

### S-006 Attendance History

Filters:

- Semester
- Course
- Status

### S-007 Course Attendance Detail

Shows:

- Total sessions
- Present
- Late
- Absent
- Excused/Leave
- Percentage
- Three-checkpoint history
- Warnings

### S-008 Attendance Warning

Explains:

- Current percentage
- Minimum threshold
- Required future attendance if calculable

---

## 4. Lecturer Mobile Screens

### L-001 Lecturer Home

Shows:

- Today's assigned classes
- Next/current class
- Offline permit state
- Local server state

### L-002 Class Control

Actions:

- Start attendance session
- View enrolled count
- Open checkpoint
- View current attendance
- End session

### L-003 Checkpoint Control

Shows:

- Checkpoint type
- Countdown
- Current dynamic QR
- Optional short code
- Number received
- Number pending
- Close checkpoint

### L-004 Physical Card Scanner

- Scan student card
- Show student identity
- Verify enrollment
- Confirm fallback attendance

### L-005 Manual Attendance

- Search/select student
- Select status
- Mandatory reason
- Confirm action

### L-006 Live Attendance List

Shows:

- Student
- Submission status
- Confidence
- Fallback/manual indicator
- Risk indicator where permitted

### L-007 Class Attendance Summary

Shows:

- Checkpoint matrix
- Final statuses
- Missing students
- Manual/fallback count

### L-008 Correction Screen

- Select student
- Current record
- Requested change
- Reason
- Remaining correction window

### L-009 Offline Host Mode

Visible only if authorized.

Shows:

- Signed permit
- Class
- Validity window
- Pending offline events
- Sync state

---

# PART B — Responsive PWA / Web

## 5. Shared Web Screens

### W-001 Login
### W-002 Dashboard
### W-003 Notifications
### W-004 Profile / Language
### W-005 Access Denied
### W-006 System/Connection Status

---

## 6. University Administration

### A-001 University Dashboard

KPIs:

- Students
- Lecturers
- Classes today
- Attendance rate
- Low-attendance students
- Manual attendance count
- Sync status
- Risk flags

### A-002 Academic Structure

Manage:

- Faculties
- Departments
- Programs/other units
- Academic years
- Semesters

### A-003 Students

- List
- Search
- Detail
- Enrollment
- Device status
- Physical card
- Attendance summary

### A-004 Lecturers

- List
- Detail
- Assignments
- Current timetable
- Activity summary

### A-005 Courses

- Course catalog
- Course offerings
- Sections
- Assign lecturers
- Enrollment counts

### A-006 Timetable

Views:

- Day
- Week
- Lecturer
- Room
- Section

Actions:

- Create
- Edit
- Cancel
- Reschedule
- Substitute lecturer
- Merge sections where supported

### A-007 Attendance Monitor

Live/today view:

- Active sessions
- Open checkpoints
- Submission counts
- Failures
- Manual/fallback records
- Connectivity status

### A-008 Attendance Policy

Configure:

- Minimum attendance
- Late threshold
- Checkpoint timing
- Token rotation
- Correction window
- Presence requirements
- Final status mapping

### A-009 Corrections Queue

- Pending requests
- Before/after
- Reason
- Actor
- Approve/reject

### A-010 Device Requests

- Initial/replacement requests
- Device history
- Approve/reject/revoke

### A-011 Physical Card Management

- Issue
- Reissue
- Revoke
- Usage history

### A-012 Imports

- Upload Excel/CSV
- Map/validate columns if required
- Preview
- Error list
- Commit
- History

### A-013 Reports

Report catalog.

### A-014 Risk Review

- Suspicious student behavior
- Suspicious lecturer behavior
- Severity
- Evidence summary
- Review/resolution

### A-015 Audit Explorer

Search by:

- User
- Target
- Action
- Date
- Session

### A-016 System Health

- Local server
- Database
- Redis
- Worker
- Backup
- Cloud sync
- Disk
- Version

---

## 7. Faculty / Department Admin

Same components as University Admin but automatically scoped.

Important screens:

- Scoped dashboard
- Students
- Lecturers
- Courses
- Timetable
- Attendance
- Corrections
- Reports
- Risk flags

---

## 8. Lecturer Web/PWA

### LW-001 Today's Classes
### LW-002 Class Detail
### LW-003 Start Attendance
### LW-004 Display QR / Checkpoint
### LW-005 Live Attendance
### LW-006 Class Summary
### LW-007 Correction
### LW-008 Lecturer Reports

Web lecturer interface can operate attendance session controls.

Student high-confidence presence submission remains mobile-focused.

---

## 9. Student PWA

General self-service:

### SW-001 Student Dashboard
### SW-002 Attendance History
### SW-003 Course Attendance
### SW-004 Warnings
### SW-005 Notifications
### SW-006 Device Request Status

The PWA may not provide all high-confidence attendance submission functions.

---

## 10. Read-only Management / Auditor

### R-001 Executive Dashboard
### R-002 Attendance Trends
### R-003 Faculty Comparison
### R-004 Low Attendance
### R-005 Lecturer Activity
### R-006 Audit Review
### R-007 Risk Summary

No modification controls.

---

## 11. Navigation Model

### Mobile Student

```text
Home
├── Today's Classes
├── Attendance
├── History
├── Notifications
└── Profile
```

### Mobile Lecturer

```text
Home
├── Today's Classes
│   └── Class Control
│       ├── Checkpoint
│       ├── Card Scan
│       ├── Manual
│       └── Summary
├── Notifications
└── Profile
```

### Web Admin

```text
Dashboard
Academic
├── Structure
├── Students
├── Lecturers
├── Courses
└── Timetable
Attendance
├── Monitor
├── Corrections
├── Policies
├── Devices
├── Physical Cards
└── Risks
Reports
Imports
Audit
System
```

---

## 12. Critical UI States

Every attendance-related screen must account for:

- Local server online
- Local server unavailable
- Internet unavailable
- Bluetooth disabled
- Device not registered
- Token expired
- Wrong class
- Checkpoint closed
- Submission duplicate
- Submission pending sync
- Submission under review
- Manual fallback required

---

## 13. RTL Requirements

- Use CSS logical properties.
- Avoid hard-coded left/right layout assumptions.
- Icons with directional meaning must mirror where appropriate.
- Tables must remain usable in RTL.
- Pashto/Dari typography must be tested with realistic data.
- Mixed Latin course codes must remain readable.

---

## 14. Accessibility

Minimum goals:

- Keyboard-accessible PWA
- Proper labels
- Reasonable contrast
- Text scaling
- Screen-reader-friendly forms
- No attendance-critical action relying on color alone
