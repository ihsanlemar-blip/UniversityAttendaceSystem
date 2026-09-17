"""Course import domain processor."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import ImportRowAction, ImportRowStatus, RecordStatus
from backend.app.imports.processors.base import BaseImportProcessor
from backend.app.imports.schemas import ImportTemplateColumn
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.course import Course
from backend.app.models.import_job import ImportRow


class CourseImportProcessor(BaseImportProcessor):
    """Domain processor for validating and committing course catalog data."""

    def get_required_headers(self) -> list[str]:
        return ["code", "name"]

    def get_template(self) -> list[ImportTemplateColumn]:
        return [
            ImportTemplateColumn(
                name="code",
                required=True,
                description="Unique institutional course code",
                example="CS-101",
            ),
            ImportTemplateColumn(
                name="name",
                required=True,
                description="Course title / name (supports Dari, Pashto, English)",
                example="مقدمه ای بر علوم کامپیوتر / Intro to CS",
            ),
            ImportTemplateColumn(
                name="credit_hours",
                required=False,
                description="Academic credit hours (positive integer)",
                example="3",
            ),
            ImportTemplateColumn(
                name="academic_unit_code",
                required=False,
                description="Faculty or department offering this course",
                example="CS",
            ),
            ImportTemplateColumn(
                name="description",
                required=False,
                description="Catalog syllabus overview or description",
                example="Foundational computing paradigms and programming basics.",
            ),
            ImportTemplateColumn(
                name="status",
                required=False,
                description="Record status: ACTIVE or INACTIVE",
                example="ACTIVE",
            ),
        ]

    def get_sample_csv(self) -> str:
        return (
            "code,name,credit_hours,academic_unit_code,description,status\n"
            "CS-101,مقدمه بر علوم کامپیوتر,3,CS,Foundational computer science,ACTIVE\n"
            "MATH-101,Calculus I,4,MATH,Differential and integral calculus,ACTIVE\n"
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
        code = raw_data.get("code")
        if not code:
            errors.append(
                {
                    "field": "code",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Course code is required.",
                }
            )

        name = raw_data.get("name")
        if not name:
            errors.append(
                {
                    "field": "name",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Course name is required.",
                }
            )

        if not code:
            return normalized_data, action, ImportRowStatus.ERROR.value, errors, warnings

        # 2. Check intra-file duplicate
        clean_code = str(code).strip()
        code_lower = clean_code.lower()
        seen_codes: set[str] = seen_keys.setdefault("course_codes", set())
        if code_lower in seen_codes:
            errors.append(
                {
                    "field": "code",
                    "code": "DUPLICATE_IN_FILE",
                    "message": f"Course code '{clean_code}' appears multiple times in file.",
                }
            )
        else:
            seen_codes.add(code_lower)

        # 3. Credit hours validation
        credits_raw = raw_data.get("credit_hours")
        if credits_raw is not None and str(credits_raw).strip() != "":
            try:
                credits_val = int(credits_raw)
                if credits_val < 0 or credits_val > 30:
                    errors.append(
                        {
                            "field": "credit_hours",
                            "code": "INVALID_CREDIT_HOURS",
                            "message": "Credit hours must be between 0 and 30.",
                        }
                    )
                else:
                    normalized_data["credit_hours"] = credits_val
            except ValueError, TypeError:
                errors.append(
                    {
                        "field": "credit_hours",
                        "code": "INVALID_CREDIT_HOURS",
                        "message": f"Invalid integer value for credit hours: '{credits_raw}'.",
                    }
                )

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
            if s_upper not in {s.value for s in RecordStatus}:
                allowed = [s.value for s in RecordStatus]
                errors.append(
                    {
                        "field": "status",
                        "code": "INVALID_STATUS",
                        "message": f"Invalid status '{status_val}'. Allowed: {allowed}",
                    }
                )
            else:
                normalized_data["status"] = s_upper
        else:
            normalized_data["status"] = RecordStatus.ACTIVE.value

        # 6. Check Database Existence
        existing_stmt = select(Course).where(
            Course.university_id == university_id,
            func.lower(Course.code) == code_lower,
        )
        existing_res = await db.execute(existing_stmt)
        existing_course = existing_res.scalar_one_or_none()

        if existing_course:
            action = ImportRowAction.UPDATE.value
            warnings.append(
                {
                    "field": "code",
                    "code": "COURSE_ALREADY_EXISTS",
                    "message": f"Course '{clean_code}' exists and will be updated on commit.",
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
        code = str(data["code"]).strip()
        name = str(data["name"]).strip()
        credit_hours = int(data["credit_hours"]) if data.get("credit_hours") is not None else None
        unit_id = uuid.UUID(data["academic_unit_id"]) if data.get("academic_unit_id") else None
        description = str(data["description"]).strip() if data.get("description") else None
        status = data.get("status") or RecordStatus.ACTIVE.value

        stmt = select(Course).where(
            Course.university_id == university_id,
            func.lower(Course.code) == code.lower(),
        )
        existing_course = (await db.execute(stmt)).scalar_one_or_none()

        if existing_course:
            existing_course.name = name
            if credit_hours is not None:
                existing_course.credit_hours = credit_hours
            if unit_id is not None:
                existing_course.academic_unit_id = unit_id
            if description is not None:
                existing_course.description = description
            existing_course.status = status
            await db.flush()
            return existing_course.id, "Course"

        new_course = Course(
            university_id=university_id,
            code=code,
            name=name,
            credit_hours=credit_hours,
            academic_unit_id=unit_id,
            description=description,
            status=status,
        )
        db.add(new_course)
        await db.flush()
        return new_course.id, "Course"
