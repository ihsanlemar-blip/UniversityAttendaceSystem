"""Pydantic schemas for Student and Lecturer academic profiles."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import LecturerStatus, StudentStatus

# --- Student Schemas ---


class StudentCreateRequest(BaseModel):
    """Payload to create a new student academic profile."""

    user_id: uuid.UUID = Field(..., description="User account ID to link profile to")
    student_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="University-unique student number / matriculation ID",
    )
    academic_unit_id: uuid.UUID | None = Field(
        None, description="Primary faculty or department placement"
    )
    section_id: uuid.UUID | None = Field(
        None, description="Assigned primary student cohort section"
    )
    admission_date: date | None = Field(None, description="Date of admission")


class StudentUpdateRequest(BaseModel):
    """Payload to update an existing student profile."""

    student_number: str | None = Field(None, min_length=1, max_length=50)
    academic_unit_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    admission_date: date | None = None
    status: StudentStatus | None = None


class StudentResponse(BaseModel):
    """Standard representation of a student profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    university_id: uuid.UUID
    student_number: str
    academic_unit_id: uuid.UUID | None
    section_id: uuid.UUID | None
    admission_date: date | None
    status: str
    created_at: datetime
    updated_at: datetime


class StudentDetailResponse(StudentResponse):
    """Detailed student profile representation with user and academic placement details."""

    username: str | None = None
    full_name: str | None = None
    email: str | None = None
    academic_unit_name: str | None = None
    section_name: str | None = None


# --- Lecturer Schemas ---


class LecturerCreateRequest(BaseModel):
    """Payload to create a new lecturer instructor profile."""

    user_id: uuid.UUID = Field(..., description="User account ID to link profile to")
    employee_code: str = Field(
        ..., min_length=1, max_length=50, description="University-unique employee / instructor code"
    )
    academic_unit_id: uuid.UUID | None = Field(
        None, description="Primary faculty or department affiliation"
    )
    title: str | None = Field(
        None, max_length=100, description="Academic title (e.g. Professor, Dr.)"
    )


class LecturerUpdateRequest(BaseModel):
    """Payload to update an existing lecturer profile."""

    employee_code: str | None = Field(None, min_length=1, max_length=50)
    academic_unit_id: uuid.UUID | None = None
    title: str | None = Field(None, max_length=100)
    status: LecturerStatus | None = None


class LecturerResponse(BaseModel):
    """Standard representation of a lecturer profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    university_id: uuid.UUID
    employee_code: str
    academic_unit_id: uuid.UUID | None
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class LecturerDetailResponse(LecturerResponse):
    """Detailed lecturer representation with user and department details."""

    username: str | None = None
    full_name: str | None = None
    email: str | None = None
    academic_unit_name: str | None = None
