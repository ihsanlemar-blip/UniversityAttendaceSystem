"""Enrollment import domain processor."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import EnrollmentStatus, ImportRowAction, ImportRowStatus
from backend.app.imports.processors.base import BaseImportProcessor
from backend.app.imports.schemas import ImportTemplateColumn
from backend.app.models.course import Course
from backend.app.models.course_offering import CourseOffering
from backend.app.models.enrollment import Enrollment
from backend.app.models.import_job import ImportRow
from backend.app.models.section import Section
from backend.app.models.semester import Semester
from backend.app.models.student import Student


class EnrollmentImportProcessor(BaseImportProcessor):
    """Domain processor for validating and committing student class roster enrollments."""

    def get_required_headers(self) -> list[str]:
        return ["student_number", "course_code", "semester_code"]

    def get_template(self) -> list[ImportTemplateColumn]:
        return [
            ImportTemplateColumn(
                name="student_number",
                required=True,
                description="Unique institutional student registration number",
                example="CS-2026-001",
            ),
            ImportTemplateColumn(
                name="course_code",
                required=True,
                description="Catalog course code being enrolled",
                example="CS-101",
            ),
            ImportTemplateColumn(
                name="semester_code",
                required=True,
                description="Target academic semester code",
                example="FALL-2026",
            ),
            ImportTemplateColumn(
                name="section_code",
                required=False,
                description="Section code (required if offering is partitioned by section)",
                example="CS-SEC-A",
            ),
            ImportTemplateColumn(
                name="status",
                required=False,
                description="Enrollment status: ACTIVE, DROPPED, COMPLETED, AUDIT",
                example="ACTIVE",
            ),
        ]

    def get_sample_csv(self) -> str:
        return (
            "student_number,course_code,semester_code,section_code,status\n"
            "CS-2026-001,CS-101,FALL-2026,CS-SEC-A,ACTIVE\n"
            "CS-2026-002,CS-101,FALL-2026,CS-SEC-A,ACTIVE\n"
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

        if not student_number or not course_code or not semester_code:
            return normalized_data, action, ImportRowStatus.ERROR.value, errors, warnings

        s_num_clean = str(student_number).strip()
        c_code_clean = str(course_code).strip()
        sem_code_clean = str(semester_code).strip()
        sec_code_raw = raw_data.get("section_code")
        sec_code_clean = str(sec_code_raw).strip() if sec_code_raw else None

        # 2. Check intra-file duplicate
        enrollment_key = (
            s_num_clean.lower(),
            c_code_clean.lower(),
            sem_code_clean.lower(),
            sec_code_clean.lower() if sec_code_clean else "",
        )
        seen_enrollments: set[tuple[str, str, str, str]] = seen_keys.setdefault(
            "enrollments", set()
        )
        if enrollment_key in seen_enrollments:
            errors.append(
                {
                    "field": "student_number",
                    "code": "DUPLICATE_IN_FILE",
                    "message": (
                        f"Enrollment for student '{s_num_clean}' in course '{c_code_clean}' "
                        f"semester '{sem_code_clean}' appears multiple times in file."
                    ),
                }
            )
        else:
            seen_enrollments.add(enrollment_key)

        # 3. Resolve Student
        s_stmt = select(Student).where(
            Student.university_id == university_id,
            func.lower(Student.student_number) == s_num_clean.lower(),
        )
        s_res = await db.execute(s_stmt)
        student = s_res.scalar_one_or_none()
        if not student:
            errors.append(
                {
                    "field": "student_number",
                    "code": "STUDENT_NOT_FOUND",
                    "message": f"Student '{s_num_clean}' not found in this university.",
                }
            )
        else:
            normalized_data["student_id"] = str(student.id)

        # 4. Resolve Course
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

        # 5. Resolve Semester
        sem_stmt = select(Semester).where(
            Semester.university_id == university_id,
            func.lower(Semester.code) == sem_code_clean.lower(),
        )
        sem_res = await db.execute(sem_stmt)
        semester = sem_res.scalar_one_or_none()
        if not semester:
            errors.append(
                {
                    "field": "semester_code",
                    "code": "SEMESTER_NOT_FOUND",
                    "message": f"Semester '{sem_code_clean}' not found in this university.",
                }
            )

        # 6. Resolve Section if provided
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

        # 7. Resolve Course Offering
        offering = None
        if course and semester:
            off_stmt = select(CourseOffering).where(
                CourseOffering.university_id == university_id,
                CourseOffering.course_id == course.id,
                CourseOffering.semester_id == semester.id,
            )
            if section:
                off_stmt = off_stmt.where(CourseOffering.section_id == section.id)
            elif sec_code_clean is None:
                off_stmt = off_stmt.where(CourseOffering.section_id.is_(None))

            off_res = await db.execute(off_stmt)
            offering = off_res.scalar_one_or_none()
            if not offering:
                errors.append(
                    {
                        "field": "course_code",
                        "code": "COURSE_OFFERING_NOT_FOUND",
                        "message": (
                            f"No active course offering found for course '{c_code_clean}', "
                            f"semester '{sem_code_clean}', section '{sec_code_clean or 'None'}'."
                        ),
                    }
                )
            else:
                normalized_data["course_offering_id"] = str(offering.id)

        # 8. Validate Status
        status_val = raw_data.get("status")
        if status_val:
            s_upper = str(status_val).upper().strip()
            if s_upper not in {s.value for s in EnrollmentStatus}:
                allowed = [s.value for s in EnrollmentStatus]
                errors.append(
                    {
                        "field": "status",
                        "code": "INVALID_STATUS",
                        "message": f"Invalid enrollment status '{status_val}'. Allowed: {allowed}",
                    }
                )
            else:
                normalized_data["status"] = s_upper
        else:
            normalized_data["status"] = EnrollmentStatus.ACTIVE.value

        # 9. Check Database Existence
        if student and offering:
            exist_stmt = select(Enrollment).where(
                Enrollment.course_offering_id == offering.id,
                Enrollment.student_id == student.id,
            )
            exist_res = await db.execute(exist_stmt)
            existing_enrollment = exist_res.scalar_one_or_none()
            if existing_enrollment:
                action = ImportRowAction.UPDATE.value
                warnings.append(
                    {
                        "field": "student_number",
                        "code": "ENROLLMENT_ALREADY_EXISTS",
                        "message": (
                            f"Student '{s_num_clean}' is already enrolled in this course offering. "
                            "Status will be updated upon commit."
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
        course_offering_id = uuid.UUID(data["course_offering_id"])
        student_id = uuid.UUID(data["student_id"])
        enrollment_status = data.get("status") or EnrollmentStatus.ACTIVE.value

        stmt = select(Enrollment).where(
            Enrollment.course_offering_id == course_offering_id,
            Enrollment.student_id == student_id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.status = enrollment_status
            await db.flush()
            return existing.id, "Enrollment"

        new_enrollment = Enrollment(
            university_id=university_id,
            course_offering_id=course_offering_id,
            student_id=student_id,
            status=enrollment_status,
        )
        db.add(new_enrollment)
        await db.flush()
        return new_enrollment.id, "Enrollment"
