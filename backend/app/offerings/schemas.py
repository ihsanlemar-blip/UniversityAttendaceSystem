"""Pydantic schemas for Course Offering, Lecturer Assignment, and Enrollment management."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import (
    LecturerAssignmentType,
    OfferingStatus,
)

# --- Lecturer Assignment Schemas ---


class LecturerAssignmentCreateRequest(BaseModel):
    """Payload to assign an instructor to a course offering."""

    lecturer_id: uuid.UUID = Field(..., description="Instructor ID to assign")
    is_primary: bool = Field(True, description="Whether this instructor is the primary course lead")
    assignment_type: LecturerAssignmentType = Field(
        LecturerAssignmentType.PRIMARY, description="Role: PRIMARY, CO_TEACHER, or ASSISTANT"
    )


class LecturerAssignmentResponse(BaseModel):
    """Representation of an assigned lecturer for an offering."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_offering_id: uuid.UUID
    lecturer_id: uuid.UUID
    is_primary: bool
    assignment_type: str
    status: str
    lecturer_name: str | None = None
    employee_code: str | None = None


# --- Course Offering Schemas ---


class CourseOfferingCreateRequest(BaseModel):
    """Payload to schedule a semester course offering instance."""

    course_id: uuid.UUID = Field(..., description="Master catalog course ID")
    semester_id: uuid.UUID = Field(..., description="Semester session ID")
    section_id: uuid.UUID | None = Field(None, description="Optional target student cohort section")
    academic_unit_id: uuid.UUID | None = Field(
        None, description="Academic unit offering this section (defaults to course unit if omitted)"
    )


class CourseOfferingUpdateRequest(BaseModel):
    """Payload to update an offering instance."""

    section_id: uuid.UUID | None = None
    academic_unit_id: uuid.UUID | None = None
    status: OfferingStatus | None = None


class CourseOfferingResponse(BaseModel):
    """Standard representation of a course offering."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    course_id: uuid.UUID
    semester_id: uuid.UUID
    section_id: uuid.UUID | None
    academic_unit_id: uuid.UUID | None
    status: str
    created_at: datetime
    updated_at: datetime


class CourseOfferingDetailResponse(CourseOfferingResponse):
    """Detailed course offering representation with related catalog and roster info."""

    course_code: str | None = None
    course_name: str | None = None
    semester_name: str | None = None
    section_code: str | None = None
    section_name: str | None = None
    assigned_lecturers: list[LecturerAssignmentResponse] = []
    enrolled_count: int = 0


# --- Enrollment Schemas ---


class EnrollmentCreateRequest(BaseModel):
    """Payload to enroll a single student into a course offering."""

    student_id: uuid.UUID = Field(..., description="Student profile ID")


class BatchEnrollmentRequest(BaseModel):
    """Payload to enroll multiple students into a course offering."""

    student_ids: list[uuid.UUID] = Field(..., min_length=1, description="List of student IDs")


class EnrollmentResponse(BaseModel):
    """Standard representation of an enrollment record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    course_offering_id: uuid.UUID
    student_id: uuid.UUID
    status: str
    enrolled_at: datetime
    dropped_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RosterItemResponse(EnrollmentResponse):
    """Class roster item with student details."""

    student_number: str | None = None
    student_name: str | None = None
    email: str | None = None


class StudentEnrollmentDetailResponse(BaseModel):
    """Representation of an enrollment from the student's personal view."""

    model_config = ConfigDict(from_attributes=True)

    enrollment_id: uuid.UUID
    course_offering_id: uuid.UUID
    course_code: str
    course_name: str
    semester_name: str
    section_code: str | None
    status: str
    enrolled_at: datetime
    dropped_at: datetime | None
