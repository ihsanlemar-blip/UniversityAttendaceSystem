"""Academic calendar service managing years, semesters, intervals, and active periods."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.calendar.schemas import (
    AcademicYearCreateRequest,
    AcademicYearDetailResponse,
    AcademicYearResponse,
    AcademicYearUpdateRequest,
    SemesterCreateRequest,
    SemesterResponse,
    SemesterUpdateRequest,
)
from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.core.constants import RecordStatus
from backend.app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from backend.app.models.academic_year import AcademicYear
from backend.app.models.semester import Semester


class AcademicCalendarService:
    """Service handling academic calendar periods, date bounds, and activation."""

    # -------------------------------------------------------------------------
    # Academic Years
    # -------------------------------------------------------------------------

    @staticmethod
    async def create_academic_year(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: AcademicYearCreateRequest,
    ) -> AcademicYear:
        """Create a new academic year with date validation and active status resolution."""
        if payload.start_date >= payload.end_date:
            raise ValidationException(
                "start_date must be strictly before end_date.",
                details={"start_date": str(payload.start_date), "end_date": str(payload.end_date)},
            )

        # Unique code check
        stmt = select(AcademicYear).where(
            AcademicYear.university_id == university_id,
            AcademicYear.code == payload.code,
        )
        if (await db.execute(stmt)).scalar_one_or_none():
            raise ConflictException(
                f"Academic year with code '{payload.code}' already exists in this university.",
                details={"code": payload.code},
            )

        # If marked as current, deactivate others first
        if payload.is_current:
            await db.execute(
                update(AcademicYear)
                .where(AcademicYear.university_id == university_id)
                .values(is_current=False)
            )

        year = AcademicYear(
            university_id=university_id,
            name=payload.name,
            code=payload.code,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_current=payload.is_current,
            status=RecordStatus.ACTIVE.value,
        )
        db.add(year)
        await db.commit()
        await db.refresh(year)
        return year

    @staticmethod
    async def get_academic_year_by_id(
        db: AsyncSession,
        university_id: uuid.UUID,
        year_id: uuid.UUID,
    ) -> AcademicYearDetailResponse:
        """Retrieve academic year and its nested semesters."""
        year = await db.get(AcademicYear, year_id)
        if not year or year.university_id != university_id:
            raise NotFoundException("AcademicYear", year_id)

        semesters_stmt = (
            select(Semester)
            .where(Semester.academic_year_id == year_id)
            .order_by(Semester.sequence_order.asc(), Semester.start_date.asc())
        )
        semesters = (await db.execute(semesters_stmt)).scalars().all()

        return AcademicYearDetailResponse(
            id=year.id,
            university_id=year.university_id,
            name=year.name,
            code=year.code,
            start_date=year.start_date,
            end_date=year.end_date,
            is_current=year.is_current,
            status=year.status,
            created_at=year.created_at,
            updated_at=year.updated_at,
            semesters=[SemesterResponse.model_validate(s) for s in semesters],
        )

    @staticmethod
    async def get_current_academic_year(
        db: AsyncSession,
        university_id: uuid.UUID,
    ) -> AcademicYear | None:
        """Retrieve the currently designated active academic year."""
        stmt = select(AcademicYear).where(
            AcademicYear.university_id == university_id,
            AcademicYear.is_current.is_(True),
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_academic_years(
        db: AsyncSession,
        university_id: uuid.UUID,
        page_params: PaginationParams,
        status: str | None = None,
        is_current: bool | None = None,
    ) -> PaginatedResponse[AcademicYearResponse]:
        """List academic years matching query filters."""
        query = select(AcademicYear).where(AcademicYear.university_id == university_id)

        if status:
            query = query.where(AcademicYear.status == status)
        if is_current is not None:
            query = query.where(AcademicYear.is_current == is_current)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar_one() or 0

        query = (
            query.order_by(AcademicYear.start_date.desc(), AcademicYear.name.asc())
            .offset(page_params.offset)
            .limit(page_params.page_size)
        )
        res = await db.execute(query)
        years = res.scalars().all()

        items = [AcademicYearResponse.model_validate(y) for y in years]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    @staticmethod
    async def update_academic_year(
        db: AsyncSession,
        university_id: uuid.UUID,
        year_id: uuid.UUID,
        payload: AcademicYearUpdateRequest,
    ) -> AcademicYear:
        """Update academic year fields and ensure semester date bounds consistency."""
        year = await db.get(AcademicYear, year_id)
        if not year or year.university_id != university_id:
            raise NotFoundException("AcademicYear", year_id)

        target_start = payload.start_date or year.start_date
        target_end = payload.end_date or year.end_date

        if target_start >= target_end:
            raise ValidationException("start_date must be strictly before end_date.")

        # Ensure existing semesters remain within the updated dates
        semesters_stmt = select(Semester).where(Semester.academic_year_id == year_id)
        semesters = (await db.execute(semesters_stmt)).scalars().all()
        for sem in semesters:
            if sem.start_date < target_start or sem.end_date > target_end:
                raise ValidationException(
                    f"Updated year dates ({target_start}..{target_end}) would invalidate "
                    f"existing semester '{sem.name}' dates ({sem.start_date}..{sem.end_date}).",
                    details={"conflicting_semester_id": str(sem.id)},
                )

        if payload.code is not None and payload.code != year.code:
            stmt = select(AcademicYear).where(
                AcademicYear.university_id == university_id,
                AcademicYear.code == payload.code,
                AcademicYear.id != year_id,
            )
            if (await db.execute(stmt)).scalar_one_or_none():
                raise ConflictException(
                    f"Academic year with code '{payload.code}' already exists in this university.",
                    details={"code": payload.code},
                )
            year.code = payload.code

        if payload.name is not None:
            year.name = payload.name
        year.start_date = target_start
        year.end_date = target_end

        await db.commit()
        await db.refresh(year)
        return year

    @staticmethod
    async def set_current_academic_year(
        db: AsyncSession,
        university_id: uuid.UUID,
        year_id: uuid.UUID,
    ) -> AcademicYear:
        """Atomically set specified academic year as current, unsetting others."""
        year = await db.get(AcademicYear, year_id)
        if not year or year.university_id != university_id:
            raise NotFoundException("AcademicYear", year_id)

        # Unset current on all years in university
        await db.execute(
            update(AcademicYear)
            .where(AcademicYear.university_id == university_id)
            .values(is_current=False)
        )
        year.is_current = True
        await db.commit()
        await db.refresh(year)
        return year

    # -------------------------------------------------------------------------
    # Semesters
    # -------------------------------------------------------------------------

    @staticmethod
    async def create_semester(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: SemesterCreateRequest,
    ) -> Semester:
        """Create semester ensuring enclosure within parent academic year date range."""
        if payload.start_date >= payload.end_date:
            raise ValidationException(
                "start_date must be strictly before end_date.",
                details={"start_date": str(payload.start_date), "end_date": str(payload.end_date)},
            )

        year = await db.get(AcademicYear, payload.academic_year_id)
        if not year or year.university_id != university_id:
            raise NotFoundException("AcademicYear", payload.academic_year_id)

        # Date enclosure validation
        if payload.start_date < year.start_date or payload.end_date > year.end_date:
            raise ValidationException(
                f"Semester dates ({payload.start_date} to {payload.end_date}) must fall within "
                f"parent academic year bounds ({year.start_date} to {year.end_date}).",
                details={
                    "semester_start": str(payload.start_date),
                    "semester_end": str(payload.end_date),
                    "academic_year_start": str(year.start_date),
                    "academic_year_end": str(year.end_date),
                },
            )

        # Unique code check within academic year
        stmt = select(Semester).where(
            Semester.academic_year_id == payload.academic_year_id,
            Semester.code == payload.code,
        )
        if (await db.execute(stmt)).scalar_one_or_none():
            raise ConflictException(
                f"Semester with code '{payload.code}' already exists in this academic year.",
                details={"code": payload.code},
            )

        # If marked as current, unset current on other semesters in university
        if payload.is_current:
            await db.execute(
                update(Semester)
                .where(Semester.university_id == university_id)
                .values(is_current=False)
            )

        semester = Semester(
            university_id=university_id,
            academic_year_id=payload.academic_year_id,
            name=payload.name,
            code=payload.code,
            sequence_order=payload.sequence_order,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_current=payload.is_current,
            status=RecordStatus.ACTIVE.value,
        )
        db.add(semester)
        await db.commit()
        await db.refresh(semester)
        return semester

    @staticmethod
    async def get_semester_by_id(
        db: AsyncSession,
        university_id: uuid.UUID,
        semester_id: uuid.UUID,
    ) -> Semester:
        """Retrieve semester by identifier."""
        semester = await db.get(Semester, semester_id)
        if not semester or semester.university_id != university_id:
            raise NotFoundException("Semester", semester_id)
        return semester

    @staticmethod
    async def get_current_semester(
        db: AsyncSession,
        university_id: uuid.UUID,
    ) -> Semester | None:
        """Retrieve the currently designated active semester."""
        stmt = select(Semester).where(
            Semester.university_id == university_id,
            Semester.is_current.is_(True),
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_semesters(
        db: AsyncSession,
        university_id: uuid.UUID,
        page_params: PaginationParams,
        academic_year_id: uuid.UUID | None = None,
        status: str | None = None,
        is_current: bool | None = None,
    ) -> PaginatedResponse[SemesterResponse]:
        """List semesters matching query filters."""
        query = select(Semester).where(Semester.university_id == university_id)

        if academic_year_id:
            query = query.where(Semester.academic_year_id == academic_year_id)
        if status:
            query = query.where(Semester.status == status)
        if is_current is not None:
            query = query.where(Semester.is_current == is_current)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar_one() or 0

        query = (
            query.order_by(Semester.start_date.desc(), Semester.sequence_order.asc())
            .offset(page_params.offset)
            .limit(page_params.page_size)
        )
        res = await db.execute(query)
        semesters = res.scalars().all()

        items = [SemesterResponse.model_validate(s) for s in semesters]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    @staticmethod
    async def update_semester(
        db: AsyncSession,
        university_id: uuid.UUID,
        semester_id: uuid.UUID,
        payload: SemesterUpdateRequest,
    ) -> Semester:
        """Update semester attributes with date bounds validation."""
        semester = await db.get(Semester, semester_id)
        if not semester or semester.university_id != university_id:
            raise NotFoundException("Semester", semester_id)

        target_start = payload.start_date or semester.start_date
        target_end = payload.end_date or semester.end_date

        if target_start >= target_end:
            raise ValidationException("start_date must be strictly before end_date.")

        # Check date enclosure against parent academic year
        year = await db.get(AcademicYear, semester.academic_year_id)
        if year:
            if target_start < year.start_date or target_end > year.end_date:
                raise ValidationException(
                    f"Semester dates ({target_start} to {target_end}) must fall within "
                    f"parent academic year bounds ({year.start_date} to {year.end_date}).",
                )

        if payload.code is not None and payload.code != semester.code:
            stmt = select(Semester).where(
                Semester.academic_year_id == semester.academic_year_id,
                Semester.code == payload.code,
                Semester.id != semester_id,
            )
            if (await db.execute(stmt)).scalar_one_or_none():
                raise ConflictException(
                    f"Semester with code '{payload.code}' already exists in this academic year.",
                    details={"code": payload.code},
                )
            semester.code = payload.code

        if payload.name is not None:
            semester.name = payload.name
        if payload.sequence_order is not None:
            semester.sequence_order = payload.sequence_order

        semester.start_date = target_start
        semester.end_date = target_end

        await db.commit()
        await db.refresh(semester)
        return semester

    @staticmethod
    async def set_current_semester(
        db: AsyncSession,
        university_id: uuid.UUID,
        semester_id: uuid.UUID,
    ) -> Semester:
        """Atomically set specified semester as current, unsetting others."""
        semester = await db.get(Semester, semester_id)
        if not semester or semester.university_id != university_id:
            raise NotFoundException("Semester", semester_id)

        # Unset current on all semesters in university
        await db.execute(
            update(Semester).where(Semester.university_id == university_id).values(is_current=False)
        )
        semester.is_current = True
        await db.commit()
        await db.refresh(semester)
        return semester
