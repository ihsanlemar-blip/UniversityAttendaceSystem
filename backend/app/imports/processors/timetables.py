"""Timetable schedule import domain processor."""

import datetime
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.constants import ImportRowAction, ImportRowStatus, TimetableStatus
from backend.app.core.exceptions import ConflictException
from backend.app.imports.processors.base import BaseImportProcessor
from backend.app.imports.schemas import ImportTemplateColumn
from backend.app.models.building import Building
from backend.app.models.course import Course
from backend.app.models.course_offering import CourseOffering
from backend.app.models.import_job import ImportRow
from backend.app.models.lecturer import Lecturer
from backend.app.models.room import Room
from backend.app.models.section import Section
from backend.app.models.semester import Semester
from backend.app.models.timetable import Timetable
from backend.app.scheduling.service import SchedulingService, times_overlap


def _parse_time(val: Any) -> datetime.time | None:
    """Parse time string in HH:MM or HH:MM:SS format."""
    if isinstance(val, datetime.time):
        return val
    if not val:
        return None
    s = str(val).strip()
    parts = s.split(":")
    if len(parts) == 2:
        try:
            return datetime.time(int(parts[0]), int(parts[1]))
        except ValueError:
            return None
    elif len(parts) == 3:
        try:
            return datetime.time(int(parts[0]), int(parts[1]), int(float(parts[2])))
        except ValueError:
            return None
    return None


