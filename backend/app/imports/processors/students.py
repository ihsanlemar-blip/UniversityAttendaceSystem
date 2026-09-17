"""Student import domain processor."""

import datetime
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
    ScopeType,
    StudentStatus,
    SystemRole,
    UserStatus,
)
from backend.app.imports.processors.base import BaseImportProcessor
from backend.app.imports.schemas import ImportTemplateColumn
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.import_job import ImportRow
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.section import Section
from backend.app.models.student import Student
from backend.app.models.user import User


class StudentImportProcessor(BaseImportProcessor):
    """Domain processor for validating and committing student rosters."""

    def get_required_headers(self) -> list[str]:
        return ["student_number", "first_name", "last_name"]

    def get_template(self) -> list[ImportTemplateColumn]:
        return [
            ImportTemplateColumn(
                name="student_number",
                required=True,
                description="Unique institutional student registration number",
                example="CS-2026-001",
            ),
            ImportTemplateColumn(
                name="first_name",
                required=True,
                description="Student first / given name (supports Dari, Pashto, English)",
                example="احمد / Ahmad",
            ),
            ImportTemplateColumn(
                name="last_name",
                required=True,
                description="Student last / family name (supports Dari, Pashto, English)",
                example="محمدی / Mohammadi",
            ),
            ImportTemplateColumn(
                name="email",
                required=False,
                description="Student official or personal email address",
                example="ahmad@kabul.edu.af",
            ),
            ImportTemplateColumn(
                name="phone",
                required=False,
                description="Student contact telephone number",
                example="+93700123456",
            ),
            ImportTemplateColumn(
                name="academic_unit_code",
                required=False,
                description="Faculty or department code matching academic catalog",
                example="CS",
            ),
            ImportTemplateColumn(
                name="section_code",
                required=False,
                description="Assigned student section cohort code",
                example="CS-SEC-A",
            ),
            ImportTemplateColumn(
                name="admission_date",
                required=False,
                description="Date of admission in YYYY-MM-DD format",
                example="2026-03-21",
            ),
            ImportTemplateColumn(
                name="username",
                required=False,
                description="Custom login username (defaults to lowercase student number)",
                example="cs_2026_001",
            ),
            ImportTemplateColumn(
                name="status",
                required=False,
                description="Profile status: ACTIVE, SUSPENDED, GRADUATED, WITHDRAWN, EXPELLED",
                example="ACTIVE",
            ),
        ]

    def get_sample_csv(self) -> str:
        return (
            "student_number,first_name,last_name,email,phone,academic_unit_code,section_code,admission_date,status\n"
            "CS-2026-001,احمد,محمدی,ahmad@kabul.edu.af,+93700123456,CS,CS-SEC-A,2026-03-21,ACTIVE\n"
            "CS-2026-002,Farhad,Rahimi,farhad@kabul.edu.af,+93700654321,CS,CS-SEC-A,2026-03-21,ACTIVE\n"
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
        student_number = raw_data.get("student_number")
        if not student_number:
            errors.append(
                {
                    "field": "student_number",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Student number is required.",
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

        if not student_number:
            return normalized_data, action, ImportRowStatus.ERROR.value, errors, warnings

        # 2. Check intra-file duplicate
        clean_snum = str(student_number).strip()
        snum_lower = clean_snum.lower()
        seen_snums: set[str] = seen_keys.setdefault("student_numbers", set())
        if snum_lower in seen_snums:
            errors.append(
                {
                    "field": "student_number",
                    "code": "DUPLICATE_IN_FILE",
                    "message": f"Student number '{clean_snum}' appears multiple times in file.",
                }
            )
        else:
            seen_snums.add(snum_lower)

        # 3. Username resolution
        username_raw = raw_data.get("username")
        if username_raw:
            username = str(username_raw).strip().lower()
        else:
            username = snum_lower.replace("-", "_").replace(" ", "_")
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

        # 5. Resolve Section
        sec_code = raw_data.get("section_code")
        if sec_code:
            sec_stmt = select(Section).where(
                Section.university_id == university_id,
                func.lower(Section.code) == str(sec_code).strip().lower(),
            )
            sec_res = await db.execute(sec_stmt)
            section = sec_res.scalar_one_or_none()
            if not section:
                errors.append(
                    {
                        "field": "section_code",
                        "code": "SECTION_NOT_FOUND",
                        "message": f"Section '{sec_code}' not found in this university.",
                    }
                )
            else:
                normalized_data["section_id"] = str(section.id)

        # 6. Validate Admission Date
        adm_date_raw = raw_data.get("admission_date")
        if adm_date_raw:
            if isinstance(adm_date_raw, str):
                try:
                    datetime.date.fromisoformat(adm_date_raw)
                except ValueError:
                    errors.append(
                        {
                            "field": "admission_date",
                            "code": "INVALID_DATE_FORMAT",
                            "message": f"Date '{adm_date_raw}' is not valid ISO (YYYY-MM-DD).",
                        }
                    )

        # 7. Validate Status
        status_val = raw_data.get("status")
        if status_val:
            s_upper = str(status_val).upper().strip()
            if s_upper not in {s.value for s in StudentStatus}:
                allowed = [s.value for s in StudentStatus]
                errors.append(
                    {
                        "field": "status",
                        "code": "INVALID_STATUS",
                        "message": f"Invalid student status '{status_val}'. Allowed: {allowed}",
                    }
                )
            else:
                normalized_data["status"] = s_upper
        else:
            normalized_data["status"] = StudentStatus.ACTIVE.value

        # 8. Check Database Existence
        existing_stmt = select(Student).where(
            Student.university_id == university_id,
            func.lower(Student.student_number) == snum_lower,
        )
        existing_res = await db.execute(existing_stmt)
        existing_student = existing_res.scalar_one_or_none()

        if existing_student:
            action = ImportRowAction.UPDATE.value
            warnings.append(
                {
                    "field": "student_number",
                    "code": "STUDENT_ALREADY_EXISTS",
                    "message": f"Student '{clean_snum}' exists and will be updated on commit.",
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
                # Check if this user is linked to another student
                link_stmt = select(Student).where(Student.user_id == existing_user.id)
                linked_res = await db.execute(link_stmt)
                linked_student = linked_res.scalar_one_or_none()
                if linked_student:
                    errors.append(
                        {
                            "field": "username",
                            "code": "USER_ALREADY_LINKED",
                            "message": (
                                f"User '{username}' is already linked to "
                                f"student '{linked_student.student_number}'."
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
        student_number = str(data["student_number"]).strip()
        username = (
            str(data.get("username") or student_number.lower().replace("-", "_")).strip().lower()
        )

        unit_id = uuid.UUID(data["academic_unit_id"]) if data.get("academic_unit_id") else None
        section_id = uuid.UUID(data["section_id"]) if data.get("section_id") else None
        adm_date = None
        if data.get("admission_date"):
            adm_date = datetime.date.fromisoformat(str(data["admission_date"]))
        student_status = data.get("status") or StudentStatus.ACTIVE.value

        # 1. Look up existing student
        stmt = select(Student).where(
            Student.university_id == university_id,
            func.lower(Student.student_number) == student_number.lower(),
        )
        existing_student = (await db.execute(stmt)).scalar_one_or_none()

        if existing_student:
            if unit_id is not None:
                existing_student.academic_unit_id = unit_id
            if section_id is not None:
                existing_student.section_id = section_id
            if adm_date is not None:
                existing_student.admission_date = adm_date
            if student_status:
                existing_student.status = student_status

            user = await db.get(User, existing_student.user_id)
            if user:
                if data.get("email"):
                    user.email = str(data["email"]).strip()
                if data.get("phone"):
                    user.phone = str(data["phone"]).strip()

            await db.flush()
            return existing_student.id, "Student"

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

            # Assign Student system role
            role_stmt = select(Role).where(Role.code == SystemRole.STUDENT.value)
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

        # 3. Create Student profile
        new_student = Student(
            user_id=user.id,
            university_id=university_id,
            student_number=student_number,
            academic_unit_id=unit_id,
            section_id=section_id,
            admission_date=adm_date,
            status=student_status,
        )
        db.add(new_student)
        await db.flush()
        return new_student.id, "Student"
