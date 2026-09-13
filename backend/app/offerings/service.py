"""Offering and roster service for semester offerings, instructors, and enrollments."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.common.types import utc_now
from backend.app.core.constants import (
    EnrollmentStatus,
    LecturerStatus,
    OfferingStatus,
    RecordStatus,
    StudentStatus,
)
from backend.app.core.exceptions import ConflictException, NotFoundException, ValidationException
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.course import Course
from backend.app.models.course_offering import CourseOffering
from backend.app.models.enrollment import Enrollment
from backend.app.models.lecturer import Lecturer
from backend.app.models.lecturer_assignment import LecturerAssignment
from backend.app.models.section import Section
from backend.app.models.semester import Semester
from backend.app.models.student import Student
from backend.app.models.user import User
from backend.app.offerings.schemas import (
    BatchEnrollmentRequest,
    CourseOfferingCreateRequest,
    CourseOfferingDetailResponse,
    CourseOfferingResponse,
    CourseOfferingUpdateRequest,
    LecturerAssignmentCreateRequest,
    LecturerAssignmentResponse,
    RosterItemResponse,
    StudentEnrollmentDetailResponse,
)


class OfferingService:
    """Service handling Course Offering scheduling, instructor linking, and student enrollments."""

    # ==========================================
    # Course Offerings
    # ==========================================

    @staticmethod
    async def create_offering(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: CourseOfferingCreateRequest,
    ) -> CourseOffering:
        """Schedule a course offering instance coupling Course + Semester + optional Section."""
        # 1. Validate course exists in university
        course = await db.get(Course, payload.course_id)
        if not course or course.university_id != university_id:
            raise NotFoundException("Course", payload.course_id)

        # 2. Validate semester exists in university
        semester = await db.get(Semester, payload.semester_id)
        if not semester or semester.university_id != university_id:
            raise NotFoundException("Semester", payload.semester_id)

        # 3. Validate section if provided
        if payload.section_id is not None:
            section = await db.get(Section, payload.section_id)
            if not section or section.university_id != university_id:
                raise NotFoundException("Section", payload.section_id)
            if section.semester_id is not None and section.semester_id != payload.semester_id:
                raise ValidationException(
                    "Specified section belongs to a different semester calendar session.",
                    details={
                        "section_semester_id": str(section.semester_id),
                        "target_semester_id": str(payload.semester_id),
                    },
                )

        # 4. Resolve academic unit (inherited from course if omitted)
        resolved_unit_id = payload.academic_unit_id or course.academic_unit_id
        if resolved_unit_id is not None:
            unit = await db.get(AcademicUnit, resolved_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university."
                )

        # 5. Check duplicate offering
        stmt = select(CourseOffering).where(
            CourseOffering.university_id == university_id,
            CourseOffering.course_id == payload.course_id,
            CourseOffering.semester_id == payload.semester_id,
        )
        if payload.section_id is not None:
            stmt = stmt.where(CourseOffering.section_id == payload.section_id)
        else:
            stmt = stmt.where(CourseOffering.section_id.is_(None))

        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ConflictException(
                "A course offering for this course, semester, and section already exists.",
                details={
                    "course_id": str(payload.course_id),
                    "semester_id": str(payload.semester_id),
                    "section_id": str(payload.section_id) if payload.section_id else None,
                },
            )

        offering = CourseOffering(
            university_id=university_id,
            course_id=payload.course_id,
            semester_id=payload.semester_id,
            section_id=payload.section_id,
            academic_unit_id=resolved_unit_id,
            status=OfferingStatus.ACTIVE.value,
        )
        db.add(offering)
        await db.commit()
        await db.refresh(offering)
        return offering

    @staticmethod
    async def get_offering(
        db: AsyncSession,
        university_id: uuid.UUID,
        offering_id: uuid.UUID,
    ) -> CourseOfferingDetailResponse:
        """Retrieve detailed course offering including catalog and instructor info."""
        offering = await db.get(CourseOffering, offering_id)
        if not offering or offering.university_id != university_id:
            raise NotFoundException("CourseOffering", offering_id)

        course = await db.get(Course, offering.course_id)
        semester = await db.get(Semester, offering.semester_id)
        section = await db.get(Section, offering.section_id) if offering.section_id else None

        # Fetch assigned lecturers
        stmt = (
            select(LecturerAssignment, Lecturer, User)
            .join(Lecturer, Lecturer.id == LecturerAssignment.lecturer_id)
            .join(User, User.id == Lecturer.user_id)
            .where(
                LecturerAssignment.course_offering_id == offering_id,
                LecturerAssignment.status == RecordStatus.ACTIVE.value,
            )
        )
        assign_rows = (await db.execute(stmt)).all()
        lecturer_dtos: list[LecturerAssignmentResponse] = []
        for la, lect, u in assign_rows:
            dto = LecturerAssignmentResponse.model_validate(la)
            dto.lecturer_name = u.username
            dto.employee_code = lect.employee_code
            lecturer_dtos.append(dto)

        # Count active enrolled students
        enr_stmt = (
            select(func.count())
            .select_from(Enrollment)
            .where(
                Enrollment.course_offering_id == offering_id,
                Enrollment.status == EnrollmentStatus.ACTIVE.value,
            )
        )
        enrolled_count = (await db.execute(enr_stmt)).scalar() or 0

        res = CourseOfferingDetailResponse.model_validate(offering)
        res.course_code = course.code if course else None
        res.course_name = course.name if course else None
        res.semester_name = semester.name if semester else None
        res.section_code = section.code if section else None
        res.section_name = section.name if section else None
        res.assigned_lecturers = lecturer_dtos
        res.enrolled_count = enrolled_count
        return res

    @staticmethod
    async def list_offerings(
        db: AsyncSession,
        university_id: uuid.UUID,
        pagination: PaginationParams,
        semester_id: uuid.UUID | None = None,
        course_id: uuid.UUID | None = None,
        academic_unit_id: uuid.UUID | None = None,
        lecturer_id: uuid.UUID | None = None,
        accessible_unit_ids: set[uuid.UUID] | None = None,
        status: OfferingStatus | None = None,
    ) -> PaginatedResponse[CourseOfferingResponse]:
        """List course offerings with pagination and multi-parameter filtering."""
        query = select(CourseOffering).where(CourseOffering.university_id == university_id)

        if accessible_unit_ids is not None:
            if not accessible_unit_ids:
                return PaginatedResponse.create(
                    items=[],
                    total=0,
                    page=pagination.page,
                    page_size=pagination.page_size,
                )
            query = query.where(CourseOffering.academic_unit_id.in_(accessible_unit_ids))

        if semester_id is not None:
            query = query.where(CourseOffering.semester_id == semester_id)

        if course_id is not None:
            query = query.where(CourseOffering.course_id == course_id)

        if academic_unit_id is not None:
            query = query.where(CourseOffering.academic_unit_id == academic_unit_id)

        if lecturer_id is not None:
            query = query.join(
                LecturerAssignment,
                LecturerAssignment.course_offering_id == CourseOffering.id,
            ).where(
                LecturerAssignment.lecturer_id == lecturer_id,
                LecturerAssignment.status == RecordStatus.ACTIVE.value,
            )

        if status is not None:
            query = query.where(CourseOffering.status == status.value)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            query.order_by(CourseOffering.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        offerings = (await db.execute(items_stmt)).scalars().all()

        return PaginatedResponse.create(
            items=[CourseOfferingResponse.model_validate(o) for o in offerings],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def update_offering(
        db: AsyncSession,
        university_id: uuid.UUID,
        offering_id: uuid.UUID,
        payload: CourseOfferingUpdateRequest,
    ) -> CourseOffering:
        """Update offering attributes."""
        offering = await db.get(CourseOffering, offering_id)
        if not offering or offering.university_id != university_id:
            raise NotFoundException("CourseOffering", offering_id)

        if payload.academic_unit_id is not None:
            unit = await db.get(AcademicUnit, payload.academic_unit_id)
            if not unit or unit.university_id != university_id:
                raise ValidationException(
                    "Specified academic unit does not exist in this university."
                )
            offering.academic_unit_id = payload.academic_unit_id

        if payload.section_id is not None:
            sec = await db.get(Section, payload.section_id)
            if not sec or sec.university_id != university_id:
                raise ValidationException("Specified section does not exist in this university.")
            offering.section_id = payload.section_id

        if payload.status is not None:
            offering.status = payload.status.value

        await db.commit()
        await db.refresh(offering)
        return offering

    # ==========================================
    # Lecturer Assignments
    # ==========================================

    @staticmethod
    async def assign_lecturer(
        db: AsyncSession,
        university_id: uuid.UUID,
        offering_id: uuid.UUID,
        payload: LecturerAssignmentCreateRequest,
    ) -> LecturerAssignment:
        """Assign an instructor to an offering, enforcing single primary instructor constraint."""
        # 1. Validate offering
        offering = await db.get(CourseOffering, offering_id)
        if not offering or offering.university_id != university_id:
            raise NotFoundException("CourseOffering", offering_id)

        # 2. Validate lecturer
        lecturer = await db.get(Lecturer, payload.lecturer_id)
        if not lecturer or lecturer.university_id != university_id:
            raise NotFoundException("Lecturer", payload.lecturer_id)
        if lecturer.status != LecturerStatus.ACTIVE.value:
            raise ValidationException("Cannot assign an inactive or on-leave lecturer.")

        # 3. If primary, enforce single primary instructor per offering
        if payload.is_primary:
            stmt = select(LecturerAssignment).where(
                LecturerAssignment.course_offering_id == offering_id,
                LecturerAssignment.is_primary.is_(True),
                LecturerAssignment.status == RecordStatus.ACTIVE.value,
            )
            existing_primary = (await db.execute(stmt)).scalar_one_or_none()
            if existing_primary and existing_primary.lecturer_id != payload.lecturer_id:
                raise ConflictException(
                    "This course offering already has an active primary instructor.",
                    details={"existing_primary_lecturer_id": str(existing_primary.lecturer_id)},
                )

        # 4. Check if lecturer already assigned
        assign_stmt = select(LecturerAssignment).where(
            LecturerAssignment.course_offering_id == offering_id,
            LecturerAssignment.lecturer_id == payload.lecturer_id,
        )
        existing_assign = (await db.execute(assign_stmt)).scalar_one_or_none()
        if existing_assign:
            if existing_assign.status == RecordStatus.ACTIVE.value:
                raise ConflictException(
                    "This instructor is already assigned to this course offering."
                )
            # Reactivate
            existing_assign.status = RecordStatus.ACTIVE.value
            existing_assign.is_primary = payload.is_primary
            existing_assign.assignment_type = payload.assignment_type.value
            await db.commit()
            await db.refresh(existing_assign)
            return existing_assign

        assignment = LecturerAssignment(
            course_offering_id=offering_id,
            lecturer_id=payload.lecturer_id,
            is_primary=payload.is_primary,
            assignment_type=payload.assignment_type.value,
            status=RecordStatus.ACTIVE.value,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        return assignment

    @staticmethod
    async def remove_lecturer(
        db: AsyncSession,
        university_id: uuid.UUID,
        offering_id: uuid.UUID,
        lecturer_id: uuid.UUID,
    ) -> None:
        """Remove or deactivate an instructor assignment."""
        offering = await db.get(CourseOffering, offering_id)
        if not offering or offering.university_id != university_id:
            raise NotFoundException("CourseOffering", offering_id)

        stmt = select(LecturerAssignment).where(
            LecturerAssignment.course_offering_id == offering_id,
            LecturerAssignment.lecturer_id == lecturer_id,
        )
        assignment = (await db.execute(stmt)).scalar_one_or_none()
        if not assignment:
            raise NotFoundException("LecturerAssignment", lecturer_id)

        await db.delete(assignment)
        await db.commit()

    # ==========================================
    # Student Enrollments & Rosters
    # ==========================================

    @staticmethod
    async def enroll_student(
        db: AsyncSession,
        university_id: uuid.UUID,
        offering_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> Enrollment:
        """Enroll a student into a course offering with reactivation on previous drop."""
        # 1. Validate offering
        offering = await db.get(CourseOffering, offering_id)
        if not offering or offering.university_id != university_id:
            raise NotFoundException("CourseOffering", offering_id)

        # 2. Validate student
        student = await db.get(Student, student_id)
        if not student or student.university_id != university_id:
            raise NotFoundException("Student", student_id)
        if student.status != StudentStatus.ACTIVE.value:
            raise ValidationException("Cannot enroll an inactive or suspended student.")

        # 3. Check existing enrollment record
        stmt = select(Enrollment).where(
            Enrollment.course_offering_id == offering_id,
            Enrollment.student_id == student_id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            if existing.status == EnrollmentStatus.ACTIVE.value:
                raise ConflictException(
                    "Student is already actively enrolled in this course offering.",
                    details={"offering_id": str(offering_id), "student_id": str(student_id)},
                )
            # Reactivate previously dropped/withdrawn enrollment
            existing.status = EnrollmentStatus.ACTIVE.value
            existing.enrolled_at = utc_now()
            existing.dropped_at = None
            await db.commit()
            await db.refresh(existing)
            return existing

        enrollment = Enrollment(
            university_id=university_id,
            course_offering_id=offering_id,
            student_id=student_id,
            status=EnrollmentStatus.ACTIVE.value,
            enrolled_at=utc_now(),
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)
        return enrollment

    @staticmethod
    async def batch_enroll(
        db: AsyncSession,
        university_id: uuid.UUID,
        offering_id: uuid.UUID,
        payload: BatchEnrollmentRequest,
    ) -> list[Enrollment]:
        """Batch enroll multiple students into a course offering."""
        offering = await db.get(CourseOffering, offering_id)
        if not offering or offering.university_id != university_id:
            raise NotFoundException("CourseOffering", offering_id)

        enrollments: list[Enrollment] = []
        for sid in payload.student_ids:
            student = await db.get(Student, sid)
            if not student or student.university_id != university_id:
                continue

            stmt = select(Enrollment).where(
                Enrollment.course_offering_id == offering_id,
                Enrollment.student_id == sid,
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                if existing.status != EnrollmentStatus.ACTIVE.value:
                    existing.status = EnrollmentStatus.ACTIVE.value
                    existing.enrolled_at = utc_now()
                    existing.dropped_at = None
                    enrollments.append(existing)
            else:
                new_enr = Enrollment(
                    university_id=university_id,
                    course_offering_id=offering_id,
                    student_id=sid,
                    status=EnrollmentStatus.ACTIVE.value,
                    enrolled_at=utc_now(),
                )
                db.add(new_enr)
                enrollments.append(new_enr)

        await db.commit()
        for e in enrollments:
            await db.refresh(e)
        return enrollments

    @staticmethod
    async def drop_enrollment(
        db: AsyncSession,
        university_id: uuid.UUID,
        offering_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> Enrollment:
        """Drop a student's enrollment while preserving the record and audit history."""
        stmt = select(Enrollment).where(
            Enrollment.course_offering_id == offering_id,
            Enrollment.student_id == student_id,
            Enrollment.university_id == university_id,
        )
        enrollment = (await db.execute(stmt)).scalar_one_or_none()
        if not enrollment:
            raise NotFoundException("Enrollment", student_id)

        if enrollment.status == EnrollmentStatus.DROPPED.value:
            raise ConflictException("Student enrollment has already been dropped.")

        enrollment.status = EnrollmentStatus.DROPPED.value
        enrollment.dropped_at = utc_now()
        await db.commit()
        await db.refresh(enrollment)
        return enrollment

    @staticmethod
    async def get_roster(
        db: AsyncSession,
        university_id: uuid.UUID,
        offering_id: uuid.UUID,
        pagination: PaginationParams,
        status: EnrollmentStatus | None = None,
    ) -> PaginatedResponse[RosterItemResponse]:
        """Get paginated class roster of enrolled students."""
        offering = await db.get(CourseOffering, offering_id)
        if not offering or offering.university_id != university_id:
            raise NotFoundException("CourseOffering", offering_id)

        query = (
            select(Enrollment, Student, User)
            .join(Student, Student.id == Enrollment.student_id)
            .join(User, User.id == Student.user_id)
            .where(Enrollment.course_offering_id == offering_id)
        )

        if status is not None:
            query = query.where(Enrollment.status == status.value)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            query.order_by(Student.student_number.asc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        rows = (await db.execute(items_stmt)).all()

        roster_items: list[RosterItemResponse] = []
        for enr, stu, usr in rows:
            item = RosterItemResponse.model_validate(enr)
            item.student_number = stu.student_number
            item.student_name = usr.username
            item.email = usr.email
            roster_items.append(item)

        return PaginatedResponse.create(
            items=roster_items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def get_student_enrollments(
        db: AsyncSession,
        university_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> list[StudentEnrollmentDetailResponse]:
        """Fetch all course offering enrollments for a specific student."""
        stmt = (
            select(Enrollment, CourseOffering, Course, Semester, Section)
            .join(CourseOffering, CourseOffering.id == Enrollment.course_offering_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .join(Semester, Semester.id == CourseOffering.semester_id)
            .outerjoin(Section, Section.id == CourseOffering.section_id)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.university_id == university_id,
            )
            .order_by(Semester.start_date.desc(), Course.code.asc())
        )
        rows = (await db.execute(stmt)).all()

        results: list[StudentEnrollmentDetailResponse] = []
        for enr, off, crs, sem, sec in rows:
            results.append(
                StudentEnrollmentDetailResponse(
                    enrollment_id=enr.id,
                    course_offering_id=off.id,
                    course_code=crs.code,
                    course_name=crs.name,
                    semester_name=sem.name,
                    section_code=sec.code if sec else None,
                    status=enr.status,
                    enrolled_at=enr.enrolled_at,
                    dropped_at=enr.dropped_at,
                )
            )
        return results