class TimetableImportProcessor(BaseImportProcessor):
    """Domain processor for validating and committing recurring timetable schedules."""

    def get_required_headers(self) -> list[str]:
        return ["course_code", "semester_code", "weekday", "start_time", "end_time"]

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
                description="Target academic semester code",
                example="FALL-2026",
            ),
            ImportTemplateColumn(
                name="weekday",
                required=True,
                description="Day of week (1=Monday, 2=Tuesday, ..., 7=Sunday)",
                example="1",
            ),
            ImportTemplateColumn(
                name="start_time",
                required=True,
                description="Class start time in 24h format (HH:MM or HH:MM:SS)",
                example="08:30",
            ),
            ImportTemplateColumn(
                name="end_time",
                required=True,
                description="Class end time in 24h format (HH:MM or HH:MM:SS)",
                example="10:00",
            ),
            ImportTemplateColumn(
                name="section_code",
                required=False,
                description="Cohort section code (if course has multiple sections)",
                example="CS-SEC-A",
            ),
            ImportTemplateColumn(
                name="building_code",
                required=False,
                description="Campus building code containing the classroom",
                example="BLD-ENG",
            ),
            ImportTemplateColumn(
                name="room_number",
                required=False,
                description="Room / classroom number",
                example="101",
            ),
            ImportTemplateColumn(
                name="lecturer_code",
                required=False,
                description="Assigned instructor employee code",
                example="EMP-LEC-101",
            ),
            ImportTemplateColumn(
                name="effective_from",
                required=False,
                description="Schedule effective start date (YYYY-MM-DD)",
                example="2026-09-01",
            ),
            ImportTemplateColumn(
                name="effective_to",
                required=False,
                description="Schedule effective end date (YYYY-MM-DD)",
                example="2026-12-31",
            ),
            ImportTemplateColumn(
                name="status",
                required=False,
                description="Timetable rule status: ACTIVE or INACTIVE",
                example="ACTIVE",
            ),
        ]

    def get_sample_csv(self) -> str:
        return (
            "course_code,semester_code,section_code,weekday,start_time,end_time,building_code,room_number,lecturer_code\n"
            "CS-101,FALL-2026,CS-SEC-A,1,08:30,10:00,BLD-ENG,101,EMP-LEC-101\n"
            "CS-101,FALL-2026,CS-SEC-A,3,08:30,10:00,BLD-ENG,101,EMP-LEC-101\n"
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

        weekday_raw = raw_data.get("weekday")
        if weekday_raw is None or str(weekday_raw).strip() == "":
            errors.append(
                {
                    "field": "weekday",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Weekday (1-7) is required.",
                }
            )

        start_time_raw = raw_data.get("start_time")
        if not start_time_raw:
            errors.append(
                {
                    "field": "start_time",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Start time is required.",
                }
            )

        end_time_raw = raw_data.get("end_time")
        if not end_time_raw:
            errors.append(
                {
                    "field": "end_time",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "End time is required.",
                }
            )

        if errors:
            return normalized_data, action, ImportRowStatus.ERROR.value, errors, warnings

        c_code_clean = str(course_code).strip()
        sem_code_clean = str(semester_code).strip()
        sec_code_raw = raw_data.get("section_code")
        sec_code_clean = str(sec_code_raw).strip() if sec_code_raw else None

        # 2. Parse Weekday
        weekday = 0
        try:
            assert weekday_raw is not None
            weekday = int(weekday_raw)
            if weekday < 1 or weekday > 7:
                errors.append(
                    {
                        "field": "weekday",
                        "code": "INVALID_WEEKDAY",
                        "message": "Weekday must be an integer between 1 (Monday) and 7 (Sunday).",
                    }
                )
            else:
                normalized_data["weekday"] = weekday
        except ValueError, TypeError:
            errors.append(
                {
                    "field": "weekday",
                    "code": "INVALID_WEEKDAY",
                    "message": f"Invalid integer for weekday: '{weekday_raw}'.",
                }
            )

        # 3. Parse Start and End Times
        start_t = _parse_time(start_time_raw)
        if not start_t:
            errors.append(
                {
                    "field": "start_time",
                    "code": "INVALID_TIME_FORMAT",
                    "message": f"Invalid start time '{start_time_raw}'. Expected HH:MM[:SS].",
                }
            )

        end_t = _parse_time(end_time_raw)
        if not end_t:
            errors.append(
                {
                    "field": "end_time",
                    "code": "INVALID_TIME_FORMAT",
                    "message": f"Invalid end time '{end_time_raw}'. Expected HH:MM or HH:MM:SS.",
                }
            )

        if start_t and end_t:
            if start_t >= end_t:
                errors.append(
                    {
                        "field": "start_time",
                        "code": "INVALID_TIME_RANGE",
                        "message": f"Start time ({start_t}) must precede end time ({end_t}).",
                    }
                )
            else:
                normalized_data["start_time"] = start_t.strftime("%H:%M:%S")
                normalized_data["end_time"] = end_t.strftime("%H:%M:%S")

        # 4. Resolve Course & Semester & Section -> Offering
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
                            f"Course offering not found for course '{c_code_clean}', "
                            f"semester '{sem_code_clean}', section '{sec_code_clean or 'None'}'."
                        ),
                    }
                )
            else:
                normalized_data["course_offering_id"] = str(offering.id)

        # 5. Parse Effective Date Range
        eff_from = None
        eff_from_raw = raw_data.get("effective_from")
        if eff_from_raw:
            try:
                eff_from = datetime.date.fromisoformat(str(eff_from_raw).strip())
                normalized_data["effective_from"] = eff_from.isoformat()
            except ValueError:
                errors.append(
                    {
                        "field": "effective_from",
                        "code": "INVALID_DATE_FORMAT",
                        "message": f"Invalid date '{eff_from_raw}'. Expected YYYY-MM-DD.",
                    }
                )

        eff_to = None
        eff_to_raw = raw_data.get("effective_to")
        if eff_to_raw:
            try:
                eff_to = datetime.date.fromisoformat(str(eff_to_raw).strip())
                normalized_data["effective_to"] = eff_to.isoformat()
            except ValueError:
                errors.append(
                    {
                        "field": "effective_to",
                        "code": "INVALID_DATE_FORMAT",
                        "message": f"Invalid date '{eff_to_raw}'. Expected YYYY-MM-DD.",
                    }
                )

        if eff_from and eff_to and eff_from > eff_to:
            errors.append(
                {
                    "field": "effective_from",
                    "code": "INVALID_DATE_RANGE",
                    "message": "effective_from cannot be after effective_to.",
                }
            )

        # 6. Resolve Room
        room_number_raw = raw_data.get("room_number")
        bld_code_raw = raw_data.get("building_code")
        room_id: uuid.UUID | None = None
        if room_number_raw:
            r_num = str(room_number_raw).strip()
            if bld_code_raw:
                b_code = str(bld_code_raw).strip()
                bld_stmt = select(Building).where(
                    Building.university_id == university_id,
                    func.lower(Building.code) == b_code.lower(),
                )
                bld_res = await db.execute(bld_stmt)
                building = bld_res.scalar_one_or_none()
                if not building:
                    errors.append(
                        {
                            "field": "building_code",
                            "code": "BUILDING_NOT_FOUND",
                            "message": f"Building '{b_code}' not found in this university.",
                        }
                    )
                else:
                    room_stmt = select(Room).where(
                        Room.university_id == university_id,
                        Room.building_id == building.id,
                        func.lower(Room.room_number) == r_num.lower(),
                    )
                    room_res = await db.execute(room_stmt)
                    room = room_res.scalar_one_or_none()
                    if not room:
                        errors.append(
                            {
                                "field": "room_number",
                                "code": "ROOM_NOT_FOUND",
                                "message": f"Room '{r_num}' not found in building '{b_code}'.",
                            }
                        )
                    else:
                        room_id = room.id
                        normalized_data["room_id"] = str(room.id)
            else:
                room_stmt = select(Room).where(
                    Room.university_id == university_id,
                    func.lower(Room.room_number) == r_num.lower(),
                )
                room_res = await db.execute(room_stmt)
                rooms = room_res.scalars().all()
                if not rooms:
                    errors.append(
                        {
                            "field": "room_number",
                            "code": "ROOM_NOT_FOUND",
                            "message": f"Room '{r_num}' does not exist in this university.",
                        }
                    )
                elif len(rooms) > 1:
                    errors.append(
                        {
                            "field": "building_code",
                            "code": "AMBIGUOUS_ROOM",
                            "message": (
                                f"Multiple rooms '{r_num}' exist. Please specify 'building_code'."
                            ),
                        }
                    )
                else:
                    room_id = rooms[0].id
                    normalized_data["room_id"] = str(rooms[0].id)

        # 7. Resolve Lecturer
        lec_code_raw = raw_data.get("lecturer_code") or raw_data.get("employee_code")
        lecturer_id: uuid.UUID | None = None
        if lec_code_raw:
            l_code = str(lec_code_raw).strip()
            lec_stmt = select(Lecturer).where(
                Lecturer.university_id == university_id,
                func.lower(Lecturer.employee_code) == l_code.lower(),
            )
            lec_res = await db.execute(lec_stmt)
            lecturer = lec_res.scalar_one_or_none()
            if not lecturer:
                errors.append(
                    {
                        "field": "lecturer_code",
                        "code": "LECTURER_NOT_FOUND",
                        "message": f"Lecturer '{l_code}' not found in this university.",
                    }
                )
            else:
                lecturer_id = lecturer.id
                normalized_data["lecturer_id"] = str(lecturer.id)

        # 8. Check intra-file conflicts
        # Keep track of file schedules: (type, entity_id, weekday, start_t, end_t)
        file_schedules = seen_keys.setdefault("schedules", [])
        if start_t and end_t and weekday >= 1 and weekday <= 7:
            for s_type, s_id, s_day, s_start, s_end in file_schedules:
                if s_day == weekday and times_overlap(start_t, end_t, s_start, s_end):
                    if room_id and s_type == "room" and s_id == room_id:
                        errors.append(
                            {
                                "field": "room_number",
                                "code": "ROOM_SCHEDULE_CONFLICT_IN_FILE",
                                "message": "Room is scheduled for another class in this file.",
                            }
                        )
                    if lecturer_id and s_type == "lecturer" and s_id == lecturer_id:
                        errors.append(
                            {
                                "field": "lecturer_code",
                                "code": "LECTURER_SCHEDULE_CONFLICT_IN_FILE",
                                "message": "Lecturer is scheduled for another class in this file.",
                            }
                        )

            if room_id:
                file_schedules.append(("room", room_id, weekday, start_t, end_t))
            if lecturer_id:
                file_schedules.append(("lecturer", lecturer_id, weekday, start_t, end_t))

        # 9. Database Conflict Engine Checks
        if semester and start_t and end_t and weekday >= 1 and weekday <= 7 and not errors:
            check_from = eff_from or semester.start_date
            check_to = eff_to or semester.end_date

            if room_id:
                try:
                    await SchedulingService.check_room_conflict(
                        db=db,
                        university_id=university_id,
                        room_id=room_id,
                        weekday=weekday,
                        start_time=start_t,
                        end_time=end_t,
                        eff_from=check_from,
                        eff_to=check_to,
                    )
                except ConflictException as c_err:
                    errors.append(
                        {
                            "field": "room_number",
                            "code": c_err.code or "ROOM_SCHEDULE_CONFLICT",
                            "message": str(c_err.message),
                        }
                    )

            if lecturer_id:
                try:
                    await SchedulingService.check_lecturer_conflict(
                        db=db,
                        university_id=university_id,
                        lecturer_id=lecturer_id,
                        weekday=weekday,
                        start_time=start_t,
                        end_time=end_t,
                        eff_from=check_from,
                        eff_to=check_to,
                    )
                except ConflictException as c_err:
                    errors.append(
                        {
                            "field": "lecturer_code",
                            "code": c_err.code or "LECTURER_SCHEDULE_CONFLICT",
                            "message": str(c_err.message),
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
        weekday = int(data["weekday"])
        start_t = _parse_time(data["start_time"])
        end_t = _parse_time(data["end_time"])
        assert start_t is not None and end_t is not None

        room_id = uuid.UUID(data["room_id"]) if data.get("room_id") else None
        lecturer_id = uuid.UUID(data["lecturer_id"]) if data.get("lecturer_id") else None
        eff_from = (
            datetime.date.fromisoformat(str(data["effective_from"]))
            if data.get("effective_from")
            else None
        )
        eff_to = (
            datetime.date.fromisoformat(str(data["effective_to"]))
            if data.get("effective_to")
            else None
        )
        status = data.get("status") or TimetableStatus.ACTIVE.value

        new_timetable = Timetable(
            university_id=university_id,
            course_offering_id=course_offering_id,
            room_id=room_id,
            lecturer_id=lecturer_id,
            weekday=weekday,
            start_time=start_t,
            end_time=end_t,
            effective_from=eff_from,
            effective_to=eff_to,
            status=status,
        )
        db.add(new_timetable)
        await db.flush()
        return new_timetable.id, "Timetable"
