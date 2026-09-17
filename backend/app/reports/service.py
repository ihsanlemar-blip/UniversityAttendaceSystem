"""Reporting service for authoritative attendance calculation and threshold evaluations."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.common.types import utc_now
from backend.app.core.constants import (
    AttendanceSessionStatus,
    AttendanceStatus,
    PolicyScopeType,
    RecordStatus,
    ThresholdStatus,
)
from backend.app.core.exceptions import NotFoundException
from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.attendance_policy import AttendancePolicy
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.course import Course
from backend.app.models.course_offering import CourseOffering
from backend.app.models.enrollment import Enrollment
from backend.app.models.lecturer import Lecturer
from backend.app.models.room import Room
from backend.app.models.student import Student


class ReportingService:
    """Core domain reporting engine for institutional attendance data."""

    DEFAULT_THRESHOLD = 75.0
    DEFAULT_MARGIN = 5.0

    @classmethod
    def evaluate_threshold(
        cls,
        percentage: float,
        threshold: float = DEFAULT_THRESHOLD,
        margin: float = DEFAULT_MARGIN,
    ) -> ThresholdStatus:
        """Categorize an attendance percentage into neutral threshold states."""
        if percentage >= threshold:
            return ThresholdStatus.ABOVE_THRESHOLD
        elif percentage >= (threshold - margin):
            return ThresholdStatus.NEAR_THRESHOLD
        else:
            return ThresholdStatus.BELOW_THRESHOLD

    @classmethod
    async def resolve_offering_threshold(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        course_offering: CourseOffering,
    ) -> float:
        """Resolve applicable attendance policy threshold for a course offering."""
        # Check course override
        if course_offering.course_id:
            c_policy_stmt = (
                select(AttendancePolicy)
                .where(
                    AttendancePolicy.university_id == university_id,
                    AttendancePolicy.course_id == course_offering.course_id,
                    AttendancePolicy.scope_type == PolicyScopeType.COURSE.value,
                    AttendancePolicy.status == RecordStatus.ACTIVE.value,
                )
                .order_by(AttendancePolicy.created_at.desc())
            )
            c_policy = (await db.execute(c_policy_stmt)).scalars().first()
            if c_policy:
                return float(c_policy.min_attendance_percentage)

        # Check university default policy
        u_policy_stmt = (
            select(AttendancePolicy)
            .where(
                AttendancePolicy.university_id == university_id,
                AttendancePolicy.scope_type == PolicyScopeType.UNIVERSITY.value,
                AttendancePolicy.status == RecordStatus.ACTIVE.value,
            )
            .order_by(AttendancePolicy.created_at.desc())
        )
        u_policy = (await db.execute(u_policy_stmt)).scalars().first()
        if u_policy:
            return float(u_policy.min_attendance_percentage)

        return cls.DEFAULT_THRESHOLD

    @classmethod
    async def get_course_roster_report(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        course_offering_id: uuid.UUID,
        threshold_filter: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Generate comprehensive course offering roster attendance report."""
        # 1. Fetch offering and related entities
        off_stmt = (
            select(CourseOffering)
            .options(
                selectinload(CourseOffering.course),
                selectinload(CourseOffering.semester),
                selectinload(CourseOffering.section),
            )
            .where(
                CourseOffering.id == course_offering_id,
                CourseOffering.university_id == university_id,
            )
        )
        off_res = await db.execute(off_stmt)
        offering = off_res.scalar_one_or_none()
        if not offering:
            raise NotFoundException("CourseOffering", course_offering_id)

        threshold_pct = await cls.resolve_offering_threshold(db, university_id, offering)

        # 2. Count conducted/closed sessions for this offering
        sess_count_stmt = (
            select(func.count(AttendanceSession.id))
            .join(ClassOccurrence, AttendanceSession.class_occurrence_id == ClassOccurrence.id)
            .where(
                ClassOccurrence.course_offering_id == course_offering_id,
                AttendanceSession.university_id == university_id,
                AttendanceSession.status == AttendanceSessionStatus.CLOSED.value,
            )
        )
        total_conducted_sessions = (await db.execute(sess_count_stmt)).scalar() or 0

        # 3. Get all active/enrolled students in this offering
        enr_stmt = (
            select(Enrollment)
            .options(
                selectinload(Enrollment.student).selectinload(Student.user),
            )
            .where(
                Enrollment.course_offering_id == course_offering_id,
                Enrollment.university_id == university_id,
            )
            .order_by(Enrollment.created_at.asc())
        )
        enrollments = list((await db.execute(enr_stmt)).scalars().all())

        # 4. Fetch all records for this offering's closed sessions
        records_stmt = (
            select(AttendanceRecord)
            .join(AttendanceSession, AttendanceRecord.attendance_session_id == AttendanceSession.id)
            .join(ClassOccurrence, AttendanceSession.class_occurrence_id == ClassOccurrence.id)
            .where(
                ClassOccurrence.course_offering_id == course_offering_id,
                AttendanceSession.university_id == university_id,
                AttendanceSession.status == AttendanceSessionStatus.CLOSED.value,
            )
        )
        records = list((await db.execute(records_stmt)).scalars().all())

        # Group records by student_id
        student_records: dict[uuid.UUID, list[AttendanceRecord]] = {}
        for rec in records:
            student_records.setdefault(rec.student_id, []).append(rec)

        # 5. Build roster items
        roster_items: list[dict[str, Any]] = []
        above_count = 0
        near_count = 0
        below_count = 0
        total_pct_sum = 0.0

        for enr in enrollments:
            student = enr.student
            user = student.user if student else None
            s_name = user.username if user else "Student"
            s_num = student.student_number if student else ""

            s_recs = student_records.get(enr.student_id, [])

            present_count = 0
            late_count = 0
            absent_count = 0
            excused_count = 0
            leave_count = 0
            has_revision = False
            total_credit = 0.0
            eligible_sessions = 0

            for r in s_recs:
                if r.version_no > 1:
                    has_revision = True

                total_credit += float(r.attendance_credit)

                if r.status == AttendanceStatus.PRESENT.value:
                    present_count += 1
                    eligible_sessions += 1
                elif r.status == AttendanceStatus.LATE.value:
                    late_count += 1
                    eligible_sessions += 1
                elif r.status == AttendanceStatus.ABSENT.value:
                    absent_count += 1
                    eligible_sessions += 1
                elif r.status == AttendanceStatus.EXCUSED.value:
                    excused_count += 1
                    eligible_sessions += 1
                elif r.status == AttendanceStatus.LEAVE.value:
                    leave_count += 1
                    # Approved leaves excluded from denominator per policy
                else:
                    eligible_sessions += 1

            # Compute percentage
            if eligible_sessions > 0:
                calc_pct = round((total_credit / eligible_sessions) * 100.0, 1)
                pct = min(100.0, max(0.0, calc_pct))
            else:
                pct = 100.0

            total_pct_sum += pct
            th_status = cls.evaluate_threshold(pct, threshold_pct, cls.DEFAULT_MARGIN)

            if th_status == ThresholdStatus.ABOVE_THRESHOLD:
                above_count += 1
            elif th_status == ThresholdStatus.NEAR_THRESHOLD:
                near_count += 1
            else:
                below_count += 1

            item = {
                "student_id": enr.student_id,
                "student_number": s_num,
                "student_name": s_name,
                "eligible_sessions": eligible_sessions,
                "attendance_credit": round(total_credit, 2),
                "attendance_percentage": pct,
                "present_count": present_count,
                "late_count": late_count,
                "absent_count": absent_count,
                "excused_count": excused_count,
                "leave_count": leave_count,
                "has_revision": has_revision,
                "threshold_status": th_status.value,
            }
            roster_items.append(item)

        # Apply threshold filter if provided
        filtered_items = roster_items
        if threshold_filter:
            tf_upper = threshold_filter.upper().strip()
            if tf_upper in {s.value for s in ThresholdStatus}:
                filtered_items = [i for i in roster_items if i["threshold_status"] == tf_upper]

        total_enrolled = len(enrollments)
        avg_pct = round(total_pct_sum / total_enrolled, 1) if total_enrolled > 0 else 100.0

        # Pagination
        total_items = len(filtered_items)
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 1
        start_idx = (page - 1) * page_size
        paginated_roster = filtered_items[start_idx : start_idx + page_size]

        return {
            "course_offering_id": course_offering_id,
            "course_code": offering.course.code if offering.course else "",
            "course_name": offering.course.name if offering.course else "",
            "semester_code": offering.semester.code if offering.semester else "",
            "section_code": offering.section.code if offering.section else None,
            "total_sessions_conducted": total_conducted_sessions,
            "threshold_percentage": threshold_pct,
            "near_threshold_margin": cls.DEFAULT_MARGIN,
            "total_enrolled": total_enrolled,
            "average_attendance_percentage": avg_pct,
            "above_threshold_count": above_count,
            "near_threshold_count": near_count,
            "below_threshold_count": below_count,
            "generated_at_utc": utc_now(),
            "roster": paginated_roster,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @classmethod
    async def get_student_attendance_summary(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        student_id: uuid.UUID,
        semester_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Generate multi-course attendance summary for a specific student."""
        # 1. Verify student exists
        s_stmt = (
            select(Student)
            .options(selectinload(Student.user))
            .where(
                Student.id == student_id,
                Student.university_id == university_id,
            )
        )
        student = (await db.execute(s_stmt)).scalar_one_or_none()
        if not student:
            raise NotFoundException("Student", student_id)

        # 2. Get student enrollments
        enr_stmt = (
            select(Enrollment)
            .options(
                selectinload(Enrollment.course_offering).selectinload(CourseOffering.course),
                selectinload(Enrollment.course_offering).selectinload(CourseOffering.semester),
                selectinload(Enrollment.course_offering).selectinload(CourseOffering.section),
            )
            .where(
                Enrollment.student_id == student_id,
                Enrollment.university_id == university_id,
            )
        )
        if semester_id:
            enr_stmt = enr_stmt.join(
                CourseOffering, Enrollment.course_offering_id == CourseOffering.id
            ).where(CourseOffering.semester_id == semester_id)

        enrollments = list((await db.execute(enr_stmt)).scalars().all())

        course_items: list[dict[str, Any]] = []
        total_pct_sum = 0.0
        below_count = 0

        for enr in enrollments:
            offering = enr.course_offering
            if not offering:
                continue

            threshold_pct = await cls.resolve_offering_threshold(db, university_id, offering)

            # Fetch student's records in closed sessions of this offering
            rec_stmt = (
                select(AttendanceRecord)
                .join(
                    AttendanceSession,
                    AttendanceRecord.attendance_session_id == AttendanceSession.id,
                )
                .join(ClassOccurrence, AttendanceSession.class_occurrence_id == ClassOccurrence.id)
                .where(
                    AttendanceRecord.student_id == student_id,
                    ClassOccurrence.course_offering_id == offering.id,
                    AttendanceSession.status == AttendanceSessionStatus.CLOSED.value,
                )
            )
            records = list((await db.execute(rec_stmt)).scalars().all())

            # Count total conducted sessions
            cond_count_stmt = (
                select(func.count(AttendanceSession.id))
                .join(ClassOccurrence, AttendanceSession.class_occurrence_id == ClassOccurrence.id)
                .where(
                    ClassOccurrence.course_offering_id == offering.id,
                    AttendanceSession.status == AttendanceSessionStatus.CLOSED.value,
                )
            )
            conducted = (await db.execute(cond_count_stmt)).scalar() or 0

            present_count = 0
            late_count = 0
            absent_count = 0
            excused_count = 0
            leave_count = 0
            has_revision = False
            total_credit = 0.0
            eligible_sessions = 0

            for r in records:
                if r.version_no > 1:
                    has_revision = True
                total_credit += float(r.attendance_credit)

                if r.status == AttendanceStatus.PRESENT.value:
                    present_count += 1
                    eligible_sessions += 1
                elif r.status == AttendanceStatus.LATE.value:
                    late_count += 1
                    eligible_sessions += 1
                elif r.status == AttendanceStatus.ABSENT.value:
                    absent_count += 1
                    eligible_sessions += 1
                elif r.status == AttendanceStatus.EXCUSED.value:
                    excused_count += 1
                    eligible_sessions += 1
                elif r.status == AttendanceStatus.LEAVE.value:
                    leave_count += 1
                else:
                    eligible_sessions += 1

            if eligible_sessions > 0:
                calc_pct = round((total_credit / eligible_sessions) * 100.0, 1)
                pct = min(100.0, max(0.0, calc_pct))
            else:
                pct = 100.0

            total_pct_sum += pct
            th_status = cls.evaluate_threshold(pct, threshold_pct, cls.DEFAULT_MARGIN)
            if th_status == ThresholdStatus.BELOW_THRESHOLD:
                below_count += 1

            course_items.append(
                {
                    "course_offering_id": offering.id,
                    "course_code": offering.course.code if offering.course else "",
                    "course_name": offering.course.name if offering.course else "",
                    "semester_code": offering.semester.code if offering.semester else "",
                    "section_code": offering.section.code if offering.section else None,
                    "total_sessions_conducted": conducted,
                    "eligible_sessions": eligible_sessions,
                    "attendance_credit": round(total_credit, 2),
                    "attendance_percentage": pct,
                    "present_count": present_count,
                    "late_count": late_count,
                    "absent_count": absent_count,
                    "excused_count": excused_count,
                    "leave_count": leave_count,
                    "has_revision": has_revision,
                    "threshold_percentage": threshold_pct,
                    "threshold_status": th_status.value,
                }
            )

        overall_avg = (
            round(total_pct_sum / len(course_items), 1) if len(course_items) > 0 else 100.0
        )

        return {
            "student_id": student.id,
            "student_number": student.student_number,
            "student_name": student.user.username if student.user else "Student",
            "generated_at_utc": utc_now(),
            "courses": course_items,
            "overall_average_percentage": overall_avg,
            "below_threshold_count": below_count,
        }

    @classmethod
    async def get_session_report(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Generate operational summary and checkpoint statistics for an attendance session."""
        stmt = (
            select(AttendanceSession)
            .options(
                selectinload(AttendanceSession.class_occurrence)
                .selectinload(ClassOccurrence.course_offering)
                .selectinload(CourseOffering.course),
                selectinload(AttendanceSession.class_occurrence)
                .selectinload(ClassOccurrence.course_offering)
                .selectinload(CourseOffering.semester),
                selectinload(AttendanceSession.class_occurrence)
                .selectinload(ClassOccurrence.course_offering)
                .selectinload(CourseOffering.section),
                selectinload(AttendanceSession.class_occurrence)
                .selectinload(ClassOccurrence.lecturer)
                .selectinload(Lecturer.user),
                selectinload(AttendanceSession.class_occurrence)
                .selectinload(ClassOccurrence.room)
                .selectinload(Room.building),
                selectinload(AttendanceSession.records),
            )
            .where(
                AttendanceSession.id == session_id,
                AttendanceSession.university_id == university_id,
            )
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise NotFoundException("AttendanceSession", session_id)

        occ = session.class_occurrence
        offering = occ.course_offering if occ else None
        lecturer = occ.lecturer if occ else None
        room = occ.room if occ else None

        records = session.records or []
        roster_count = len(records)
        start_credited = 0
        middle_credited = 0
        end_credited = 0
        present_count = 0
        late_count = 0
        absent_count = 0
        excused_count = 0
        leave_count = 0
        manual_count = 0
        offline_count = 0
        revision_count = 0

        for r in records:
            if r.start_credited:
                start_credited += 1
            if r.middle_credited:
                middle_credited += 1
            if r.end_credited:
                end_credited += 1

            if r.is_manual:
                manual_count += 1
            if r.version_no > 1:
                revision_count += 1

            if r.calculation_snapshot and r.calculation_snapshot.get("offline_created"):
                offline_count += 1

            if r.status == AttendanceStatus.PRESENT.value:
                present_count += 1
            elif r.status == AttendanceStatus.LATE.value:
                late_count += 1
            elif r.status == AttendanceStatus.ABSENT.value:
                absent_count += 1
            elif r.status == AttendanceStatus.EXCUSED.value:
                excused_count += 1
            elif r.status == AttendanceStatus.LEAVE.value:
                leave_count += 1

        return {
            "session_id": session.id,
            "occurrence_id": occ.id if occ else uuid.uuid4(),
            "course_code": offering.course.code if (offering and offering.course) else "",
            "course_name": offering.course.name if (offering and offering.course) else "",
            "semester_code": offering.semester.code if (offering and offering.semester) else "",
            "section_code": offering.section.code if (offering and offering.section) else None,
            "lecturer_code": lecturer.employee_code if lecturer else None,
            "lecturer_name": lecturer.user.username if (lecturer and lecturer.user) else None,
            "room_number": room.room_number if room else None,
            "building_code": room.building.code if (room and room.building) else None,
            "opened_at_utc": session.opened_at_utc,
            "closed_at_utc": session.closed_at_utc,
            "status": session.status,
            "roster_count": roster_count,
            "start_credited_count": start_credited,
            "middle_credited_count": middle_credited,
            "end_credited_count": end_credited,
            "present_count": present_count,
            "late_count": late_count,
            "absent_count": absent_count,
            "excused_count": excused_count,
            "leave_count": leave_count,
            "manual_count": manual_count,
            "offline_count": offline_count,
            "revision_count": revision_count,
            "network_presence_mode": session.policy_snapshot.get(
                "network_presence_mode", "DISABLED"
            ),
            "host_type": session.host_type,
            "generated_at_utc": utc_now(),
        }

    @classmethod
    async def get_department_report(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        academic_unit_id: uuid.UUID,
        semester_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Aggregate attendance metrics across all active course offerings in a department."""
        unit = await db.get(AcademicUnit, academic_unit_id)
        if not unit or unit.university_id != university_id:
            raise NotFoundException("AcademicUnit", academic_unit_id)

        # Query all course offerings hosted by this unit or its courses
        off_stmt = (
            select(CourseOffering)
            .join(Course, CourseOffering.course_id == Course.id)
            .options(
                selectinload(CourseOffering.course),
                selectinload(CourseOffering.semester),
                selectinload(CourseOffering.section),
            )
            .where(
                CourseOffering.university_id == university_id,
                (CourseOffering.academic_unit_id == academic_unit_id)
                | (Course.academic_unit_id == academic_unit_id),
            )
        )
        if semester_id:
            off_stmt = off_stmt.where(CourseOffering.semester_id == semester_id)

        offerings = list((await db.execute(off_stmt)).scalars().all())

        offering_summaries: list[dict[str, Any]] = []
        total_enrolled = 0
        total_courses_set: set[uuid.UUID] = set()
        pct_sum = 0.0
        dept_below_count = 0
        dept_near_count = 0
        dept_above_count = 0

        for off in offerings:
            if off.course_id:
                total_courses_set.add(off.course_id)

            report = await cls.get_course_roster_report(
                db=db,
                university_id=university_id,
                course_offering_id=off.id,
                page_size=1000,
            )

            off_enrolled = report["total_enrolled"]
            total_enrolled += off_enrolled
            avg_pct = report["average_attendance_percentage"]
            pct_sum += avg_pct * off_enrolled if off_enrolled > 0 else 0.0

            dept_below_count += report["below_threshold_count"]
            dept_near_count += report["near_threshold_count"]
            dept_above_count += report["above_threshold_count"]

            offering_summaries.append(
                {
                    "course_offering_id": off.id,
                    "course_code": report["course_code"],
                    "course_name": report["course_name"],
                    "semester_code": report["semester_code"],
                    "section_code": report["section_code"],
                    "enrolled_count": off_enrolled,
                    "conducted_sessions_count": report["total_sessions_conducted"],
                    "average_attendance_percentage": avg_pct,
                    "below_threshold_count": report["below_threshold_count"],
                    "near_threshold_count": report["near_threshold_count"],
                }
            )

        dept_avg = (
            round(pct_sum / total_enrolled, 1)
            if total_enrolled > 0
            else (
                round(
                    sum(o["average_attendance_percentage"] for o in offering_summaries)
                    / len(offering_summaries),
                    1,
                )
                if offering_summaries
                else 100.0
            )
        )

        return {
            "academic_unit_id": unit.id,
            "academic_unit_code": unit.code,
            "academic_unit_name": unit.name,
            "total_courses": len(total_courses_set),
            "total_offerings": len(offerings),
            "total_students_enrolled": total_enrolled,
            "department_average_percentage": dept_avg,
            "below_threshold_count": dept_below_count,
            "near_threshold_count": dept_near_count,
            "above_threshold_count": dept_above_count,
            "generated_at_utc": utc_now(),
            "offerings": offering_summaries,
        }

    @classmethod
    async def get_faculty_report(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        faculty_id: uuid.UUID,
        semester_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Aggregate attendance metrics across all child departments in a faculty."""
        fac = await db.get(AcademicUnit, faculty_id)
        if not fac or fac.university_id != university_id:
            raise NotFoundException("AcademicUnit", faculty_id)

        # Get all child departments
        child_stmt = select(AcademicUnit).where(
            AcademicUnit.parent_id == faculty_id,
            AcademicUnit.university_id == university_id,
        )
        departments = list((await db.execute(child_stmt)).scalars().all())

        dept_summaries: list[dict[str, Any]] = []
        total_students = 0
        total_pct_sum = 0.0
        fac_below = 0
        fac_near = 0
        fac_above = 0

        for d in departments:
            d_rep = await cls.get_department_report(
                db=db,
                university_id=university_id,
                academic_unit_id=d.id,
                semester_id=semester_id,
            )
            d_students = d_rep["total_students_enrolled"]
            total_students += d_students
            total_pct_sum += d_rep["department_average_percentage"] * d_students

            fac_below += d_rep["below_threshold_count"]
            fac_near += d_rep["near_threshold_count"]
            fac_above += d_rep["above_threshold_count"]
            dept_summaries.append(d_rep)

        fac_avg = (
            round(total_pct_sum / total_students, 1)
            if total_students > 0
            else (
                round(
                    sum(d["department_average_percentage"] for d in dept_summaries)
                    / len(dept_summaries),
                    1,
                )
                if dept_summaries
                else 100.0
            )
        )

        return {
            "academic_unit_id": fac.id,
            "academic_unit_code": fac.code,
            "academic_unit_name": fac.name,
            "total_departments": len(departments),
            "total_students": total_students,
            "faculty_average_percentage": fac_avg,
            "below_threshold_count": fac_below,
            "near_threshold_count": fac_near,
            "above_threshold_count": fac_above,
            "generated_at_utc": utc_now(),
            "departments": dept_summaries,
        }

    @classmethod
    async def get_lecturer_report(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        lecturer_id: uuid.UUID,
        semester_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Neutral operational summary of scheduled and conducted sessions for an instructor."""
        l_stmt = (
            select(Lecturer)
            .options(selectinload(Lecturer.user))
            .where(
                Lecturer.id == lecturer_id,
                Lecturer.university_id == university_id,
            )
        )
        lecturer = (await db.execute(l_stmt)).scalar_one_or_none()
        if not lecturer:
            raise NotFoundException("Lecturer", lecturer_id)

        # Occurrences assigned to lecturer
        occ_stmt = select(ClassOccurrence).where(
            ClassOccurrence.lecturer_id == lecturer_id,
            ClassOccurrence.university_id == university_id,
        )
        if semester_id:
            occ_stmt = occ_stmt.join(
                CourseOffering, ClassOccurrence.course_offering_id == CourseOffering.id
            ).where(CourseOffering.semester_id == semester_id)

        occurrences = list((await db.execute(occ_stmt)).scalars().all())
        scheduled_count = len(occurrences)

        # Conducted sessions
        sess_stmt = (
            select(AttendanceSession)
            .join(ClassOccurrence, AttendanceSession.class_occurrence_id == ClassOccurrence.id)
            .options(selectinload(AttendanceSession.records))
            .where(
                ClassOccurrence.lecturer_id == lecturer_id,
                AttendanceSession.university_id == university_id,
                AttendanceSession.status == AttendanceSessionStatus.CLOSED.value,
            )
        )
        sessions = list((await db.execute(sess_stmt)).scalars().all())
        conducted_count = len(sessions)

        manual_count = 0
        offline_count = 0
        revision_count = 0

        for s in sessions:
            for r in s.records:
                if r.is_manual:
                    manual_count += 1
                if r.version_no > 1:
                    revision_count += 1
                if r.calculation_snapshot and r.calculation_snapshot.get("offline_created"):
                    offline_count += 1

        return {
            "lecturer_id": lecturer.id,
            "employee_code": lecturer.employee_code,
            "lecturer_name": lecturer.user.username if lecturer.user else "Lecturer",
            "sessions_scheduled": scheduled_count,
            "sessions_conducted": conducted_count,
            "manual_attendance_count": manual_count,
            "offline_sessions_count": offline_count,
            "revision_count": revision_count,
            "generated_at_utc": utc_now(),
        }
