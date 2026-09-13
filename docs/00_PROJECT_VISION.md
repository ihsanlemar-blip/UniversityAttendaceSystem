# Digital Student Attendance System
## Project Vision

**Document status:** Foundation / Version 1.0  
**Target context:** Private university in Afghanistan  
**Initial scale:** 2,000–3,000 students, 200–300 lecturers  
**Primary deployment model:** Campus-local, offline-capable, hybrid local/cloud architecture

---

## 1. Vision

The Digital Student Attendance System will provide a reliable, fast, auditable, and anti-cheating attendance platform for university classes in environments where internet access may be unreliable or unavailable.

The system will use a **three-checkpoint attendance model**—beginning, middle, and end of class—to verify not only that a student entered the classroom, but also that the student remained present for a meaningful portion of the session.

The system must work over the university's local Wi-Fi/LAN even when that network has no external internet access.

The core principle is:

> **Schedule + Dynamic QR/Token + Registered Device + University Local Wi-Fi/LAN + Bluetooth Proximity + Three Checkpoints + Audit Logs + Offline Operation**

No single signal is treated as sufficient proof of attendance.

---

## 2. Problem Statement

Traditional paper attendance and simple QR/code-based attendance systems have several weaknesses:

- Students can sign for one another.
- Static QR codes or numeric codes can be shared through messaging apps.
- Attendance may be recorded only once at the beginning of class.
- Students can check in and leave early.
- Internet-dependent systems fail when connectivity is poor.
- Manual attendance records are difficult to audit.
- Attendance corrections may be changed without a transparent history.
- University management lacks timely attendance analytics.
- Existing attendance solutions often do not fit the infrastructure conditions of Afghan universities.

The proposed system will address these weaknesses through layered physical-presence checks, offline operation, configurable rules, strong auditability, and a simple user experience.

---

## 3. Target Users

The system is initially designed for one private university with:

- **2,000–3,000 students**
- **200–300 lecturers**
- Multiple faculties
- Multiple departments
- Multiple programs and sections
- Multiple simultaneous classes

The architecture must not impose a hard technical limit at 3,000 students and should support future expansion.

---

## 4. User Roles

The initial role model will include:

- Super Admin
- University Admin
- Faculty Admin
- Department Admin
- Academic / Attendance Officer
- Lecturer
- Student
- Read-only Management / Auditor

Permissions must be configurable and enforced server-side.

---

## 5. Core Product Goals

### 5.1 Reliable Physical Presence
Attendance should be accepted only when multiple independent indicators support that the student is physically present.

### 5.2 Three-Checkpoint Verification
Each scheduled class may contain three attendance checkpoints:

1. Start of class
2. Middle of class
3. End of class

The final attendance outcome is calculated from these checkpoints according to configurable university policy.

### 5.3 No Internet Dependency
The system must work on the university's local Wi-Fi/LAN without external internet access.

### 5.4 Fast Operation
A class of approximately 100 students should be able to complete each attendance checkpoint within a short configurable window, normally 3–5 minutes.

### 5.5 Strong Anti-Cheating
The system should significantly reduce proxy attendance, code sharing, device sharing, and fraudulent attendance manipulation.

### 5.6 Auditability
Important actions and changes must leave a permanent audit trail.

### 5.7 Configurability
Rules such as late thresholds, attendance percentages, checkpoint duration, and correction windows must be configurable without code changes.

### 5.8 Future Integration
The university already has systems for financial and examination functions. The attendance system should be designed so future versions can integrate with them rather than duplicating those systems.

---

## 6. Product Principles

1. **Offline-first for campus attendance**
2. **Local network is not the same as internet**
3. **Security through multiple signals, not one mechanism**
4. **Configurable policies instead of hard-coded rules**
5. **Audit every sensitive change**
6. **Minimize personal and biometric data collection**
7. **Keep Version 1 focused on attendance**
8. **Design for future integrations**
9. **Support Pashto, Dari, and English**
10. **Support RTL for Pashto and Dari**
11. **Use open, maintainable interfaces and standards**
12. **Keep AI-generated code governed by written architecture and acceptance criteria**

---

## 7. Platform Vision

### Responsive Web / PWA
Used for:

- Administration
- Faculty and department management
- Lecturer dashboards
- Timetables
- Reports
- Data imports
- Configuration
- General student access
- Windows/Linux laptop access

### Mobile Application
A Flutter-based mobile application is recommended for security-sensitive attendance functions requiring:

- Device registration
- QR scanning
- Bluetooth proximity
- Reliable local storage
- Stronger offline behavior
- Android support
- iOS-capable architecture

The PWA should not be the sole mechanism for Bluetooth-based presence validation.

---

## 8. Deployment Vision

The system will use a hybrid model:

### University Local Infrastructure
- Local application/API service
- PostgreSQL database or controlled local database service
- Campus Wi-Fi/LAN
- Works without internet
- Local attendance processing

### Cloud / Remote Infrastructure
- Backup
- Synchronization
- Disaster recovery
- Optional remote administration
- Future multi-university services

Internet outages must not stop normal on-campus attendance.

---

## 9. Attendance Proof Model

A valid attendance event may consider:

- Scheduled class
- Correct checkpoint window
- Registered user
- Registered device
- Campus network presence
- Dynamic signed QR/token
- Bluetooth proximity
- Submission timing
- Duplicate/device-abuse checks
- Lecturer session authorization
- Audit evidence

No single factor should be considered definitive proof on its own.

---

## 10. Physical Student Card Fallback

Students without a smartphone may use a university-issued physical card with a unique signed QR identifier.

The physical QR card is a **fallback credential**, not a remote self-check-in mechanism.

Normally:

- Lecturer or authorized attendance staff scans the card.
- The attendance record is marked as fallback/manual-verification.
- Frequent fallback use can be flagged for review.
- Sensitive personal information must not be encoded directly in the QR.

---

## 11. Non-Goals for Version 1

Version 1 will not attempt to replace:

- Financial management systems
- Examination management systems
- Full student information systems
- LMS platforms
- Payroll
- Full ERP functions
- Face recognition attendance
- Continuous GPS tracking

These may be integrated or extended in future versions.

---

## 12. Success Criteria

Version 1 will be considered successful when it can:

- Run attendance over campus Wi-Fi without internet.
- Support three attendance checkpoints.
- Handle classes of approximately 100 students efficiently.
- Prevent simple QR/code sharing from being sufficient for attendance.
- Detect common device/account abuse.
- Produce accurate reports.
- Keep a permanent audit history.
- Support student, lecturer, and administrator workflows.
- Operate in Pashto, Dari, and English.
- Complete a 2–4 week pilot with 100–200 students and 3–5 lecturers.
- Demonstrate stable offline/local-network operation.

---

## 13. Pilot Goal

The first pilot should include:

- One department
- 3–5 lecturers
- 100–200 students
- Several courses
- 2–4 weeks

The pilot should test:

- Usability
- Performance
- Connectivity
- Bluetooth reliability
- QR/token rotation
- Device registration
- Manual fallback
- Sync behavior
- Cheating attempts
- Reporting accuracy
- Lecturer and student feedback

After pilot evaluation, the system can be expanded university-wide.
