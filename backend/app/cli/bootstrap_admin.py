"""Bootstrap CLI command to provision initial University, seed RBAC, and create Super Admin."""

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from backend.app.auth.passwords import hash_password, validate_password_policy
from backend.app.core.constants import DEFAULT_LOCALE, DEFAULT_TIMEZONE, SystemRole, UserStatus
from backend.app.core.database import get_sessionmaker
from backend.app.models.role import Role
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.rbac.seeding import seed_system_rbac
from backend.app.rbac.service import RbacService


async def bootstrap_super_admin(
    username: str,
    password: str,
    university_code: str = "HU",
    university_name: str = "Herat University",
    email: str | None = None,
) -> None:
    """Provision institutional university, seed roles, and create initial Super Admin."""
    normalized_username = username.strip().lower()

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        # 1. Ensure University exists
        stmt_uni = select(University).where(University.code == university_code)
        res_uni = await session.execute(stmt_uni)
        uni = res_uni.scalar_one_or_none()

        if not uni:
            uni = University(
                name=university_name,
                code=university_code,
                timezone=DEFAULT_TIMEZONE,
                default_language=DEFAULT_LOCALE,
                status="ACTIVE",
            )
            session.add(uni)
            await session.commit()
            await session.refresh(uni)
            print(f"[+] Created initial University: {uni.name} ({uni.code}) [{uni.id}]")
        else:
            print(f"[*] University already exists: {uni.name} ({uni.code}) [{uni.id}]")

        # 2. Seed System Roles and Permissions
        print("[*] Seeding system permissions and roles...")
        await seed_system_rbac(session)
        print("[+] System permissions and roles verified.")

        # 3. Fetch SUPER_ADMIN Role
        stmt_role = select(Role).where(Role.code == SystemRole.SUPER_ADMIN.value)
        res_role = await session.execute(stmt_role)
        super_admin_role = res_role.scalar_one()

        # 4. Check if Super Admin User exists
        stmt_user = select(User).where(
            User.university_id == uni.id,
            User.username == normalized_username,
        )
        res_user = await session.execute(stmt_user)
        user = res_user.scalar_one_or_none()

        if not user:
            validate_password_policy(password)
            pw_hash = hash_password(password)

            user = User(
                university_id=uni.id,
                username=normalized_username,
                password_hash=pw_hash,
                email=email.strip().lower() if email else None,
                status=UserStatus.ACTIVE.value,
                must_change_password=False,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"[+] Created Super Admin User: {user.username} [{user.id}]")
        else:
            print(f"[*] User already exists: {user.username} [{user.id}]")

        # 5. Ensure SUPER_ADMIN role assignment exists
        roles = await RbacService.get_user_roles(session, user.id)
        if SystemRole.SUPER_ADMIN.value not in roles:
            await RbacService.assign_role(
                db=session,
                user_id=user.id,
                role_id=super_admin_role.id,
                university_id=uni.id,
                assigned_by=user.id,
            )
            print(
                f"[+] Assigned role {super_admin_role.code} to {user.username} at UNIVERSITY scope."
            )
        else:
            print(f"[*] User {user.username} already possesses {super_admin_role.code} role.")

    print("\n[SUCCESS] Super Admin bootstrap completed successfully.")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Bootstrap Digital Student Attendance System Super Admin.",
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Super Admin username (default: admin)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Super Admin password (if omitted, will be prompted securely)",
    )
    parser.add_argument(
        "--university-code",
        default="HU",
        help="Institutional university code (default: HU)",
    )
    parser.add_argument(
        "--university-name",
        default="Herat University",
        help="Institutional university name (default: Herat University)",
    )
    parser.add_argument(
        "--email",
        default="admin@hu.edu.af",
        help="Super Admin email address",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()

    password = args.password
    if not password:
        password = getpass.getpass(f"Enter password for user '{args.username}': ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("[ERROR] Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    try:
        asyncio.run(
            bootstrap_super_admin(
                username=args.username,
                password=password,
                university_code=args.university_code,
                university_name=args.university_name,
                email=args.email,
            )
        )
    except Exception as e:
        print(f"[FATAL] Bootstrap failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
