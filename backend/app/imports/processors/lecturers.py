"""Lecturer import domain processor."""

import secrets
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import hash_password
from backend.app.common.types import utc_now
from backend.app.core.constants import (
    ImportRowAction,
    ImportRowStatus,
    LecturerStatus,
    ScopeType,
    SystemRole,
    UserStatus,
)
from backend.app.imports.processors.base import BaseImportProcessor
from backend.app.imports.schemas import ImportTemplateColumn
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.import_job import ImportRow
from backend.app.models.lecturer import Lecturer
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.user import User


class LecturerImportProcessor(BaseImportProcessor):
    """Domain processor for validating and committing lecturer / instructor profiles."""

    def get_required_headers(self) -> list[str]:
        return ["employee_code", "first_name", "last_name"]

    def get_template(self) -> list[ImportTemplateColumn]:
        return [
            ImportTemplateColumn(
                name="employee_code",
                required=True,
                description="Unique institutional employee code / payroll ID",
                example="EMP-LEC-101",
            ),
            ImportTemplateColumn(
                name="first_name",
                required=True,
                description="Lecturer given name (supports Dari, Pashto, English)",
                example="استاد نورالله / Dr. Noorullah",
            ),
            ImportTemplateColumn(
                name="last_name",
                required=True,
                description="Lecturer family name (supports Dari, Pashto, English)",
                example="کریمی / Karimi",
            ),
            ImportTemplateColumn(
                name="email",
                required=False,
                description="Institutional academic email address",
                example="noorullah.karimi@kabul.edu.af",
            ),
            ImportTemplateColumn(
                name="phone",
                required=False,
                description="Faculty contact telephone number",
                example="+93799123456",
            ),
            ImportTemplateColumn(
                name="academic_unit_code",
                required=False,
                description="Faculty or department code matching academic catalog",
                example="CS",
            ),
            ImportTemplateColumn(
                name="title",
                required=False,
                description="Academic title (e.g. Professor, Assistant Professor, Lecturer)",
                example="Assistant Professor",
            ),
            ImportTemplateColumn(
                name="username",
                required=False,
                description="Custom login username (defaults to lowercase employee code)",
                example="emp_lec_101",
            ),
            ImportTemplateColumn(
                name="status",
                required=False,
                description="Profile status: ACTIVE, ON_LEAVE, SUSPENDED, TERMINATED",
                example="ACTIVE",
            ),
        ]

    def get_sample_csv(self) -> str:
        return (
            "employee_code,first_name,last_name,email,phone,academic_unit_code,title,status\n"
            "EMP-LEC-101,نورالله,کریمی,noor@kabul.edu.af,+93799123456,CS,Professor,ACTIVE\n"
            "EMP-LEC-102,Zalmay,Hotak,zalmay.hotak@kabul.edu.af,+93799654321,CS,Lecturer,ACTIVE\n"
        )

    async def validate_row(
        self,
        db: AsyncSession,
        university_id: uuid.UUID,
        row_number: int,
        raw_data: dict[str, Any],
        seen_keys: dict[str, Any],
    ) -> tuple[dict[str, Any], str, str, list[dict[str, Any]], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        normalized_data: dict[str, Any] = dict(raw_data)
        action = ImportRowAction.CREATE.value

        # 1. Required fields
        employee_code = raw_data.get("employee_code")
        if not employee_code:
            errors.append(
                {
                    "field": "employee_code",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Employee code is required.",
                }
            )

        first_name = raw_data.get("first_name")
        if not first_name:
            errors.append(
                {
                    "field": "first_name",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "First name is required.",
                }
            )

        last_name = raw_data.get("last_name")
        if not last_name:
            errors.append(
                {
                    "field": "last_name",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Last name is required.",
                }
            )

        if not employee_code:
            return normalized_data, action, ImportRowStatus.ERROR.value, errors, warnings

        # 2. Check intra-file duplicate
        clean_code = str(employee_code).strip()
        code_lower = clean_code.lower()
        seen_codes: set[str] = seen_keys.setdefault("employee_codes", set())
        if code_lower in seen_codes:
            errors.append(
                {
                    "field": "employee_code",
                    "code": "DUPLICATE_IN_FILE",
                    "message": f"Employee code '{clean_code}' appears multiple times in file.",
                }
            )
        else:
            seen_codes.add(code_lower)

        # 3. Username resolution
        username_raw = raw_data.get("username")
        if username_raw:
            username = str(username_raw).strip().lower()
        else:
            username = code_lower.replace("-", "_").replace(" ", "_")
        normalized_data["username"] = username

        seen_usernames: set[str] = seen_keys.setdefault("usernames", set())
        if username in seen_usernames:
            errors.append(
                {
                    "field": "username",
                    "code": "DUPLICATE_USERNAME_IN_FILE",
                    "message": f"Username '{username}' appears multiple times in file.",
                }
            )
        else:
            seen_usernames.add(username)

        # 4. Resolve Academic Unit
        unit_code = raw_data.get("academic_unit_code")
        if unit_code:
            u_stmt = select(AcademicUnit).where(
                AcademicUnit.university_id == university_id,
                func.lower(AcademicUnit.code) == str(unit_code).strip().lower(),
            )
            u_res = await db.execute(u_stmt)
            unit = u_res.scalar_one_or_none()
            if not unit:
                errors.append(
                    {
                        "field": "academic_unit_code",
                        "code": "ACADEMIC_UNIT_NOT_FOUND",
                        "message": f"Academic unit '{unit_code}' not found in this university.",
                    }
                )
            else:
                normalized_data["academic_unit_id"] = str(unit.id)

        # 5. Validate Status
        status_val = raw_data.get("status")
        if status_val:
            s_upper = str(status_val).upper().strip()
            if s_upper not in {s.value for s in LecturerStatus}:
                allowed = [s.value for s in LecturerStatus]
                errors.append(
                    {
                        "field": "status",
                        "code": "INVALID_STATUS",
                        "message": f"Invalid lecturer status '{status_val}'. Allowed: {allowed}",
                    }
                )
            else:
                normalized_data["status"] = s_upper
        else:
            normalized_data["status"] = LecturerStatus.ACTIVE.value

        # 6. Check Database Existence
        existing_stmt = select(Lecturer).where(
            Lecturer.university_id == university_id,
            func.lower(Lecturer.employee_code) == code_lower,
        )
        existing_res = await db.execute(existing_stmt)
        existing_lec = existing_res.scalar_one_or_none()

        if existing_lec:
            action = ImportRowAction.UPDATE.value
            warnings.append(
                {
                    "field": "employee_code",
                    "code": "LECTURER_ALREADY_EXISTS",
                    "message": f"Lecturer '{clean_code}' exists and will be updated on commit.",
                }
            )
        else:
            # Check user table collision
            u_user_stmt = select(User).where(
                User.university_id == university_id,
                func.lower(User.username) == username,
            )
            u_user_res = await db.execute(u_user_stmt)
            existing_user = u_user_res.scalar_one_or_none()
            if existing_user:
                link_stmt = select(Lecturer).where(Lecturer.user_id == existing_user.id)
                linked_res = await db.execute(link_stmt)
                linked_lec = linked_res.scalar_one_or_none()
                if linked_lec:
                    errors.append(
                        {
                            "field": "username",
                            "code": "USER_ALREADY_LINKED",
                            "message": (
                                f"User '{username}' is already linked to "
                                f"lecturer '{linked_lec.employee_code}'."
                            ),
                        }
                    )

        status = (
            ImportRowStatus.ERROR.value
            if errors
            else (ImportRowStatus.WARNING.value if warnings else ImportRowStatus.VALID.value)
        )
        return normalized_data, action, status, errors, warnings

    async def commit_row(
        self,
        db: AsyncSession,
        university_id: uuid.UUID,
        staged_row: ImportRow,
        actor_user_id: uuid.UUID,
    ) -> tuple[uuid.UUID, str]:
        data = staged_row.normalized_data or staged_row.raw_data
        employee_code = str(data["employee_code"]).strip()
        username = (
            str(data.get("username") or employee_code.lower().replace("-", "_")).strip().lower()
        )

        unit_id = uuid.UUID(data["academic_unit_id"]) if data.get("academic_unit_id") else None
        title = str(data["title"]).strip() if data.get("title") else None
        lec_status = data.get("status") or LecturerStatus.ACTIVE.value

        # 1. Look up existing lecturer
        stmt = select(Lecturer).where(
            Lecturer.university_id == university_id,
            func.lower(Lecturer.employee_code) == employee_code.lower(),
        )
        existing_lec = (await db.execute(stmt)).scalar_one_or_none()

        if existing_lec:
            if unit_id is not None:
                existing_lec.academic_unit_id = unit_id
            if title is not None:
                existing_lec.title = title
            if lec_status:
                existing_lec.status = lec_status

            user = await db.get(User, existing_lec.user_id)
            if user:
                if data.get("email"):
                    user.email = str(data["email"]).strip()
                if data.get("phone"):
                    user.phone = str(data["phone"]).strip()

            await db.flush()
            return existing_lec.id, "Lecturer"

        # 2. Look up or create user
        u_stmt = select(User).where(
            User.university_id == university_id,
            func.lower(User.username) == username,
        )
        user = (await db.execute(u_stmt)).scalar_one_or_none()

        if not user:
            temp_password = f"Tmp!{secrets.token_urlsafe(16)}"
            user = User(
                university_id=university_id,
                username=username,
                password_hash=hash_password(temp_password),
                email=str(data["email"]).strip() if data.get("email") else None,
                phone=str(data["phone"]).strip() if data.get("phone") else None,
                status=UserStatus.ACTIVE.value,
                must_change_password=True,
            )
            db.add(user)
            await db.flush()

            # Assign Lecturer system role
            role_stmt = select(Role).where(Role.code == SystemRole.LECTURER.value)
            role = (await db.execute(role_stmt)).scalar_one_or_none()
            if role:
                assignment = RoleAssignment(
                    user_id=user.id,
                    role_id=role.id,
                    university_id=university_id,
                    scope_type=ScopeType.UNIVERSITY.value,
                    scope_id=university_id,
                    assigned_at=utc_now(),
                    assigned_by=actor_user_id,
                )
                db.add(assignment)
                await db.flush()

        # 3. Create Lecturer profile
        new_lec = Lecturer(
            user_id=user.id,
            university_id=university_id,
            employee_code=employee_code,
            academic_unit_id=unit_id,
            title=title,
            status=lec_status,
        )
        db.add(new_lec)
        await db.flush()
        return new_lec.id, "Lecturer"
