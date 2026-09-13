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
    existing_rp_pairs = {(rp.role_id, rp.permission_id) for rp in rp_res.scalars().all()}

    # Mapping logic:
    # Super Admin gets all permissions
    super_admin_role = role_map.get(SystemRole.SUPER_ADMIN.value)
    if super_admin_role:
        for perm in perm_map.values():
            pair = (super_admin_role.id, perm.id)
            if pair not in existing_rp_pairs:
                db.add(RolePermission(role_id=super_admin_role.id, permission_id=perm.id))
                existing_rp_pairs.add(pair)

    # University Admin gets user, role assignment, and session management permissions
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
        ]
        for admin_p_code in uni_admin_perms:
            target_perm = perm_map.get(admin_p_code)
            if target_perm:
                pair = (uni_admin_role.id, target_perm.id)
                if pair not in existing_rp_pairs:
                    db.add(RolePermission(role_id=uni_admin_role.id, permission_id=target_perm.id))
                    existing_rp_pairs.add(pair)

    # Auditor gets read-only permissions
    auditor_role = role_map.get(SystemRole.AUDITOR.value)
    if auditor_role:
        auditor_perms = [
            "users.read",
            "roles.read",
            "permissions.read",
            "role_assignments.read",
            "sessions.read",
            "audit.read",
        ]
        for aud_p_code in auditor_perms:
            target_perm = perm_map.get(aud_p_code)
            if target_perm:
                pair = (auditor_role.id, target_perm.id)
                if pair not in existing_rp_pairs:
                    db.add(RolePermission(role_id=auditor_role.id, permission_id=target_perm.id))
                    existing_rp_pairs.add(pair)

    await db.commit()
