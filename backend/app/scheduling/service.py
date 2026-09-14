"""Scheduling business logic: recurring timetables, conflict engine,
and ClassOccurrence generator.
"""

import datetime
import uuid
import zoneinfo

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.core.constants import (
    ClassOccurrenceStatus,
    EnrollmentStatus,
    OfferingStatus,
    RoomStatus,
    TimetableStatus,
)
from backend.app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from backend.app.core.logging import get_logger
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.course_offering import CourseOffering
from backend.app.models.enrollment import Enrollment
from backend.app.models.lecturer import Lecturer
from backend.app.models.lecturer_assignment import LecturerAssignment
from backend.app.models.room import Room
from backend.app.models.student import Student
from backend.app.models.timetable import Timetable
from backend.app.scheduling.schemas import (
    ClassOccurrenceDetailResponse,
    OccurrenceGenerationResponse,
    OccurrenceRescheduleRequest,
    TimetableCreateRequest,
    TimetableDetailResponse,
    TimetableUpdateRequest,
)

logger = get_logger(__name__)


# ==========================================
# Overlap Utility Functions
# ==========================================


def times_overlap(
    s1: datetime.time,
    e1: datetime.time,
    s2: datetime.time,
    e2: datetime.time,
) -> bool:
    """Return True if time intervals [s1, e1) and [s2, e2) strictly overlap.

    Adjacent time windows (e.g. 08:00–09:00 and 09:00–10:00) do NOT overlap.
    """
    return s1 < e2 and e1 > s2


def date_ranges_overlap(
    f1: datetime.date,
    t1: datetime.date,
    f2: datetime.date,
    t2: datetime.date,
) -> bool:
    """Return True if inclusive calendar date ranges [f1, t1] and [f2, t2] overlap."""
    return f1 <= t2 and t1 >= f2


