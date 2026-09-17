"""Course Offering import domain processor."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import ImportRowAction, ImportRowStatus, OfferingStatus
from backend.app.imports.processors.base import BaseImportProcessor
from backend.app.imports.schemas import ImportTemplateColumn
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.course import Course
from backend.app.models.course_offering import CourseOffering
from backend.app.models.import_job import ImportRow
from backend.app.models.section import Section
from backend.app.models.semester import Semester


class CourseOfferingImportProcessor(BaseImportProcessor):
    """Domain processor for validating and committing semester course offerings."""

    def get_required_headers(self) -> list[str]:
        return ["course_code", "semester_code"]

    def get_template(self) -> list[ImportTemplateColumn]:
        return [
            ImportTemplateColumn(
                name="course_code",
                required=True,
                description="Institutional course catalog code",
                example="CS-101",
            ),
            ImportTemplateColumn(
                name="semester_code",
                required=True,
                description="Active academic semester code",
                example="FALL-2026",
            ),
            ImportTemplateColumn(
                name="section_code",
                required=False,
                description="Section cohort code (if offering is section-specific)",
                example="CS-SEC-A",
            ),
            ImportTemplateColumn(
                name="academic_unit_code",
                required=False,
                description="Hosting faculty or department code",
                example="CS",
            ),
            ImportTemplateColumn(
                name="status",
                required=False,
                description="Offering status: ACTIVE, CANCELLED, COMPLETED",
                example="ACTIVE",
            ),
        ]

    def get_sample_csv(self) -> str:
        return (
            "course_code,semester_code,section_code,academic_unit_code,status\n"
            "CS-101,FALL-2026,CS-SEC-A,CS,ACTIVE\n"
            "MATH-101,FALL-2026,MATH-SEC-1,MATH,ACTIVE\n"
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
        course_code = raw_data.get("course_code")
        if not course_code:
            errors.append(
                {
                    "field": "course_code",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Course code is required.",
                }
            )

        semester_code = raw_data.get("semester_code")
        if not semester_code:
            errors.append(
                {
                    "field": "semester_code",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Semester code is required.",
                }
            )

        if not course_code or not semester_code:
            return normalized_data, action, ImportRowStatus.ERROR.value, errors, warnings

        c_code_clean = str(course_code).strip()
        s_code_clean = str(semester_code).strip()
        sec_code_raw = raw_data.get("section_code")
        sec_code_clean = str(sec_code_raw).strip() if sec_code_raw else None

        # 2. Check intra-file duplicate
        offering_key = (
            c_code_clean.lower(),
            s_code_clean.lower(),
            sec_code_clean.lower() if sec_code_clean else "",
        )
        seen_offerings: set[tuple[str, str, str]] = seen_keys.setdefault("offerings", set())
        if offering_key in seen_offerings:
            errors.append(
                {
                    "field": "course_code",
                    "code": "DUPLICATE_IN_FILE",
                    "message": (
                        f"Offering for course '{c_code_clean}', semester '{s_code_clean}', "
                        f"section '{sec_code_clean or 'None'}' appears multiple times in file."
                    ),
                }
            )
        else:
            seen_offerings.add(offering_key)

        # 3. Resolve Course
        c_stmt = select(Course).where(
            Course.university_id == university_id,
            func.lower(Course.code) == c_code_clean.lower(),
        )
        c_res = await db.execute(c_stmt)
        course = c_res.scalar_one_or_none()
        if not course:
            errors.append(
                {
                    "field": "course_code",
                    "code": "COURSE_NOT_FOUND",
                    "message": f"Course '{c_code_clean}' not found in this university.",
                }
            )
        else:
            normalized_data["course_id"] = str(course.id)

        # 4. Resolve Semester
        sem_stmt = select(Semester).where(
            Semester.university_id == university_id,
            func.lower(Semester.code) == s_code_clean.lower(),
        )
        sem_res = await db.execute(sem_stmt)
        semester = sem_res.scalar_one_or_none()
        if not semester:
            errors.append(
                {
                    "field": "semester_code",
                    "code": "SEMESTER_NOT_FOUND",
                    "message": f"Semester '{s_code_clean}' not found in this university.",
                }
            )
        else:
            normalized_data["semester_id"] = str(semester.id)

        # 5. Resolve Section if provided
        section = None
        if sec_code_clean:
            sec_stmt = select(Section).where(
                Section.university_id == university_id,
                func.lower(Section.code) == sec_code_clean.lower(),
            )
            if semester:
                sec_stmt = sec_stmt.where(
                    (Section.semester_id == semester.id) | (Section.semester_id.is_(None))
                )
            sec_res = await db.execute(sec_stmt)
            section = sec_res.scalar_one_or_none()
            if not section:
                errors.append(
                    {
                        "field": "section_code",
                        "code": "SECTION_NOT_FOUND",
                        "message": f"Section '{sec_code_clean}' not found in this university.",
                    }
                )
            else:
                normalized_data["section_id"] = str(section.id)

        # 6. Resolve Academic Unit if provided
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

        # 7. Validate Status
        status_val = raw_data.get("status")
        if status_val:
            s_upper = str(status_val).upper().strip()
            if s_upper not in {s.value for s in OfferingStatus}:
                allowed = [s.value for s in OfferingStatus]
                errors.append(
                    {
                        "field": "status",
                        "code": "INVALID_STATUS",
                        "message": f"Invalid offering status '{status_val}'. Allowed: {allowed}",
                    }
                )
            else:
                normalized_data["status"] = s_upper
        else:
            normalized_data["status"] = OfferingStatus.ACTIVE.value

        # 8. Check Database Existence
        if course and semester:
            exist_stmt = select(CourseOffering).where(
                CourseOffering.university_id == university_id,
                CourseOffering.course_id == course.id,
                CourseOffering.semester_id == semester.id,
            )
            if section:
                exist_stmt = exist_stmt.where(CourseOffering.section_id == section.id)
            else:
                exist_stmt = exist_stmt.where(CourseOffering.section_id.is_(None))

            exist_res = await db.execute(exist_stmt)
            existing_offering = exist_res.scalar_one_or_none()
            if existing_offering:
                action = ImportRowAction.UPDATE.value
                warnings.append(
                    {
                        "field": "course_code",
                        "code": "OFFERING_ALREADY_EXISTS",
                        "message": "Course offering already exists and will be updated on commit.",
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
        course_id = uuid.UUID(data["course_id"])
        semester_id = uuid.UUID(data["semester_id"])
        section_id = uuid.UUID(data["section_id"]) if data.get("section_id") else None
        unit_id = uuid.UUID(data["academic_unit_id"]) if data.get("academic_unit_id") else None
        offering_status = data.get("status") or OfferingStatus.ACTIVE.value

        stmt = select(CourseOffering).where(
            CourseOffering.university_id == university_id,
            CourseOffering.course_id == course_id,
            CourseOffering.semester_id == semester_id,
        )
        if section_id:
            stmt = stmt.where(CourseOffering.section_id == section_id)
        else:
            stmt = stmt.where(CourseOffering.section_id.is_(None))

        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            if unit_id is not None:
                existing.academic_unit_id = unit_id
            existing.status = offering_status
            await db.flush()
            return existing.id, "CourseOffering"

        new_offering = CourseOffering(
            university_id=university_id,
            course_id=course_id,
            semester_id=semester_id,
            section_id=section_id,
            academic_unit_id=unit_id,
            status=offering_status,
        )
        db.add(new_offering)
        await db.flush()
        return new_offering.id, "CourseOffering"
