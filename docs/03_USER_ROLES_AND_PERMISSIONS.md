# Digital Student Attendance System
## User Roles and Permissions

**Version:** 1.0  
**Security model:** Role-Based Access Control (RBAC) with scoped permissions

---

## 1. Principles

1. Permissions are enforced server-side.
2. UI visibility is not a security control.
3. Users receive only the permissions required for their role.
4. Faculty/department roles must be scoped to assigned organizational units.
5. Sensitive actions require audit logging.
6. Some permissions may require explicit approval or elevated authorization.
7. Permissions must be configurable without changing source code.

---

## 2. Roles

### 2.1 Super Admin

**Scope:** Platform-wide

Typical permissions:

- Manage global system configuration
- Manage university-level administrators
- Manage security policies
- Manage role definitions
- View all audit logs
- Configure integration settings
- Manage system-wide backup/sync settings
- Access diagnostic tools
- Perform emergency recovery actions

Should not normally perform routine attendance editing.

---

### 2.2 University Admin

**Scope:** Entire university

Typical permissions:

- Manage faculties and departments
- Manage academic years and semesters
- Manage university policies
- Manage users
- Manage courses and rooms
- Configure attendance rules
- Configure threshold policies
- Approve exceptional attendance actions
- View university-wide reports
- Review suspicious activity
- Authorize device reset
- Manage imports
- Manage timetable data

---

### 2.3 Faculty Admin

**Scope:** Assigned faculty

Typical permissions:

- View/manage faculty departments
- Manage faculty course offerings
- Manage faculty lecturers
- Manage faculty students where authorized
- View faculty reports
- Review faculty attendance issues
- Import faculty-scoped data
- Approve scoped exceptions if granted

Cannot access unrelated faculties unless explicitly authorized.

---

### 2.4 Department Admin

**Scope:** Assigned department

Typical permissions:

- Manage department sections
- Manage course offerings
- Assign lecturers
- Manage schedules
- Review attendance
- View department reports
- Manage department enrollments
- Resolve department-level attendance issues
- Request/approve corrections where policy allows

---

### 2.5 Academic / Attendance Officer

**Scope:** Assigned university/faculty/department area

Typical permissions:

- Monitor attendance operations
- Review suspicious events
- Process attendance correction requests
- Perform authorized administrative corrections
- Manage attendance exceptions
- Review manual fallback records
- Generate reports
- Assist with student device reset
- Manage physical QR-card replacement
- Audit lecturer attendance activity

---

### 2.6 Lecturer

**Scope:** Assigned course offerings and class sessions

Permissions:

- View assigned classes
- View enrolled students for assigned classes
- Start authorized attendance session
- Open/close checkpoints
- Display QR/token
- Scan fallback physical cards
- View live/summary attendance for own class
- Record manual emergency attendance with reason
- Correct attendance within configured lecturer correction window
- Submit correction request outside normal window
- View own class attendance reports

Restrictions:

- Cannot create arbitrary attendance for unassigned courses.
- Cannot modify attendance without audit trail.
- Cannot access unrelated classes.
- Cannot bypass institutional policy without authorized exception.

---

### 2.7 Student

**Scope:** Own account and enrollments

Permissions:

- Authenticate
- Register approved primary device
- Submit attendance for enrolled classes
- View own attendance history
- View own checkpoint results
- View own percentage
- View own warnings
- Request device change
- View own correction outcomes
- Manage permitted profile settings

Restrictions:

- Cannot see other students' attendance.
- Cannot submit attendance for unregistered courses.
- Cannot create sessions.
- Cannot change attendance records.

---

### 2.8 Read-only Management / Auditor

**Scope:** Assigned organizational level

Permissions:

- View authorized reports
- View aggregate statistics
- View audit data where permitted
- View suspicious-event summaries
- Export read-only reports where permitted

Restrictions:

- Cannot change users
- Cannot change attendance
- Cannot change configuration
- Cannot start sessions

---

## 3. Permission Categories

Recommended permission naming:

```text
resource.action
```

Examples:

```text
students.read
students.create
students.update
students.import
lecturers.read
courses.manage
timetable.manage
attendance.session.start
attendance.checkpoint.open
attendance.submit
attendance.manual.create
attendance.correct
attendance.override
attendance.audit.read
devices.reset
reports.department.read
reports.university.read
settings.attendance.update
```

---

## 4. Scoped Authorization

Permissions may be restricted by:

- University
- Faculty
- Department
- Program
- Course offering
- Section
- Semester

Example:

A Faculty Admin with `attendance.audit.read` should only see attendance within the assigned faculty unless granted wider scope.

---

## 5. Sensitive Permissions

The following should be considered sensitive:

- Attendance override
- Device reset
- Bulk attendance modification
- Policy change
- Audit export
- User role change
- Exception session creation
- Import overwrite
- Data deletion/archive
- Integration configuration

Sensitive actions may require:

- Re-authentication
- Elevated role
- Reason
- Approval
- Additional audit event

---

## 6. Separation of Duties

Where practical:

- Lecturer records attendance.
- Attendance Officer reviews exceptions.
- University Admin controls policy.
- Auditor reviews without modifying.
- Super Admin controls platform security.

One person may hold multiple roles only where university policy permits.

---

## 7. Attendance Correction Rights

### Lecturer
- Default window: 24 hours
- Must provide reason
- Only own assigned class
- Every change audited

### Attendance Officer / Admin
- Can correct according to scope
- Must provide reason
- Original value retained
- High-risk changes may require approval

---

## 8. Device Reset Rights

Student device reset may be performed by authorized staff.

Required audit fields:

- Student
- Old device registration
- New device request
- Approving user
- Date/time
- Reason
- Verification method

Frequent resets should be flagged.

---

## 9. Physical QR Card Rights

Only authorized users may:

- Issue card identifier
- Revoke card
- Replace card
- Scan fallback attendance
- Review fallback usage

A student should not gain administrative card-management permissions.

---

## 10. Audit Expectations

Audit events should capture:

- Actor
- Role
- Action
- Target
- Old value
- New value
- Timestamp
- Reason
- Device/session context
- Scope
- Correlation/request ID where applicable
