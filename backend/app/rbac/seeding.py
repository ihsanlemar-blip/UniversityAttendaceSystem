"""Idempotent seeding service for system roles and base permissions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import SystemRole
from backend.app.models.permission import Permission
from backend.app.models.role import Role
from backend.app.models.role_permission import RolePermission

# Standard system permissions for core platform and identity domains
SYSTEM_PERMISSIONS = [
    ("users.read", "View user accounts and profiles"),
    ("users.create", "Create new user accounts"),
    ("users.update", "Update user account information"),
    ("users.disable", "Disable user accounts"),
    ("users.enable", "Re-enable disabled user accounts"),
    ("users.reset_password", "Administratively reset user credentials"),
    ("roles.read", "View authorization role definitions"),
    ("roles.create", "Create custom university roles"),
    ("roles.update", "Update role descriptions and permissions"),
    ("permissions.read", "View available system permissions"),
    ("role_assignments.read", "View user role assignments"),
    ("role_assignments.manage", "Assign and revoke user roles"),
    ("sessions.read", "View active authentication sessions"),
    ("sessions.revoke", "Revoke user authentication sessions"),
    ("audit.read", "View immutable audit logs"),
    ("academic_units.read", "View academic hierarchy units and organizational trees"),
    ("academic_units.manage", "Create, update, reparent, and deactivate academic units"),
    ("academic_years.read", "View institutional academic years"),
    ("academic_years.manage", "Create, update, and activate academic years"),
    ("semesters.read", "View semester calendar sessions"),
    ("semesters.manage", "Create, update, and activate semester calendar sessions"),
    ("courses.read", "View master course catalog definitions"),
    ("courses.manage", "Create, update, and manage course catalog"),
    ("sections.read", "View student sections and cohorts"),
    ("sections.manage", "Create, update, and manage student sections"),
    ("students.read", "View student academic profiles and rosters"),
    ("students.manage", "Create, update, and manage student profiles"),
    ("lecturers.read", "View lecturer profiles and teaching assignments"),
    ("lecturers.manage", "Create, update, and manage lecturer profiles"),
    ("course_offerings.read", "View course offerings and instructor assignments"),
    (
        "course_offerings.manage",
        "Create, schedule, and manage course offerings and instructor assignments",
    ),
    ("enrollments.read", "View course offering enrollments and student class rosters"),
    ("enrollments.manage", "Enroll students, drop, and manage course offering rosters"),
    ("buildings.read", "View campus buildings and facility containers"),
    ("buildings.create", "Create new campus buildings"),
    ("buildings.update", "Update campus building details"),
    ("buildings.deactivate", "Deactivate campus buildings"),
    ("rooms.read", "View rooms, classrooms, and lecture hall facilities"),
    ("rooms.create", "Create new room and facility spaces"),
    ("rooms.update", "Update room and facility details"),
    ("rooms.deactivate", "Deactivate rooms and facility spaces"),
    ("timetables.read", "View recurring timetable schedule rules"),
    ("timetables.create", "Create recurring timetable schedule rules"),
    ("timetables.update", "Update recurring timetable schedule rules"),
    ("timetables.deactivate", "Deactivate recurring timetable schedule rules"),
    (
        "timetables.generate_occurrences",
        "Generate concrete class occurrences from timetable rules",
    ),
    ("class_occurrences.read", "View concrete scheduled class occurrences"),
    ("class_occurrences.cancel", "Cancel concrete scheduled class occurrences"),
    ("class_occurrences.reschedule", "Reschedule concrete scheduled class occurrences"),
    ("attendance_policies.read", "View attendance policies and hierarchy rules"),
    ("attendance_policies.manage", "Create, update, and manage attendance policies"),
    ("attendance_sessions.read", "View attendance sessions and real-time status"),
    (
        "attendance_sessions.manage",
        "Initialize, open, pause, resume, and close attendance sessions",
    ),
    ("attendance_checkpoints.manage", "Open and close attendance checkpoints"),
    ("attendance_records.read", "View attendance records and class rosters"),
    (
        "attendance_records.override",
        "Manually override attendance records, excuse, and grant leave",
    ),
    ("attendance_audit.read", "View immutable attendance audit revision history"),
    ("attendance.self_read", "View personal attendance history and verification status"),
    ("devices.self_read", "View personal registered device status and history"),
    ("devices.self_register", "Perform initial self-registration of primary device"),
    ("devices.replacement_request", "Submit replacement or lost report for personal device"),
    ("devices.read", "View registered student devices and replacement requests"),
    ("devices.replacement_review", "Approve or reject student device replacement requests"),
    ("devices.suspend", "Suspend registered student devices"),
    ("devices.revoke", "Revoke or mark compromised student devices"),
]

# Base role definitions
SYSTEM_ROLES = [
    (
        SystemRole.SUPER_ADMIN.value,
        "Super Administrator",
        "Platform-level super user with complete administrative authority",
        True,
    ),
    (
        SystemRole.UNIVERSITY_ADMIN.value,
        "University Administrator",
        "Institutional administrator managing university structure, users, and policy",
        True,
    ),
    (
        SystemRole.FACULTY_ADMIN.value,
        "Faculty Administrator",
        "Faculty-scoped administrator managing departments and lecturers",
        True,
    ),
    (
        SystemRole.DEPARTMENT_ADMIN.value,
        "Department Administrator",
        "Department-scoped administrator managing courses and schedules",
        True,
    ),
    (
        SystemRole.ATTENDANCE_OFFICER.value,
        "Attendance Officer",
        "Academic operations officer monitoring and correcting attendance",
        True,
    ),
    (
        SystemRole.LECTURER.value,
        "Lecturer",
        "Academic instructor conducting classes and taking attendance",
        True,
    ),
    (
        SystemRole.STUDENT.value,
        "Student",
        "Enrolled student attending classes and verifying presence",
        True,
    ),
    (
        SystemRole.AUDITOR.value,
        "Auditor",
        "Read-only oversight role with reporting and audit access",
        True,
    ),
]


async def seed_system_rbac(db: AsyncSession) -> None:
    """Idempotently seed system permissions, roles, and standard mappings."""
    # 1. Seed Permissions
    existing_perms_stmt = select(Permission)
    perms_res = await db.execute(existing_perms_stmt)
    perm_map: dict[str, Permission] = {p.code: p for p in perms_res.scalars().all()}

    for p_tuple in SYSTEM_PERMISSIONS:
        p_code, p_desc = p_tuple
        if p_code not in perm_map:
            new_perm = Permission(code=p_code, description=p_desc)
            db.add(new_perm)
            await db.flush()
            perm_map[p_code] = new_perm

    # 2. Seed Roles
    existing_roles_stmt = select(Role)
    roles_res = await db.execute(existing_roles_stmt)
    role_map: dict[str, Role] = {r.code: r for r in roles_res.scalars().all()}

    for r_code, r_name, r_desc, is_sys in SYSTEM_ROLES:
        if r_code not in role_map:
            new_role = Role(code=r_code, name=r_name, description=r_desc, is_system=is_sys)
            db.add(new_role)
            await db.flush()
            role_map[r_code] = new_role

    # 3. Seed Role-Permission Associations
    existing_rp_stmt = select(RolePermission)
    rp_res = await db.execute(existing_rp_stmt)
    existing_rps = list(rp_res.scalars().all())
    existing_rp_pairs = {(rp.role_id, rp.permission_id) for rp in existing_rps}

    # Mapping logic:
    # Super Admin gets all permissions
    super_admin_role = role_map.get(SystemRole.SUPER_ADMIN.value)
    if super_admin_role:
        for perm in perm_map.values():
            pair = (super_admin_role.id, perm.id)
            if pair not in existing_rp_pairs:
                db.add(RolePermission(role_id=super_admin_role.id, permission_id=perm.id))
                existing_rp_pairs.add(pair)

    # University Admin gets user, role assignment, session, and academic structure permissions
    uni_admin_role = role_map.get(SystemRole.UNIVERSITY_ADMIN.value)
    if uni_admin_role:
        uni_admin_perms = [
            "users.read",
            "users.create",
            "users.update",
            "users.disable",
            "users.enable",
            "users.reset_password",
            "roles.read",
            "permissions.read",
            "role_assignments.read",
            "role_assignments.manage",
            "sessions.read",
            "sessions.revoke",
            "academic_units.read",
            "academic_units.manage",
            "academic_years.read",
            "academic_years.manage",
            "semesters.read",
            "semesters.manage",
            "courses.read",
            "courses.manage",
            "sections.read",
            "sections.manage",
            "students.read",
            "students.manage",
            "lecturers.read",
            "lecturers.manage",
            "course_offerings.read",
            "course_offerings.manage",
            "enrollments.read",
            "enrollments.manage",
            "buildings.read",
            "buildings.create",
            "buildings.update",
            "buildings.deactivate",
            "rooms.read",
            "rooms.create",
            "rooms.update",
            "rooms.deactivate",
            "timetables.read",
            "timetables.create",
            "timetables.update",
            "timetables.deactivate",
            "timetables.generate_occurrences",
            "class_occurrences.read",
            "class_occurrences.cancel",
            "class_occurrences.reschedule",
            "attendance_policies.read",
            "attendance_policies.manage",
            "attendance_sessions.read",
            "attendance_sessions.manage",
            "attendance_checkpoints.manage",
            "attendance_records.read",
            "attendance_records.override",
            "attendance_audit.read",
        ]
        for admin_p_code in uni_admin_perms:
            target_perm = perm_map.get(admin_p_code)
            if target_perm:
                pair = (uni_admin_role.id, target_perm.id)
                if pair not in existing_rp_pairs:
                    db.add(RolePermission(role_id=uni_admin_role.id, permission_id=target_perm.id))
                    existing_rp_pairs.add(pair)

    # Faculty Admin gets academic structure, curriculum, people, offerings, and enrollments
    faculty_admin_role = role_map.get(SystemRole.FACULTY_ADMIN.value)
    if faculty_admin_role:
        fac_perms = [
            "users.read",
            "academic_units.read",
            "academic_years.read",
            "semesters.read",
            "courses.read",
            "courses.manage",
            "sections.read",
            "sections.manage",
            "students.read",
            "students.manage",
            "lecturers.read",
            "lecturers.manage",
            "course_offerings.read",
            "course_offerings.manage",
            "enrollments.read",
            "enrollments.manage",
            "buildings.read",
            "rooms.read",
            "timetables.read",
            "timetables.create",
            "timetables.update",
            "timetables.deactivate",
            "timetables.generate_occurrences",
            "class_occurrences.read",
            "class_occurrences.cancel",
            "class_occurrences.reschedule",
            "attendance_policies.read",
            "attendance_policies.manage",
            "attendance_sessions.read",
            "attendance_sessions.manage",
            "attendance_checkpoints.manage",
            "attendance_records.read",
            "attendance_records.override",
            "attendance_audit.read",
            "devices.read",
            "devices.replacement_review",
            "devices.suspend",
            "devices.revoke",
        ]
        for p_code in fac_perms:
            target_perm = perm_map.get(p_code)
            if target_perm:
                pair = (faculty_admin_role.id, target_perm.id)
                if pair not in existing_rp_pairs:
                    db.add(
                        RolePermission(role_id=faculty_admin_role.id, permission_id=target_perm.id)
                    )
                    existing_rp_pairs.add(pair)

    # Department Admin gets academic structure, curriculum, people, offerings, and enrollments
    dept_admin_role = role_map.get(SystemRole.DEPARTMENT_ADMIN.value)
    if dept_admin_role:
        dept_perms = [
            "users.read",
            "academic_units.read",
            "academic_years.read",
            "semesters.read",
            "courses.read",
            "courses.manage",
            "sections.read",
            "sections.manage",
            "students.read",
            "students.manage",
            "lecturers.read",
            "lecturers.manage",
            "course_offerings.read",
            "course_offerings.manage",
            "enrollments.read",
            "enrollments.manage",
            "buildings.read",
            "rooms.read",
            "timetables.read",
            "timetables.create",
            "timetables.update",
            "timetables.deactivate",
            "timetables.generate_occurrences",
            "class_occurrences.read",
            "class_occurrences.cancel",
            "class_occurrences.reschedule",
            "attendance_policies.read",
            "attendance_policies.manage",
            "attendance_sessions.read",
            "attendance_sessions.manage",
            "attendance_checkpoints.manage",
            "attendance_records.read",
            "attendance_records.override",
            "attendance_audit.read",
            "devices.read",
            "devices.replacement_review",
            "devices.suspend",
            "devices.revoke",
        ]
        for p_code in dept_perms:
            target_perm = perm_map.get(p_code)
            if target_perm:
                pair = (dept_admin_role.id, target_perm.id)
                if pair not in existing_rp_pairs:
                    db.add(RolePermission(role_id=dept_admin_role.id, permission_id=target_perm.id))
                    existing_rp_pairs.add(pair)

    # Attendance Officer gets operational identity and session monitoring permissions
    attendance_officer_role = role_map.get(SystemRole.ATTENDANCE_OFFICER.value)
    if attendance_officer_role:
        officer_perms = [
            "users.read",
            "sessions.read",
            "audit.read",
            "academic_units.read",
            "academic_years.read",
            "semesters.read",
            "courses.read",
            "sections.read",
            "students.read",
            "lecturers.read",
            "course_offerings.read",
            "enrollments.read",
            "buildings.read",
            "rooms.read",
            "timetables.read",
            "class_occurrences.read",
            "attendance_policies.read",
            "attendance_sessions.read",
            "attendance_records.read",
            "attendance_records.override",
            "attendance_audit.read",
            "devices.read",
            "devices.replacement_review",
            "devices.suspend",
            "devices.revoke",
        ]
        for off_p_code in officer_perms:
            target_perm = perm_map.get(off_p_code)
            if target_perm:
                pair = (attendance_officer_role.id, target_perm.id)
                if pair not in existing_rp_pairs:
                    db.add(
                        RolePermission(
                            role_id=attendance_officer_role.id,
                            permission_id=target_perm.id,
                        )
                    )
                    existing_rp_pairs.add(pair)

    # Lecturer gets academic catalog, sections, roster and offering read permissions
    lecturer_role = role_map.get(SystemRole.LECTURER.value)
    if lecturer_role:
        lecturer_perms = [
            "academic_units.read",
            "academic_years.read",
            "semesters.read",
            "courses.read",
            "sections.read",
            "students.read",
            "lecturers.read",
            "course_offerings.read",
            "enrollments.read",
            "buildings.read",
            "rooms.read",
            "timetables.read",
            "class_occurrences.read",
            "attendance_policies.read",
            "attendance_sessions.read",
            "attendance_sessions.manage",
            "attendance_checkpoints.manage",
            "attendance_records.read",
            "attendance_records.override",
            "attendance_audit.read",
        ]
        for p_code in lecturer_perms:
            target_perm = perm_map.get(p_code)
            if target_perm:
                pair = (lecturer_role.id, target_perm.id)
                if pair not in existing_rp_pairs:
                    db.add(RolePermission(role_id=lecturer_role.id, permission_id=target_perm.id))
                    existing_rp_pairs.add(pair)

    # Student gets academic catalog, offerings, sections, and personal attendance read permissions
    student_role = role_map.get(SystemRole.STUDENT.value)
    if student_role:
        student_perms = [
            "academic_units.read",
            "academic_years.read",
            "semesters.read",
            "courses.read",
            "sections.read",
            "course_offerings.read",
            "buildings.read",
            "rooms.read",
            "timetables.read",
            "class_occurrences.read",
            "attendance.self_read",
            "devices.self_read",
            "devices.self_register",
            "devices.replacement_request",
        ]
        target_perm_ids = {perm_map[p].id for p in student_perms if p in perm_map}
        for p_code in student_perms:
            target_perm = perm_map.get(p_code)
            if target_perm:
                pair = (student_role.id, target_perm.id)
                if pair not in existing_rp_pairs:
                    db.add(RolePermission(role_id=student_role.id, permission_id=target_perm.id))
                    existing_rp_pairs.add(pair)
        for rp in existing_rps:
            if rp.role_id == student_role.id and rp.permission_id not in target_perm_ids:
                await db.delete(rp)
                existing_rp_pairs.discard((rp.role_id, rp.permission_id))

    # Auditor gets read-only permissions across all domains
    auditor_role = role_map.get(SystemRole.AUDITOR.value)
    if auditor_role:
        auditor_perms = [
            "users.read",
            "roles.read",
            "permissions.read",
            "role_assignments.read",
            "sessions.read",
            "audit.read",
            "academic_units.read",
            "academic_years.read",
            "semesters.read",
            "courses.read",
            "sections.read",
            "students.read",
            "lecturers.read",
            "course_offerings.read",
            "enrollments.read",
            "buildings.read",
            "rooms.read",
            "timetables.read",
            "class_occurrences.read",
            "attendance_policies.read",
            "attendance_sessions.read",
            "attendance_records.read",
            "attendance_audit.read",
            "devices.read",
        ]
        for aud_p_code in auditor_perms:
            target_perm = perm_map.get(aud_p_code)
            if target_perm:
                pair = (auditor_role.id, target_perm.id)
                if pair not in existing_rp_pairs:
                    db.add(RolePermission(role_id=auditor_role.id, permission_id=target_perm.id))
                    existing_rp_pairs.add(pair)

    await db.commit()
