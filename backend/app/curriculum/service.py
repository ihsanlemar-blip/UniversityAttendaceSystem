"""Curriculum service managing course catalog and student section cohorts."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.core.constants import RecordStatus
from backend.app.core.exceptions import ConflictException, NotFoundException, ValidationException
from backend.app.curriculum.schemas import (
    CourseCreateRequest,
    CourseDetailResponse,
    CourseResponse,
    CourseUpdateRequest,
    SectionCreateRequest,
    SectionDetailResponse,
    SectionResponse,
    SectionUpdateRequest,
)
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.course import Course
from backend.app.models.course_offering import CourseOffering
from backend.app.models.section import Section
from backend.app.models.semester import Semester


class CurriculumService:
    """Service handling Course catalog and Section cohort business logic."""

    # ==========================================
    # Courses
    # ==========================================

    @staticmethod
    async def create_course(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: CourseCreateRequest,
    ) -> Course:
        """Create a new course catalog item with code uniqueness check."""
        # 1. Check code uniqueness within university
        stmt = select(Course).where(
            Course.university_id == university_id,
            func.lower(Course.code) == payload.code.lower(),
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ConflictException(
                f"Course with code '{payload.code}' already exists in this university.",
                details={"code": payload.code},
            )

        # 2. Validate academic unit if provided
        if payload.academic_unit_id is not None:
            unit = await db.get(AcademicUnit, payload.academic_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university.",
                    details={"academic_unit_id": str(payload.academic_unit_id)},
                )
            if unit.status != RecordStatus.ACTIVE.value:
                raise ValidationException(
                    "Cannot assign course to an inactive or archived academic unit.",
                    details={"academic_unit_id": str(payload.academic_unit_id)},
                )

        course = Course(
            university_id=university_id,
            academic_unit_id=payload.academic_unit_id,
            code=payload.code.strip(),
            name=payload.name.strip(),
            credit_hours=payload.credit_hours,
            description=payload.description,
            status=RecordStatus.ACTIVE.value,
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course

    @staticmethod
    async def get_course(
        db: AsyncSession,
        university_id: uuid.UUID,
        course_id: uuid.UUID,
    ) -> CourseDetailResponse:
        """Retrieve a course by ID with academic unit details."""
        course = await db.get(Course, course_id)
        if not course or course.university_id != university_id:
            raise NotFoundException("Course", course_id)

        unit_name = None
        if course.academic_unit_id:
            unit = await db.get(AcademicUnit, course.academic_unit_id)
            unit_name = unit.name if unit else None

        res = CourseDetailResponse.model_validate(course)
        res.academic_unit_name = unit_name
        return res

    @staticmethod
    async def list_courses(
        db: AsyncSession,
        university_id: uuid.UUID,
        pagination: PaginationParams,
        academic_unit_id: uuid.UUID | None = None,
        accessible_unit_ids: set[uuid.UUID] | None = None,
        status: RecordStatus | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[CourseResponse]:
        """List courses with pagination, search, and scoped filtering."""
        query = select(Course).where(Course.university_id == university_id)

        # Scoped access restriction
        if accessible_unit_ids is not None:
            if not accessible_unit_ids:
                return PaginatedResponse.create(
                    items=[],
                    total=0,
                    page=pagination.page,
                    page_size=pagination.page_size,
                )
            query = query.where(Course.academic_unit_id.in_(accessible_unit_ids))

        if academic_unit_id is not None:
            query = query.where(Course.academic_unit_id == academic_unit_id)

        if status is not None:
            query = query.where(Course.status == status.value)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Course.code.ilike(search_pattern),
                    Course.name.ilike(search_pattern),
                )
            )

        # Total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Paginated fetch
        items_stmt = (
            query.order_by(Course.code.asc()).offset(pagination.offset).limit(pagination.page_size)
        )
        courses = (await db.execute(items_stmt)).scalars().all()

        return PaginatedResponse.create(
            items=[CourseResponse.model_validate(c) for c in courses],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def update_course(
        db: AsyncSession,
        university_id: uuid.UUID,
        course_id: uuid.UUID,
        payload: CourseUpdateRequest,
    ) -> Course:
        """Update an existing course catalog record."""
        course = await db.get(Course, course_id)
        if not course or course.university_id != university_id:
            raise NotFoundException("Course", course_id)

        if payload.academic_unit_id is not None:
            unit = await db.get(AcademicUnit, payload.academic_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university.",
                    details={"academic_unit_id": str(payload.academic_unit_id)},
                )
            course.academic_unit_id = payload.academic_unit_id

        if payload.name is not None:
            course.name = payload.name.strip()
        if payload.credit_hours is not None:
            course.credit_hours = payload.credit_hours
        if payload.description is not None:
            course.description = payload.description
        if payload.status is not None:
            course.status = payload.status.value

        await db.commit()
        await db.refresh(course)
        return course

    @staticmethod
    async def delete_course(
        db: AsyncSession,
        university_id: uuid.UUID,
        course_id: uuid.UUID,
    ) -> None:
        """Archive or delete a course if no active offerings exist."""
        course = await db.get(Course, course_id)
        if not course or course.university_id != university_id:
            raise NotFoundException("Course", course_id)

        # Check for existing offerings
        stmt = (
            select(func.count())
            .select_from(CourseOffering)
            .where(CourseOffering.course_id == course_id)
        )
        offerings_count = (await db.execute(stmt)).scalar() or 0
        if offerings_count > 0:
            raise ConflictException(
                f"Cannot delete course '{course.code}' because it has "
                f"{offerings_count} course offering(s).",
                details={"course_id": str(course_id), "offerings_count": offerings_count},
            )

        await db.delete(course)
        await db.commit()

    # ==========================================
    # Sections
    # ==========================================

    @staticmethod
    async def create_section(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: SectionCreateRequest,
    ) -> Section:
        """Create a student section cohort with semester uniqueness check."""
        # 1. Uniqueness check within semester
        stmt = select(Section).where(
            Section.university_id == university_id,
            Section.semester_id == payload.semester_id,
            func.lower(Section.code) == payload.code.lower(),
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ConflictException(
                f"Section with code '{payload.code}' already exists for this semester.",
                details={"code": payload.code, "semester_id": str(payload.semester_id)},
            )

        # 2. Validate academic unit if provided
        if payload.academic_unit_id is not None:
            unit = await db.get(AcademicUnit, payload.academic_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university.",
                    details={"academic_unit_id": str(payload.academic_unit_id)},
                )

        # 3. Validate semester if provided
        if payload.semester_id is not None:
            sem = await db.get(Semester, payload.semester_id)
            if not sem or sem.university_id != university_id:
                raise ValidationException(
                    "Specified semester does not exist in this university.",
                    details={"semester_id": str(payload.semester_id)},
                )

        section = Section(
            university_id=university_id,
            academic_unit_id=payload.academic_unit_id,
            semester_id=payload.semester_id,
            code=payload.code.strip(),
            name=payload.name.strip(),
            status=RecordStatus.ACTIVE.value,
        )
        db.add(section)
        await db.commit()
        await db.refresh(section)
        return section

    @staticmethod
    async def get_section(
        db: AsyncSession,
        university_id: uuid.UUID,
        section_id: uuid.UUID,
    ) -> SectionDetailResponse:
        """Retrieve a section by ID with related entity names."""
        section = await db.get(Section, section_id)
        if not section or section.university_id != university_id:
            raise NotFoundException("Section", section_id)

        unit_name = None
        if section.academic_unit_id:
            unit = await db.get(AcademicUnit, section.academic_unit_id)
            unit_name = unit.name if unit else None

        sem_name = None
        if section.semester_id:
            sem = await db.get(Semester, section.semester_id)
            sem_name = sem.name if sem else None

        res = SectionDetailResponse.model_validate(section)
        res.academic_unit_name = unit_name
        res.semester_name = sem_name
        return res

    @staticmethod
    async def list_sections(
        db: AsyncSession,
        university_id: uuid.UUID,
        pagination: PaginationParams,
        semester_id: uuid.UUID | None = None,
        academic_unit_id: uuid.UUID | None = None,
        accessible_unit_ids: set[uuid.UUID] | None = None,
        status: RecordStatus | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[SectionResponse]:
        """List sections with pagination, semester, and unit filtering."""
        query = select(Section).where(Section.university_id == university_id)

        if accessible_unit_ids is not None:
            if not accessible_unit_ids:
                return PaginatedResponse.create(
                    items=[],
                    total=0,
                    page=pagination.page,
                    page_size=pagination.page_size,
                )
            query = query.where(Section.academic_unit_id.in_(accessible_unit_ids))

        if semester_id is not None:
            query = query.where(Section.semester_id == semester_id)

        if academic_unit_id is not None:
            query = query.where(Section.academic_unit_id == academic_unit_id)

        if status is not None:
            query = query.where(Section.status == status.value)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Section.code.ilike(search_pattern),
                    Section.name.ilike(search_pattern),
                )
            )

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            query.order_by(Section.code.asc()).offset(pagination.offset).limit(pagination.page_size)
        )
        sections = (await db.execute(items_stmt)).scalars().all()

        return PaginatedResponse.create(
            items=[SectionResponse.model_validate(s) for s in sections],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def update_section(
        db: AsyncSession,
        university_id: uuid.UUID,
        section_id: uuid.UUID,
        payload: SectionUpdateRequest,
    ) -> Section:
        """Update an existing section cohort."""
        section = await db.get(Section, section_id)
        if not section or section.university_id != university_id:
            raise NotFoundException("Section", section_id)

        if payload.academic_unit_id is not None:
            unit = await db.get(AcademicUnit, payload.academic_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university.",
                    details={"academic_unit_id": str(payload.academic_unit_id)},
                )
            section.academic_unit_id = payload.academic_unit_id

        if payload.semester_id is not None:
            sem = await db.get(Semester, payload.semester_id)
            if not sem or sem.university_id != university_id:
                raise ValidationException(
                    "Specified semester does not exist in this university.",
                    details={"semester_id": str(payload.semester_id)},
                )
            section.semester_id = payload.semester_id

        if payload.name is not None:
            section.name = payload.name.strip()
        if payload.status is not None:
            section.status = payload.status.value

        await db.commit()
        await db.refresh(section)
        return section