class SchedulingService:
    """Service handling recurring timetable rules, conflict checks, and class occurrences."""

    # ==========================================
    # Conflict Detection Engine
    # ==========================================

    @staticmethod
    async def _resolve_effective_dates(
        db: AsyncSession,
        course_offering_id: uuid.UUID,
        eff_from: datetime.date | None,
        eff_to: datetime.date | None,
    ) -> tuple[datetime.date, datetime.date]:
        """Resolve effective date range clamped to offering's semester."""
        stmt = (
            select(CourseOffering)
            .options(selectinload(CourseOffering.semester))
            .where(CourseOffering.id == course_offering_id)
        )
        res = await db.execute(stmt)
        offering = res.scalar_one_or_none()
        if not offering or not offering.semester:
            raise NotFoundException("CourseOffering", course_offering_id)

        sem_start = offering.semester.start_date
        sem_end = offering.semester.end_date

        start_date = max(sem_start, eff_from) if eff_from else sem_start
        end_date = min(sem_end, eff_to) if eff_to else sem_end

        if start_date > end_date:
            raise ValidationException(
                "Effective date range falls outside the semester dates.",
                details={"semester_start": str(sem_start), "semester_end": str(sem_end)},
            )
        return start_date, end_date

    @staticmethod
    async def check_room_conflict(
        db: AsyncSession,
        university_id: uuid.UUID,
        room_id: uuid.UUID | None,
        weekday: int,
        start_time: datetime.time,
        end_time: datetime.time,
        eff_from: datetime.date,
        eff_to: datetime.date,
        exclude_timetable_id: uuid.UUID | None = None,
    ) -> None:
        """Verify no conflicting active timetable rule exists for the specified room."""
        if not room_id:
            return

        stmt = (
            select(Timetable)
            .options(selectinload(Timetable.course_offering).selectinload(CourseOffering.semester))
            .where(
                Timetable.university_id == university_id,
                Timetable.room_id == room_id,
                Timetable.weekday == weekday,
                Timetable.status == TimetableStatus.ACTIVE.value,
            )
        )
        if exclude_timetable_id:
            stmt = stmt.where(Timetable.id != exclude_timetable_id)

        res = await db.execute(stmt)
        existing_rules = res.scalars().all()

        for rule in existing_rules:
            r_sem = rule.course_offering.semester
            r_from = rule.effective_from or r_sem.start_date
            r_to = rule.effective_to or r_sem.end_date
            if date_ranges_overlap(eff_from, eff_to, r_from, r_to):
                if times_overlap(start_time, end_time, rule.start_time, rule.end_time):
                    raise ConflictException(
                        "Room is already scheduled for another class during this time window.",
                        code="ROOM_SCHEDULE_CONFLICT",
                        details={
                            "conflict_type": "ROOM_SCHEDULE_CONFLICT",
                            "room_id": str(room_id),
                            "weekday": weekday,
                            "conflicting_timetable_id": str(rule.id),
                            "start_time": str(rule.start_time),
                            "end_time": str(rule.end_time),
                        },
                    )

    @staticmethod
    async def check_lecturer_conflict(
        db: AsyncSession,
        university_id: uuid.UUID,
        lecturer_id: uuid.UUID | None,
        weekday: int,
        start_time: datetime.time,
        end_time: datetime.time,
        eff_from: datetime.date,
        eff_to: datetime.date,
        exclude_timetable_id: uuid.UUID | None = None,
    ) -> None:
        """Verify the instructor is not already booked for another overlapping class."""
        if not lecturer_id:
            return

        stmt = (
            select(Timetable)
            .options(selectinload(Timetable.course_offering).selectinload(CourseOffering.semester))
            .where(
                Timetable.university_id == university_id,
                Timetable.lecturer_id == lecturer_id,
                Timetable.weekday == weekday,
                Timetable.status == TimetableStatus.ACTIVE.value,
            )
        )
        if exclude_timetable_id:
            stmt = stmt.where(Timetable.id != exclude_timetable_id)

        res = await db.execute(stmt)
        existing_rules = res.scalars().all()

        for rule in existing_rules:
            r_sem = rule.course_offering.semester
            r_from = rule.effective_from or r_sem.start_date
            r_to = rule.effective_to or r_sem.end_date
            if date_ranges_overlap(eff_from, eff_to, r_from, r_to):
                if times_overlap(start_time, end_time, rule.start_time, rule.end_time):
                    raise ConflictException(
                        "Lecturer is already scheduled for another class during this time window.",
                        code="LECTURER_SCHEDULE_CONFLICT",
                        details={
                            "conflict_type": "LECTURER_SCHEDULE_CONFLICT",
                            "lecturer_id": str(lecturer_id),
                            "weekday": weekday,
                            "conflicting_timetable_id": str(rule.id),
                            "start_time": str(rule.start_time),
                            "end_time": str(rule.end_time),
                        },
                    )

    @staticmethod
    async def check_section_conflict(
        db: AsyncSession,
        university_id: uuid.UUID,
        section_id: uuid.UUID | None,
        weekday: int,
        start_time: datetime.time,
        end_time: datetime.time,
        eff_from: datetime.date,
        eff_to: datetime.date,
        exclude_timetable_id: uuid.UUID | None = None,
    ) -> None:
        """Verify the section cohort is not scheduled for another overlapping class."""
        if not section_id:
            return

        stmt = (
            select(Timetable)
            .join(CourseOffering, Timetable.course_offering_id == CourseOffering.id)
            .options(selectinload(Timetable.course_offering).selectinload(CourseOffering.semester))
            .where(
                Timetable.university_id == university_id,
                CourseOffering.section_id == section_id,
                Timetable.weekday == weekday,
                Timetable.status == TimetableStatus.ACTIVE.value,
            )
        )
        if exclude_timetable_id:
            stmt = stmt.where(Timetable.id != exclude_timetable_id)

        res = await db.execute(stmt)
        existing_rules = res.scalars().all()

        for rule in existing_rules:
            r_sem = rule.course_offering.semester
            r_from = rule.effective_from or r_sem.start_date
            r_to = rule.effective_to or r_sem.end_date
            if date_ranges_overlap(eff_from, eff_to, r_from, r_to):
                if times_overlap(start_time, end_time, rule.start_time, rule.end_time):
                    raise ConflictException(
                        "Section cohort is already scheduled for another class in this window.",
                        code="SECTION_SCHEDULE_CONFLICT",
                        details={
                            "conflict_type": "SECTION_SCHEDULE_CONFLICT",
                            "section_id": str(section_id),
                            "weekday": weekday,
                            "conflicting_timetable_id": str(rule.id),
                            "start_time": str(rule.start_time),
                            "end_time": str(rule.end_time),
                        },
                    )

    @staticmethod
    async def check_offering_self_conflict(
        db: AsyncSession,
        course_offering_id: uuid.UUID,
        weekday: int,
        start_time: datetime.time,
        end_time: datetime.time,
        eff_from: datetime.date,
        eff_to: datetime.date,
        exclude_timetable_id: uuid.UUID | None = None,
    ) -> None:
        """Verify the course offering does not have an overlapping slot on the same weekday."""
        stmt = (
            select(Timetable)
            .options(selectinload(Timetable.course_offering).selectinload(CourseOffering.semester))
            .where(
                Timetable.course_offering_id == course_offering_id,
                Timetable.weekday == weekday,
                Timetable.status == TimetableStatus.ACTIVE.value,
            )
        )
        if exclude_timetable_id:
            stmt = stmt.where(Timetable.id != exclude_timetable_id)

        res = await db.execute(stmt)
        existing_rules = res.scalars().all()

        for rule in existing_rules:
            r_sem = rule.course_offering.semester
            r_from = rule.effective_from or r_sem.start_date
            r_to = rule.effective_to or r_sem.end_date
            if date_ranges_overlap(eff_from, eff_to, r_from, r_to):
                if times_overlap(start_time, end_time, rule.start_time, rule.end_time):
                    raise ConflictException(
                        "Course offering already has an overlapping slot on this weekday.",
                        code="DUPLICATE_TIMETABLE_RULE",
                        details={
                            "conflict_type": "DUPLICATE_TIMETABLE_RULE",
                            "offering_id": str(course_offering_id),
                            "weekday": weekday,
                            "conflicting_timetable_id": str(rule.id),
                        },
                    )

    # ==========================================
    # Timetable Rule Management
    # ==========================================

    @staticmethod
    async def create_timetable_rule(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: TimetableCreateRequest,
    ) -> Timetable:
        """Create a recurring weekly timetable schedule rule with full conflict checking."""
        if payload.start_time >= payload.end_time:
            raise ValidationException(
                "Class start_time must be strictly before end_time.",
                details={"start_time": str(payload.start_time), "end_time": str(payload.end_time)},
            )

        # 1. Validate course offering
        offering_stmt = (
            select(CourseOffering)
            .options(
                selectinload(CourseOffering.semester),
                selectinload(CourseOffering.lecturer_assignments),
            )
            .where(
                CourseOffering.id == payload.course_offering_id,
                CourseOffering.university_id == university_id,
            )
        )
        o_res = await db.execute(offering_stmt)
        offering = o_res.scalar_one_or_none()
        if not offering:
            raise NotFoundException("CourseOffering", payload.course_offering_id)

        if offering.status != OfferingStatus.ACTIVE.value:
            raise ValidationException(
                "Cannot schedule a timetable for an inactive course offering."
            )

        # 2. Semester boundary validation
        sem = offering.semester
        if payload.effective_from and payload.effective_from < sem.start_date:
            raise ValidationException(
                "effective_from cannot be before the semester start date.",
                details={"semester_start": str(sem.start_date)},
            )
        if payload.effective_to and payload.effective_to > sem.end_date:
            raise ValidationException(
                "effective_to cannot be after the semester end date.",
                details={"semester_end": str(sem.end_date)},
            )
        if (
            payload.effective_from
            and payload.effective_to
            and payload.effective_from > payload.effective_to
        ):
            raise ValidationException("effective_from cannot be after effective_to.")

        eff_from, eff_to = await SchedulingService._resolve_effective_dates(
            db, offering.id, payload.effective_from, payload.effective_to
        )

        # 3. Validate Room
        if payload.room_id:
            room_stmt = select(Room).where(
                Room.id == payload.room_id,
                Room.university_id == university_id,
            )
            r_res = await db.execute(room_stmt)
            room = r_res.scalar_one_or_none()
            if not room:
                raise NotFoundException("Room", payload.room_id)
            if room.status != RoomStatus.ACTIVE.value:
                raise ValidationException("Designated room is not currently active.")

        # 4. Resolve and validate Lecturer
        target_lecturer_id = payload.lecturer_id
        if target_lecturer_id:
            # Must be assigned to this offering
            valid_assignment = any(
                la.lecturer_id == target_lecturer_id for la in offering.lecturer_assignments
            )
            if not valid_assignment:
                raise ValidationException(
                    "Designated lecturer is not assigned to this course offering.",
                    details={"lecturer_id": str(target_lecturer_id)},
                )
        else:
            # Default to primary lecturer if exists
            primary_la = next(
                (la for la in offering.lecturer_assignments if la.is_primary),
                None,
            )
            if primary_la:
                target_lecturer_id = primary_la.lecturer_id

        # 5. Multidimensional conflict validation
        await SchedulingService.check_offering_self_conflict(
            db=db,
            course_offering_id=offering.id,
            weekday=payload.weekday,
            start_time=payload.start_time,
            end_time=payload.end_time,
            eff_from=eff_from,
            eff_to=eff_to,
        )
        if payload.room_id:
            await SchedulingService.check_room_conflict(
                db=db,
                university_id=university_id,
                room_id=payload.room_id,
                weekday=payload.weekday,
                start_time=payload.start_time,
                end_time=payload.end_time,
                eff_from=eff_from,
                eff_to=eff_to,
            )
        if target_lecturer_id:
            await SchedulingService.check_lecturer_conflict(
                db=db,
                university_id=university_id,
                lecturer_id=target_lecturer_id,
                weekday=payload.weekday,
                start_time=payload.start_time,
                end_time=payload.end_time,
                eff_from=eff_from,
                eff_to=eff_to,
            )
        if offering.section_id:
            await SchedulingService.check_section_conflict(
                db=db,
                university_id=university_id,
                section_id=offering.section_id,
                weekday=payload.weekday,
                start_time=payload.start_time,
                end_time=payload.end_time,
                eff_from=eff_from,
                eff_to=eff_to,
            )

        # 6. Persist timetable rule
        timetable = Timetable(
            university_id=university_id,
            course_offering_id=payload.course_offering_id,
            room_id=payload.room_id,
            lecturer_id=target_lecturer_id,
            weekday=payload.weekday,
            start_time=payload.start_time,
            end_time=payload.end_time,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            status=TimetableStatus.ACTIVE.value,
        )
        db.add(timetable)
        await db.commit()
        await db.refresh(timetable)
        logger.info(
            f"TIMETABLE_CREATED id={timetable.id} offering_id={timetable.course_offering_id} "
            f"weekday={timetable.weekday} {timetable.start_time}-{timetable.end_time}"
        )
        return timetable

    @staticmethod
    async def get_timetable_rule(
        db: AsyncSession,
        timetable_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> TimetableDetailResponse:
        """Retrieve detailed timetable schedule rule by ID."""
        stmt = (
            select(Timetable)
            .options(
                selectinload(Timetable.course_offering).selectinload(CourseOffering.course),
                selectinload(Timetable.course_offering).selectinload(CourseOffering.section),
                selectinload(Timetable.room).selectinload(Room.building),
                selectinload(Timetable.lecturer).selectinload(Lecturer.user),
            )
            .where(
                Timetable.id == timetable_id,
                Timetable.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        tt = res.scalar_one_or_none()
        if not tt:
            raise NotFoundException("Timetable", timetable_id)

        detail = TimetableDetailResponse.model_validate(tt)
        if tt.course_offering:
            if tt.course_offering.course:
                detail.course_name = tt.course_offering.course.name
                detail.course_code = tt.course_offering.course.code
            if tt.course_offering.section:
                detail.section_name = tt.course_offering.section.name
        if tt.room:
            detail.room_number = tt.room.room_number
            if tt.room.building:
                detail.building_name = tt.room.building.name
        if tt.lecturer and tt.lecturer.user:
            detail.lecturer_name = tt.lecturer.user.username
        return detail

    @staticmethod
    async def list_timetables(
        db: AsyncSession,
        university_id: uuid.UUID,
        pagination: PaginationParams,
        semester_id: uuid.UUID | None = None,
        course_offering_id: uuid.UUID | None = None,
        academic_unit_id: uuid.UUID | None = None,
        room_id: uuid.UUID | None = None,
        lecturer_id: uuid.UUID | None = None,
        section_id: uuid.UUID | None = None,
        weekday: int | None = None,
        status: TimetableStatus | None = None,
    ) -> PaginatedResponse[TimetableDetailResponse]:
        """List paginated timetable rules with rich filtering."""
        query = (
            select(Timetable)
            .join(CourseOffering, Timetable.course_offering_id == CourseOffering.id)
            .options(
                selectinload(Timetable.course_offering).selectinload(CourseOffering.course),
                selectinload(Timetable.course_offering).selectinload(CourseOffering.section),
                selectinload(Timetable.room).selectinload(Room.building),
                selectinload(Timetable.lecturer).selectinload(Lecturer.user),
            )
            .where(Timetable.university_id == university_id)
        )

        if semester_id:
            query = query.where(CourseOffering.semester_id == semester_id)
        if course_offering_id:
            query = query.where(Timetable.course_offering_id == course_offering_id)
        if academic_unit_id:
            query = query.where(CourseOffering.academic_unit_id == academic_unit_id)
        if room_id:
            query = query.where(Timetable.room_id == room_id)
        if lecturer_id:
            query = query.where(Timetable.lecturer_id == lecturer_id)
        if section_id:
            query = query.where(CourseOffering.section_id == section_id)
        if weekday:
            query = query.where(Timetable.weekday == weekday)
        if status:
            query = query.where(Timetable.status == status.value)

        # Total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Page query
        query = query.order_by(Timetable.weekday.asc(), Timetable.start_time.asc())
        query = query.offset(pagination.offset).limit(pagination.page_size)
        items_res = await db.execute(query)
        timetables = items_res.scalars().all()

        details: list[TimetableDetailResponse] = []
        for tt in timetables:
            d = TimetableDetailResponse.model_validate(tt)
            if tt.course_offering:
                if tt.course_offering.course:
                    d.course_name = tt.course_offering.course.name
                    d.course_code = tt.course_offering.course.code
                if tt.course_offering.section:
                    d.section_name = tt.course_offering.section.name
            if tt.room:
                d.room_number = tt.room.room_number
                if tt.room.building:
                    d.building_name = tt.room.building.name
            if tt.lecturer and tt.lecturer.user:
                d.lecturer_name = tt.lecturer.user.username
            details.append(d)

        return PaginatedResponse.create(
            items=details,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def update_timetable_rule(
        db: AsyncSession,
        timetable_id: uuid.UUID,
        university_id: uuid.UUID,
        payload: TimetableUpdateRequest,
    ) -> TimetableDetailResponse:
        """Update timetable rule with conflict checks; leaves historical occurrences untouched."""
        stmt = (
            select(Timetable)
            .options(
                selectinload(Timetable.course_offering).selectinload(CourseOffering.semester),
                selectinload(Timetable.course_offering).selectinload(
                    CourseOffering.lecturer_assignments
                ),
            )
            .where(
                Timetable.id == timetable_id,
                Timetable.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        tt = res.scalar_one_or_none()
        if not tt:
            raise NotFoundException("Timetable", timetable_id)

        # Candidate values
        new_weekday = payload.weekday or tt.weekday
        new_start = payload.start_time or tt.start_time
        new_end = payload.end_time or tt.end_time
        new_room = payload.room_id if payload.room_id is not None else tt.room_id
        new_lecturer = payload.lecturer_id if payload.lecturer_id is not None else tt.lecturer_id
        new_from = (
            payload.effective_from if payload.effective_from is not None else tt.effective_from
        )
        new_to = payload.effective_to if payload.effective_to is not None else tt.effective_to

        if new_start >= new_end:
            raise ValidationException("Class start_time must be strictly before end_time.")

        eff_from, eff_to = await SchedulingService._resolve_effective_dates(
            db, tt.course_offering_id, new_from, new_to
        )

        # Conflict checks excluding current timetable
        await SchedulingService.check_offering_self_conflict(
            db=db,
            course_offering_id=tt.course_offering_id,
            weekday=new_weekday,
            start_time=new_start,
            end_time=new_end,
            eff_from=eff_from,
            eff_to=eff_to,
            exclude_timetable_id=tt.id,
        )
        if new_room:
            await SchedulingService.check_room_conflict(
                db=db,
                university_id=university_id,
                room_id=new_room,
                weekday=new_weekday,
                start_time=new_start,
                end_time=new_end,
                eff_from=eff_from,
                eff_to=eff_to,
                exclude_timetable_id=tt.id,
            )
        if new_lecturer:
            await SchedulingService.check_lecturer_conflict(
                db=db,
                university_id=university_id,
                lecturer_id=new_lecturer,
                weekday=new_weekday,
                start_time=new_start,
                end_time=new_end,
                eff_from=eff_from,
                eff_to=eff_to,
                exclude_timetable_id=tt.id,
            )
        if tt.course_offering.section_id:
            await SchedulingService.check_section_conflict(
                db=db,
                university_id=university_id,
                section_id=tt.course_offering.section_id,
                weekday=new_weekday,
                start_time=new_start,
                end_time=new_end,
                eff_from=eff_from,
                eff_to=eff_to,
                exclude_timetable_id=tt.id,
            )

        tt.weekday = new_weekday
        tt.start_time = new_start
        tt.end_time = new_end
        tt.room_id = new_room
        tt.lecturer_id = new_lecturer
        tt.effective_from = new_from
        tt.effective_to = new_to
        if payload.status is not None:
            tt.status = payload.status.value

        await db.commit()
        await db.refresh(tt)
        logger.info(f"TIMETABLE_UPDATED id={tt.id}")
        return await SchedulingService.get_timetable_rule(db, tt.id, university_id)

    @staticmethod
    async def set_timetable_status(
        db: AsyncSession,
        timetable_id: uuid.UUID,
        university_id: uuid.UUID,
        status: TimetableStatus,
    ) -> TimetableDetailResponse:
        """Update timetable operational status without deleting generated occurrences."""
        stmt = select(Timetable).where(
            Timetable.id == timetable_id,
            Timetable.university_id == university_id,
        )
        res = await db.execute(stmt)
        tt = res.scalar_one_or_none()
        if not tt:
            raise NotFoundException("Timetable", timetable_id)

        tt.status = status.value
        await db.commit()
        await db.refresh(tt)
        logger.info(f"TIMETABLE_DEACTIVATED id={tt.id} status={tt.status}")
        return await SchedulingService.get_timetable_rule(db, tt.id, university_id)

    # ==========================================
    # ClassOccurrence Generation Engine
    # ==========================================

    @staticmethod
    async def generate_occurrences_for_timetable(
        db: AsyncSession,
        timetable_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> OccurrenceGenerationResponse:
        """Deterministically expand recurring timetable rule into concrete ClassOccurrences."""
        # 1. Load timetable with parent course offering and university
        stmt = (
            select(Timetable)
            .options(
                selectinload(Timetable.course_offering).selectinload(CourseOffering.semester),
                selectinload(Timetable.university),
            )
            .where(
                Timetable.id == timetable_id,
                Timetable.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        tt = res.scalar_one_or_none()
        if not tt:
            raise NotFoundException("Timetable", timetable_id)

        if tt.status != TimetableStatus.ACTIVE.value:
            raise ValidationException("Cannot generate occurrences for an inactive timetable rule.")

        sem = tt.course_offering.semester
        tz_name = tt.university.timezone
        local_tz = zoneinfo.ZoneInfo(tz_name)

        # 2. Determine bounds: [max(sem.start, eff_from), min(sem.end, eff_to)]
        eff_start = max(sem.start_date, tt.effective_from or sem.start_date)
        eff_end = min(sem.end_date, tt.effective_to or sem.end_date)

        if eff_start > eff_end:
            return OccurrenceGenerationResponse(
                timetable_id=tt.id,
                generated_count=0,
                existing_count=0,
                message="Effective range falls entirely outside the semester.",
            )

        # 3. Enumerate dates matching timetable weekday (1=Mon ... 7=Sun)
        current_date = eff_start
        generated_count = 0
        existing_count = 0

        while current_date <= eff_end:
            if current_date.isoweekday() == tt.weekday:
                # Local datetime
                local_start = datetime.datetime.combine(
                    current_date, tt.start_time, tzinfo=local_tz
                )
                local_end = datetime.datetime.combine(current_date, tt.end_time, tzinfo=local_tz)

                # Convert to UTC
                utc_start = local_start.astimezone(datetime.UTC)
                utc_end = local_end.astimezone(datetime.UTC)

                # Check idempotency via (timetable_id, scheduled_start_utc)
                existing_stmt = select(ClassOccurrence).where(
                    ClassOccurrence.timetable_id == tt.id,
                    ClassOccurrence.scheduled_start_utc == utc_start,
                )
                ex_res = await db.execute(existing_stmt)
                if ex_res.scalar_one_or_none():
                    existing_count += 1
                else:
                    occurrence = ClassOccurrence(
                        university_id=tt.university_id,
                        course_offering_id=tt.course_offering_id,
                        timetable_id=tt.id,
                        room_id=tt.room_id,
                        lecturer_id=tt.lecturer_id,
                        local_date=current_date,
                        scheduled_start_utc=utc_start,
                        scheduled_end_utc=utc_end,
                        status=ClassOccurrenceStatus.SCHEDULED.value,
                    )
                    db.add(occurrence)
                    generated_count += 1

            current_date += datetime.timedelta(days=1)

        await db.commit()
        logger.info(
            f"OCCURRENCES_GENERATED tt={tt.id} gen={generated_count} existing={existing_count}"
        )
        return OccurrenceGenerationResponse(
            timetable_id=tt.id,
            generated_count=generated_count,
            existing_count=existing_count,
            message=(
                f"Generated {generated_count} class occurrences ({existing_count} already existed)."
            ),
        )

    @staticmethod
    async def generate_occurrences_for_semester(
        db: AsyncSession,
        semester_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> OccurrenceGenerationResponse:
        """Bulk generate concrete occurrences for all active timetable rules in a semester."""
        stmt = (
            select(Timetable)
            .join(CourseOffering, Timetable.course_offering_id == CourseOffering.id)
            .where(
                CourseOffering.semester_id == semester_id,
                Timetable.university_id == university_id,
                Timetable.status == TimetableStatus.ACTIVE.value,
            )
        )
        res = await db.execute(stmt)
        rules = res.scalars().all()

        total_gen = 0
        total_ex = 0
        for rule in rules:
            result = await SchedulingService.generate_occurrences_for_timetable(
                db=db,
                timetable_id=rule.id,
                university_id=university_id,
            )
            total_gen += result.generated_count
            total_ex += result.existing_count

        return OccurrenceGenerationResponse(
            semester_id=semester_id,
            generated_count=total_gen,
            existing_count=total_ex,
            message=(
                f"Semester occurrences generation complete: "
                f"{total_gen} created, {total_ex} existing."
            ),
        )

    # ==========================================
    # Concrete ClassOccurrence Operations
    # ==========================================

    @staticmethod
    async def get_class_occurrence(
        db: AsyncSession,
        occurrence_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> ClassOccurrenceDetailResponse:
        """Retrieve concrete class occurrence details."""
        stmt = (
            select(ClassOccurrence)
            .options(
                selectinload(ClassOccurrence.course_offering).selectinload(CourseOffering.course),
                selectinload(ClassOccurrence.course_offering).selectinload(CourseOffering.section),
                selectinload(ClassOccurrence.room).selectinload(Room.building),
                selectinload(ClassOccurrence.lecturer).selectinload(Lecturer.user),
                selectinload(ClassOccurrence.substitute_lecturer).selectinload(Lecturer.user),
            )
            .where(
                ClassOccurrence.id == occurrence_id,
                ClassOccurrence.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        occ = res.scalar_one_or_none()
        if not occ:
            raise NotFoundException("ClassOccurrence", occurrence_id)

        detail = ClassOccurrenceDetailResponse.model_validate(occ)
        if occ.course_offering:
            if occ.course_offering.course:
                detail.course_name = occ.course_offering.course.name
                detail.course_code = occ.course_offering.course.code
            if occ.course_offering.section:
                detail.section_name = occ.course_offering.section.name
        if occ.room:
            detail.room_number = occ.room.room_number
            if occ.room.building:
                detail.building_name = occ.room.building.name
        if occ.lecturer and occ.lecturer.user:
            detail.lecturer_name = occ.lecturer.user.username
        if occ.substitute_lecturer and occ.substitute_lecturer.user:
            detail.substitute_lecturer_name = occ.substitute_lecturer.user.username
        return detail

    @staticmethod
    async def list_class_occurrences(
        db: AsyncSession,
        university_id: uuid.UUID,
        pagination: PaginationParams,
        from_date: datetime.date | None = None,
        to_date: datetime.date | None = None,
        course_offering_id: uuid.UUID | None = None,
        room_id: uuid.UUID | None = None,
        lecturer_id: uuid.UUID | None = None,
        section_id: uuid.UUID | None = None,
        status: ClassOccurrenceStatus | None = None,
    ) -> PaginatedResponse[ClassOccurrenceDetailResponse]:
        """Query bounded class occurrences with pagination."""
        query = (
            select(ClassOccurrence)
            .join(CourseOffering, ClassOccurrence.course_offering_id == CourseOffering.id)
            .options(
                selectinload(ClassOccurrence.course_offering).selectinload(CourseOffering.course),
                selectinload(ClassOccurrence.course_offering).selectinload(CourseOffering.section),
                selectinload(ClassOccurrence.room).selectinload(Room.building),
                selectinload(ClassOccurrence.lecturer).selectinload(Lecturer.user),
                selectinload(ClassOccurrence.substitute_lecturer).selectinload(Lecturer.user),
            )
            .where(ClassOccurrence.university_id == university_id)
        )

        if from_date:
            query = query.where(ClassOccurrence.local_date >= from_date)
        if to_date:
            query = query.where(ClassOccurrence.local_date <= to_date)
        if course_offering_id:
            query = query.where(ClassOccurrence.course_offering_id == course_offering_id)
        if room_id:
            query = query.where(ClassOccurrence.room_id == room_id)
        if lecturer_id:
            query = query.where(
                or_(
                    ClassOccurrence.lecturer_id == lecturer_id,
                    ClassOccurrence.substitute_lecturer_id == lecturer_id,
                )
            )
        if section_id:
            query = query.where(CourseOffering.section_id == section_id)
        if status:
            query = query.where(ClassOccurrence.status == status.value)

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Query page items
        query = query.order_by(
            ClassOccurrence.scheduled_start_utc.asc(),
        )
        query = query.offset(pagination.offset).limit(pagination.page_size)
        items_res = await db.execute(query)
        occurrences = items_res.scalars().all()

        details: list[ClassOccurrenceDetailResponse] = []
        for occ in occurrences:
            d = ClassOccurrenceDetailResponse.model_validate(occ)
            if occ.course_offering:
                if occ.course_offering.course:
                    d.course_name = occ.course_offering.course.name
                    d.course_code = occ.course_offering.course.code
                if occ.course_offering.section:
                    d.section_name = occ.course_offering.section.name
            if occ.room:
                d.room_number = occ.room.room_number
                if occ.room.building:
                    d.building_name = occ.room.building.name
            if occ.lecturer and occ.lecturer.user:
                d.lecturer_name = occ.lecturer.user.username
            if occ.substitute_lecturer and occ.substitute_lecturer.user:
                d.substitute_lecturer_name = occ.substitute_lecturer.user.username
            details.append(d)

        return PaginatedResponse.create(
            items=details,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    @staticmethod
    async def cancel_occurrence(
        db: AsyncSession,
        occurrence_id: uuid.UUID,
        university_id: uuid.UUID,
        reason: str,
    ) -> ClassOccurrenceDetailResponse:
        """Administratively cancel a concrete class meeting while preserving audit history."""
        stmt = select(ClassOccurrence).where(
            ClassOccurrence.id == occurrence_id,
            ClassOccurrence.university_id == university_id,
        )
        res = await db.execute(stmt)
        occ = res.scalar_one_or_none()
        if not occ:
            raise NotFoundException("ClassOccurrence", occurrence_id)

        occ.status = ClassOccurrenceStatus.CANCELLED.value
        occ.cancellation_reason = reason.strip()

        await db.commit()
        await db.refresh(occ)
        logger.info(f"CLASS_OCCURRENCE_CANCELLED id={occ.id} reason={occ.cancellation_reason}")
        return await SchedulingService.get_class_occurrence(db, occ.id, university_id)

    @staticmethod
    async def reschedule_occurrence(
        db: AsyncSession,
        occurrence_id: uuid.UUID,
        university_id: uuid.UUID,
        payload: OccurrenceRescheduleRequest,
    ) -> ClassOccurrenceDetailResponse:
        """Reschedule a specific class meeting, validating conflicts and preserving history."""
        stmt = (
            select(ClassOccurrence)
            .options(
                selectinload(ClassOccurrence.course_offering),
                selectinload(ClassOccurrence.university),
            )
            .where(
                ClassOccurrence.id == occurrence_id,
                ClassOccurrence.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        original = res.scalar_one_or_none()
        if not original:
            raise NotFoundException("ClassOccurrence", occurrence_id)

        if payload.new_start_time >= payload.new_end_time:
            raise ValidationException("New class start time must be strictly before end time.")

        # Local and UTC calculation
        tz_name = original.university.timezone
        local_tz = zoneinfo.ZoneInfo(tz_name)
        new_local_start = datetime.datetime.combine(
            payload.new_date, payload.new_start_time, tzinfo=local_tz
        )
        new_local_end = datetime.datetime.combine(
            payload.new_date, payload.new_end_time, tzinfo=local_tz
        )
        new_utc_start = new_local_start.astimezone(datetime.UTC)
        new_utc_end = new_local_end.astimezone(datetime.UTC)

        target_room_id = payload.new_room_id or original.room_id
        target_lecturer_id = payload.substitute_lecturer_id or original.lecturer_id

        # Conflict check against active concrete occurrences
        if target_room_id:
            room_conf_stmt = select(ClassOccurrence).where(
                ClassOccurrence.university_id == university_id,
                ClassOccurrence.room_id == target_room_id,
                ClassOccurrence.local_date == payload.new_date,
                ClassOccurrence.status == ClassOccurrenceStatus.SCHEDULED.value,
                ClassOccurrence.id != original.id,
                ClassOccurrence.scheduled_start_utc < new_utc_end,
                ClassOccurrence.scheduled_end_utc > new_utc_start,
            )
            rc_res = await db.execute(room_conf_stmt)
            if rc_res.scalar_one_or_none():
                raise ConflictException(
                    "Target room is already booked for another class at this rescheduled time.",
                    code="ROOM_SCHEDULE_CONFLICT",
                    details={"conflict_type": "ROOM_SCHEDULE_CONFLICT"},
                )

        if target_lecturer_id:
            lec_conf_stmt = select(ClassOccurrence).where(
                ClassOccurrence.university_id == university_id,
                or_(
                    ClassOccurrence.lecturer_id == target_lecturer_id,
                    ClassOccurrence.substitute_lecturer_id == target_lecturer_id,
                ),
                ClassOccurrence.local_date == payload.new_date,
                ClassOccurrence.status == ClassOccurrenceStatus.SCHEDULED.value,
                ClassOccurrence.id != original.id,
                ClassOccurrence.scheduled_start_utc < new_utc_end,
                ClassOccurrence.scheduled_end_utc > new_utc_start,
            )
            lc_res = await db.execute(lec_conf_stmt)
            if lc_res.scalar_one_or_none():
                raise ConflictException(
                    "Lecturer has another scheduled class at this rescheduled time.",
                    code="LECTURER_SCHEDULE_CONFLICT",
                    details={"conflict_type": "LECTURER_SCHEDULE_CONFLICT"},
                )

        # 1. Create new rescheduled occurrence
        new_occ = ClassOccurrence(
            university_id=university_id,
            course_offering_id=original.course_offering_id,
            timetable_id=original.timetable_id,
            room_id=target_room_id,
            lecturer_id=original.lecturer_id,
            substitute_lecturer_id=payload.substitute_lecturer_id,
            local_date=payload.new_date,
            scheduled_start_utc=new_utc_start,
            scheduled_end_utc=new_utc_end,
            status=ClassOccurrenceStatus.SCHEDULED.value,
            cancellation_reason=None,
            rescheduled_from_id=original.id,
        )
        db.add(new_occ)
        await db.flush()

        # 2. Mark original as RESCHEDULED and link
        original.status = ClassOccurrenceStatus.RESCHEDULED.value
        original.cancellation_reason = payload.reason or "Rescheduled to new date/time"
        original.rescheduled_to_id = new_occ.id

        await db.commit()
        await db.refresh(new_occ)
        logger.info(
            f"CLASS_OCCURRENCE_RESCHEDULED old_id={original.id} "
            f"new_id={new_occ.id} date={new_occ.local_date}"
        )
        return await SchedulingService.get_class_occurrence(db, new_occ.id, university_id)

    # ==========================================
    # Personal Schedules (Self-Views)
    # ==========================================

    @staticmethod
    async def get_lecturer_schedule(
        db: AsyncSession,
        user_id: uuid.UUID,
        university_id: uuid.UUID,
        from_date: datetime.date | None = None,
        to_date: datetime.date | None = None,
    ) -> list[ClassOccurrenceDetailResponse]:
        """Fetch concrete class meetings for offerings assigned to the logged-in lecturer."""
        # Find lecturer profile for this user
        lec_stmt = select(Lecturer).where(
            Lecturer.user_id == user_id,
            Lecturer.university_id == university_id,
        )
        l_res = await db.execute(lec_stmt)
        lecturer = l_res.scalar_one_or_none()
        if not lecturer:
            return []

        # Find assigned course offering IDs
        assign_stmt = select(LecturerAssignment.course_offering_id).where(
            LecturerAssignment.lecturer_id == lecturer.id,
        )
        a_res = await db.execute(assign_stmt)
        offering_ids = list(a_res.scalars().all())
        if not offering_ids:
            return []

        query = (
            select(ClassOccurrence)
            .options(
                selectinload(ClassOccurrence.course_offering).selectinload(CourseOffering.course),
                selectinload(ClassOccurrence.course_offering).selectinload(CourseOffering.section),
                selectinload(ClassOccurrence.room).selectinload(Room.building),
                selectinload(ClassOccurrence.lecturer).selectinload(Lecturer.user),
            )
            .where(
                ClassOccurrence.course_offering_id.in_(offering_ids),
                ClassOccurrence.university_id == university_id,
            )
        )
        if from_date:
            query = query.where(ClassOccurrence.local_date >= from_date)
        if to_date:
            query = query.where(ClassOccurrence.local_date <= to_date)

        query = query.order_by(ClassOccurrence.scheduled_start_utc.asc())
        res = await db.execute(query)
        occurrences = res.scalars().all()

        details: list[ClassOccurrenceDetailResponse] = []
        for occ in occurrences:
            d = ClassOccurrenceDetailResponse.model_validate(occ)
            if occ.course_offering:
                if occ.course_offering.course:
                    d.course_name = occ.course_offering.course.name
                    d.course_code = occ.course_offering.course.code
                if occ.course_offering.section:
                    d.section_name = occ.course_offering.section.name
            if occ.room:
                d.room_number = occ.room.room_number
                if occ.room.building:
                    d.building_name = occ.room.building.name
            if occ.lecturer and occ.lecturer.user:
                d.lecturer_name = occ.lecturer.user.username
            details.append(d)
        return details

    @staticmethod
    async def get_student_schedule(
        db: AsyncSession,
        user_id: uuid.UUID,
        university_id: uuid.UUID,
        from_date: datetime.date | None = None,
        to_date: datetime.date | None = None,
    ) -> list[ClassOccurrenceDetailResponse]:
        """Fetch concrete class meetings for offerings actively enrolled by the student."""
        # Find student profile for this user
        stu_stmt = select(Student).where(
            Student.user_id == user_id,
            Student.university_id == university_id,
        )
        s_res = await db.execute(stu_stmt)
        student = s_res.scalar_one_or_none()
        if not student:
            return []

        # Find actively enrolled offerings only (DROPPED excluded per M7.1)
        enr_stmt = select(Enrollment.course_offering_id).where(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVE.value,
        )
        e_res = await db.execute(enr_stmt)
        offering_ids = list(e_res.scalars().all())
        if not offering_ids:
            return []

        query = (
            select(ClassOccurrence)
            .options(
                selectinload(ClassOccurrence.course_offering).selectinload(CourseOffering.course),
                selectinload(ClassOccurrence.course_offering).selectinload(CourseOffering.section),
                selectinload(ClassOccurrence.room).selectinload(Room.building),
                selectinload(ClassOccurrence.lecturer).selectinload(Lecturer.user),
            )
            .where(
                ClassOccurrence.course_offering_id.in_(offering_ids),
                ClassOccurrence.university_id == university_id,
            )
        )
        if from_date:
            query = query.where(ClassOccurrence.local_date >= from_date)
        if to_date:
            query = query.where(ClassOccurrence.local_date <= to_date)

        query = query.order_by(ClassOccurrence.scheduled_start_utc.asc())
        res = await db.execute(query)
        occurrences = res.scalars().all()

        details: list[ClassOccurrenceDetailResponse] = []
        for occ in occurrences:
            d = ClassOccurrenceDetailResponse.model_validate(occ)
            if occ.course_offering:
                if occ.course_offering.course:
                    d.course_name = occ.course_offering.course.name
                    d.course_code = occ.course_offering.course.code
                if occ.course_offering.section:
                    d.section_name = occ.course_offering.section.name
            if occ.room:
                d.room_number = occ.room.room_number
                if occ.room.building:
                    d.building_name = occ.room.building.name
            if occ.lecturer and occ.lecturer.user:
                d.lecturer_name = occ.lecturer.user.username
            details.append(d)
        return details
