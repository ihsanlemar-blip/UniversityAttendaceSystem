"""Pydantic schemas for Course catalog and Section cohort management."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import RecordStatus

# --- Course Schemas ---


class CourseCreateRequest(BaseModel):
    """Payload to register a new course in the curriculum catalog."""

    code: str = Field(
        ..., min_length=1, max_length=50, description="Unique course code (e.g. CS101)"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Full course title")
    academic_unit_id: uuid.UUID | None = Field(
        None, description="Department or Faculty offering this course"
    )
    credit_hours: int | None = Field(None, ge=0, le=30, description="Academic credit units")
    description: str | None = Field(
        None, max_length=1000, description="Course syllabus/description"
    )


class CourseUpdateRequest(BaseModel):
    """Payload to update an existing course catalog record."""

    name: str | None = Field(None, min_length=1, max_length=255)
    academic_unit_id: uuid.UUID | None = None
    credit_hours: int | None = Field(None, ge=0, le=30)
    description: str | None = Field(None, max_length=1000)
    status: RecordStatus | None = None


class CourseResponse(BaseModel):
    """Standard representation of a course catalog entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    academic_unit_id: uuid.UUID | None
    code: str
    name: str
    credit_hours: int | None
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class CourseDetailResponse(CourseResponse):
    """Detailed course representation including academic unit name."""

    academic_unit_name: str | None = None


# --- Section Schemas ---


class SectionCreateRequest(BaseModel):
    """Payload to register a new student section cohort."""

    code: str = Field(..., min_length=1, max_length=50, description="Section code (e.g. A, CS-01)")
    name: str = Field(..., min_length=1, max_length=100, description="Section descriptive name")
    academic_unit_id: uuid.UUID | None = Field(
        None, description="Owning academic department or faculty"
    )
    semester_id: uuid.UUID | None = Field(
        None, description="Semester calendar session this section belongs to"
    )


class SectionUpdateRequest(BaseModel):
    """Payload to update an existing section record."""

    name: str | None = Field(None, min_length=1, max_length=100)
    academic_unit_id: uuid.UUID | None = None
    semester_id: uuid.UUID | None = None
    status: RecordStatus | None = None


class SectionResponse(BaseModel):
    """Standard representation of a student section."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    academic_unit_id: uuid.UUID | None
    semester_id: uuid.UUID | None
    code: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class SectionDetailResponse(SectionResponse):
    """Detailed section representation including academic unit and semester names."""

    academic_unit_name: str | None = None
    semester_name: str | None = None
