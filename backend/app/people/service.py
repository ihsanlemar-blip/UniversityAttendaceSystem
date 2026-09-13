"""People service managing Student and Lecturer academic profiles."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.core.constants import LecturerStatus, StudentStatus
from backend.app.core.exceptions import ConflictException, NotFoundException, ValidationException
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.lecturer import Lecturer
from backend.app.models.section import Section
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.people.schemas import (
    LecturerCreateRequest,
    LecturerDetailResponse,
    LecturerResponse,
    LecturerUpdateRequest,
    StudentCreateRequest,
    StudentDetailResponse,
    StudentResponse,
    StudentUpdateRequest,
)


class PeopleService:
    """Service handling Student and Lecturer profile lifecycle."""

    # ==========================================
    # Students
    # ==========================================

    @staticmethod
    async def create_student(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: StudentCreateRequest,
    ) -> Student:
        """Create a student academic profile linked 1-to-1 to a User account."""
        # 1. Verify user exists and belongs to same university
        user = await db.get(User, payload.user_id)
        if not user or user.university_id != university_id:
            raise NotFoundException("User", payload.user_id)

        # 2. Check user not already linked to another student profile
        stmt = select(Student).where(Student.user_id == payload.user_id)
        existing_student = (await db.execute(stmt)).scalar_one_or_none()
        if existing_student:
            raise ConflictException(
                "This user account is already linked to an existing student profile.",
                details={"user_id": str(payload.user_id)},
            )

        # 3. Check student_number uniqueness within university
        stmt = select(Student).where(
            Student.university_id == university_id,
            func.lower(Student.student_number) == payload.student_number.lower(),
        )
        existing_num = (await db.execute(stmt)).scalar_one_or_none()
        if existing_num:
            raise ConflictException(
                f"Student number '{payload.student_number}' already exists in this university.",
                details={"student_number": payload.student_number},
            )

        # 4. Validate academic unit if provided
        if payload.academic_unit_id is not None:
            unit = await db.get(AcademicUnit, payload.academic_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university.",
                    details={"academic_unit_id": str(payload.academic_unit_id)},
                )

        # 5. Validate section if provided
        if payload.section_id is not None:
            sec = await db.get(Section, payload.section_id)
            if not sec or sec.university_id != university_id:
                raise ValidationException(
                    "Specified section does not exist in this university.",
                    details={"section_id": str(payload.section_id)},
                )

        student = Student(
            user_id=payload.user_id,
            university_id=university_id,
            student_number=payload.student_number.strip(),
            academic_unit_id=payload.academic_unit_id,
            section_id=payload.section_id,
            admission_date=payload.admission_date,
            status=StudentStatus.ACTIVE.value,
        )
        db.add(student)
        await db.commit()
        await db.refresh(student)
        return student

    @staticmethod
    async def get_student(
        db: AsyncSession,
        university_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> StudentDetailResponse:
        """Get detailed student profile by ID."""
        student = await db.get(Student, student_id)
        if not student or student.university_id != university_id:
            raise NotFoundException("Student", student_id)

        user = await db.get(User, student.user_id)
        unit = (
            await db.get(AcademicUnit, student.academic_unit_id)
            if student.academic_unit_id
            else None
        )
        section = await db.get(Section, student.section_id) if student.section_id else None

        res = StudentDetailResponse.model_validate(student)
        res.username = user.username if user else None
        res.full_name = user.username if user else None
        res.email = user.email if user else None
        res.academic_unit_name = unit.name if unit else None
        res.section_name = section.name if section else None
        return res

    @staticmethod
    async def get_student_by_user_id(
        db: AsyncSession,
        university_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StudentDetailResponse:
        """Get student profile by linked User ID."""
        stmt = select(Student).where(
            Student.university_id == university_id,
            Student.user_id == user_id,
        )
        student = (await db.execute(stmt)).scalar_one_or_none()
        if not student:
            raise NotFoundException("Student", user_id)

        return await PeopleService.get_student(db, university_id, student.id)

    @staticmethod
    async def list_students(
        db: AsyncSession,
        university_id: uuid.UUID,
        pagination: PaginationParams,
        academic_unit_id: uuid.UUID | None = None,
        section_id: uuid.UUID | None = None,
        accessible_unit_ids: set[uuid.UUID] | None = None,
        status: StudentStatus | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[StudentResponse]:
        """List students with pagination, search, and scoped filtering."""
        query = select(Student).where(Student.university_id == university_id)

        if accessible_unit_ids is not None:
            if not accessible_unit_ids:
                return PaginatedResponse.create(
                    items=[],
                    total=0,
                    page=pagination.page,
                    page_size=pagination.page_size,
                )
            query = query.where(Student.academic_unit_id.in_(accessible_unit_ids))

        if academic_unit_id is not None:
            query = query.where(Student.academic_unit_id == academic_unit_id)

        if section_id is not None:
            query = query.where(Student.section_id == section_id)

        if status is not None:
            query = query.where(Student.status == status.value)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.join(User, User.id == Student.user_id).where(
                or_(
                    Student.student_number.ilike(search_pattern),
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            )

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            query.order_by(Student.student_number.asc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        students = (await db.execute(items_stmt)).scalars().all()

        return PaginatedResponse.create(
            items=[StudentResponse.model_validate(s) for s in students],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def update_student(
        db: AsyncSession,
        university_id: uuid.UUID,
        student_id: uuid.UUID,
        payload: StudentUpdateRequest,
    ) -> Student:
        """Update student profile attributes."""
        student = await db.get(Student, student_id)
        if not student or student.university_id != university_id:
            raise NotFoundException("Student", student_id)

        if payload.student_number is not None:
            stmt = select(Student).where(
                Student.university_id == university_id,
                Student.id != student_id,
                func.lower(Student.student_number) == payload.student_number.lower(),
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                raise ConflictException(
                    f"Student number '{payload.student_number}' is already "
                    "assigned to another student.",
                    details={"student_number": payload.student_number},
                )
            student.student_number = payload.student_number.strip()

        if payload.academic_unit_id is not None:
            unit = await db.get(AcademicUnit, payload.academic_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university.",
                    details={"academic_unit_id": str(payload.academic_unit_id)},
                )
            student.academic_unit_id = payload.academic_unit_id

        if payload.section_id is not None:
            sec = await db.get(Section, payload.section_id)
            if not sec or sec.university_id != university_id:
                raise ValidationException(
                    "Specified section does not exist in this university.",
                    details={"section_id": str(payload.section_id)},
                )
            student.section_id = payload.section_id

        if payload.admission_date is not None:
            student.admission_date = payload.admission_date

        if payload.status is not None:
            student.status = payload.status.value

        await db.commit()
        await db.refresh(student)
        return student

    # ==========================================
    # Lecturers
    # ==========================================

    @staticmethod
    async def create_lecturer(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: LecturerCreateRequest,
    ) -> Lecturer:
        """Create a lecturer academic profile linked 1-to-1 to a User account."""
        # 1. Verify user exists and belongs to same university
        user = await db.get(User, payload.user_id)
        if not user or user.university_id != university_id:
            raise NotFoundException("User", payload.user_id)

        # 2. Check user not already linked to another lecturer profile
        stmt = select(Lecturer).where(Lecturer.user_id == payload.user_id)
        existing_lecturer = (await db.execute(stmt)).scalar_one_or_none()
        if existing_lecturer:
            raise ConflictException(
                "This user account is already linked to an existing lecturer profile.",
                details={"user_id": str(payload.user_id)},
            )

        # 3. Check employee_code uniqueness within university
        stmt = select(Lecturer).where(
            Lecturer.university_id == university_id,
            func.lower(Lecturer.employee_code) == payload.employee_code.lower(),
        )
        existing_code = (await db.execute(stmt)).scalar_one_or_none()
        if existing_code:
            raise ConflictException(
                f"Employee code '{payload.employee_code}' already exists in this university.",
                details={"employee_code": payload.employee_code},
            )

        # 4. Validate academic unit if provided
        if payload.academic_unit_id is not None:
            unit = await db.get(AcademicUnit, payload.academic_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university.",
                    details={"academic_unit_id": str(payload.academic_unit_id)},
                )

        lecturer = Lecturer(
            user_id=payload.user_id,
            university_id=university_id,
            employee_code=payload.employee_code.strip(),
            academic_unit_id=payload.academic_unit_id,
            title=payload.title.strip() if payload.title else None,
            status=LecturerStatus.ACTIVE.value,
        )
        db.add(lecturer)
        await db.commit()
        await db.refresh(lecturer)
        return lecturer

    @staticmethod
    async def get_lecturer(
        db: AsyncSession,
        university_id: uuid.UUID,
        lecturer_id: uuid.UUID,
    ) -> LecturerDetailResponse:
        """Get detailed lecturer profile by ID."""
        lecturer = await db.get(Lecturer, lecturer_id)
        if not lecturer or lecturer.university_id != university_id:
            raise NotFoundException("Lecturer", lecturer_id)

        user = await db.get(User, lecturer.user_id)
        unit = (
            await db.get(AcademicUnit, lecturer.academic_unit_id)
            if lecturer.academic_unit_id
            else None
        )

        res = LecturerDetailResponse.model_validate(lecturer)
        res.username = user.username if user else None
        res.full_name = user.username if user else None
        res.email = user.email if user else None
        res.academic_unit_name = unit.name if unit else None
        return res

    @staticmethod
    async def get_lecturer_by_user_id(
        db: AsyncSession,
        university_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> LecturerDetailResponse:
        """Get lecturer profile by linked User ID."""
        stmt = select(Lecturer).where(
            Lecturer.university_id == university_id,
            Lecturer.user_id == user_id,
        )
        lecturer = (await db.execute(stmt)).scalar_one_or_none()
        if not lecturer:
            raise NotFoundException("Lecturer", user_id)

        return await PeopleService.get_lecturer(db, university_id, lecturer.id)

    @staticmethod
    async def list_lecturers(
        db: AsyncSession,
        university_id: uuid.UUID,
        pagination: PaginationParams,
        academic_unit_id: uuid.UUID | None = None,
        accessible_unit_ids: set[uuid.UUID] | None = None,
        status: LecturerStatus | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[LecturerResponse]:
        """List lecturers with pagination, search, and scoped filtering."""
        query = select(Lecturer).where(Lecturer.university_id == university_id)

        if accessible_unit_ids is not None:
            if not accessible_unit_ids:
                return PaginatedResponse.create(
                    items=[],
                    total=0,
                    page=pagination.page,
                    page_size=pagination.page_size,
                )
            query = query.where(Lecturer.academic_unit_id.in_(accessible_unit_ids))

        if academic_unit_id is not None:
            query = query.where(Lecturer.academic_unit_id == academic_unit_id)

        if status is not None:
            query = query.where(Lecturer.status == status.value)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.join(User, User.id == Lecturer.user_id).where(
                or_(
                    Lecturer.employee_code.ilike(search_pattern),
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            )

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            query.order_by(Lecturer.employee_code.asc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        lecturers = (await db.execute(items_stmt)).scalars().all()

        return PaginatedResponse.create(
            items=[LecturerResponse.model_validate(item) for item in lecturers],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def update_lecturer(
        db: AsyncSession,
        university_id: uuid.UUID,
        lecturer_id: uuid.UUID,
        payload: LecturerUpdateRequest,
    ) -> Lecturer:
        """Update lecturer profile attributes."""
        lecturer = await db.get(Lecturer, lecturer_id)
        if not lecturer or lecturer.university_id != university_id:
            raise NotFoundException("Lecturer", lecturer_id)

        if payload.employee_code is not None:
            stmt = select(Lecturer).where(
                Lecturer.university_id == university_id,
                Lecturer.id != lecturer_id,
                func.lower(Lecturer.employee_code) == payload.employee_code.lower(),
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                raise ConflictException(
                    f"Employee code '{payload.employee_code}' is already "
                    "assigned to another lecturer.",
                    details={"employee_code": payload.employee_code},
                )
            lecturer.employee_code = payload.employee_code.strip()

        if payload.academic_unit_id is not None:
            unit = await db.get(AcademicUnit, payload.academic_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university.",
                    details={"academic_unit_id": str(payload.academic_unit_id)},
                )
            lecturer.academic_unit_id = payload.academic_unit_id

        if payload.title is not None:
            lecturer.title = payload.title.strip()

        if payload.status is not None:
            lecturer.status = payload.status.value

        await db.commit()
        await db.refresh(lecturer)
        return lecturer
