# Digital Student Attendance System
## Scope and MVP Definition

**Version:** 1.0  
**Purpose:** Define what Version 1 must include, what it may include later, and what is explicitly out of scope.

---

## 1. MVP Objective

The Minimum Viable Product must prove that the university can conduct reliable, anti-cheating, three-checkpoint attendance for real classes over campus Wi-Fi/LAN without requiring external internet access.

The MVP is not intended to be a full university ERP.

---

## 2. MVP Target Environment

- One private university in Afghanistan
- 2,000–3,000 students at full rollout
- 200–300 lecturers at full rollout
- Pilot: 100–200 students, 3–5 lecturers
- Classes up to approximately 100 students
- Internet may be unreliable or unavailable
- Campus Wi-Fi/LAN is available
- Students primarily use smartphones
- Lecturers use Windows/Linux laptops and smartphones

---

## 3. Must-Have MVP Features

### Identity and Access
- User accounts
- Role-based permissions
- Student authentication
- Lecturer authentication
- Admin authentication
- Registered student device
- Device change/recovery workflow

### Academic Data
- University
- Faculties
- Departments
- Optional programs
- Academic years
- Semesters
- Courses
- Sections
- Course offerings
- Lecturer assignments
- Enrollments
- Rooms
- Timetables

### Attendance
- Scheduled attendance sessions
- Three checkpoints
- Dynamic QR/token
- Optional numeric fallback code
- Campus network validation
- Bluetooth proximity support
- Device validation
- Physical QR-card fallback
- Manual emergency attendance
- Attendance status calculation
- Late handling
- Excused/Leave handling
- Corrections
- Audit log

### Offline / Local Operation
- Campus LAN operation without internet
- Local server operation
- Mobile local storage where needed
- Queued synchronization
- Defined offline fallback for authorized lecturer device

### Reporting
- Student attendance
- Course attendance
- Section attendance
- Daily reports
- Low-attendance list
- Lecturer activity
- Checkpoint analysis
- Suspicious activity
- Manual/corrected attendance

### Administration
- Policy configuration
- Attendance threshold configuration
- Late threshold configuration
- Checkpoint duration configuration
- Token rotation configuration
- Correction-window configuration
- User and role management
- Excel/CSV import

### Languages
- Pashto
- Dari
- English
- RTL/LTR support

---

## 4. Should-Have Features for V1 if Time Permits

- Dashboard analytics
- In-app notifications
- Bulk administrative actions
- Advanced anomaly detection
- Admin approval workflow for sensitive corrections
- Device trust scoring
- Export to Excel/PDF/CSV
- Advanced attendance heatmaps
- More detailed audit review UI

---

## 5. Explicitly Out of Scope for MVP

The MVP will not implement:

- Financial management
- Examination management
- Payroll
- Full student information system
- Full LMS
- Gradebook
- Transcript generation
- Teacher evaluation
- Full university ERP
- Face recognition
- Selfie attendance
- Continuous GPS tracking
- Biometric attendance
- Public SaaS multi-tenancy
- Full WhatsApp/SMS integration
- Production integration with finance/exam systems

These may be considered later.

---

## 6. Future Integration Scope

The university already has finance and examination systems.

Future versions may integrate with them for:

- Student identity
- Enrollment status
- Course registrations
- Exam eligibility
- Attendance-based eligibility
- Shared academic identifiers

Integration must not be assumed before the external systems' API/data contracts are reviewed.

---

## 7. MVP Attendance Flow

1. Timetable defines scheduled class.
2. Lecturer opens assigned class.
3. System verifies lecturer authorization and allowed time.
4. Lecturer starts checkpoint.
5. Local server creates signed short-lived token.
6. QR/token rotates during the open window.
7. Student submits attendance using registered mobile app.
8. System verifies multiple signals:
   - enrollment
   - schedule
   - checkpoint
   - token validity
   - device registration
   - campus network
   - Bluetooth signal where available/required
9. Attendance event is recorded.
10. Lecturer closes or checkpoint auto-closes.
11. Process repeats for middle and end checkpoints.
12. System calculates final attendance according to policy.
13. Records are available for reports and audit.

---

## 8. MVP Physical Card Flow

For a student without a smartphone:

1. Student presents physical university card.
2. Lecturer/authorized staff scans the card.
3. System verifies card and enrollment.
4. Attendance is recorded with fallback flag.
5. Action is added to audit history.

A photograph of the card should not function as an unattended remote check-in.

---

## 9. MVP Offline Modes

### Supported
- Internet down, campus LAN/local server working
- Cloud unavailable
- Mobile app temporarily disconnected during a checkpoint, with controlled local queueing where safe

### Controlled Fallback
- Local campus server unavailable
- Lecturer device temporarily acts as authorized local session host

### Not Guaranteed in MVP
- Fully decentralized attendance among many student devices with no lecturer/local server authority
- Unlimited multi-day offline operation without synchronization

---

## 10. MVP Anti-Cheating Scope

MVP should prevent or detect:

- Static code sharing
- Screenshot-only QR sharing
- One device used for several accounts
- Frequent device changes
- Student not on campus network
- Attendance outside checkpoint window
- Attendance for non-enrolled course
- Attendance for wrong section
- Attendance outside scheduled class
- Duplicate submission
- Excessive manual attendance
- Suspicious lecturer corrections

MVP does not claim to make fraud impossible. It aims to make ordinary proxy attendance materially harder and auditable.

---

## 11. Pilot Scope

Pilot includes:

- One department
- 3–5 lecturers
- 100–200 students
- Several courses
- 2–4 weeks

Pilot should deliberately test:

- Internet outage
- Local network-only operation
- Bluetooth disabled
- QR screenshot sharing
- Wrong-device attempts
- Physical card fallback
- Lecturer correction
- Local-server interruption
- Sync recovery
- High-concurrency checkpoint

---

## 12. MVP Exit Criteria

Before university-wide rollout, the pilot must show:

- Stable local network performance
- Acceptable checkpoint completion time
- No major data-loss incidents
- Correct final attendance calculation
- Reliable audit trail
- Usable lecturer workflow
- Usable student workflow
- Successful recovery from internet outage
- Acceptable false-positive rate for anti-cheating rules
- Tested backup and restore
- Tested synchronization
- Resolved critical security findings
