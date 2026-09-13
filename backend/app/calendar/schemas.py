"""Schemas for academic years and semester calendar sessions."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AcademicYearCreateRequest(BaseModel):
    """Payload for creating an academic year."""

    name: str = Field(min_length=1, max_length=100, description="Display name e.g. 2026-2027")
    code: str = Field(min_length=1, max_length=50, description="Unique code e.g. AY-2026-2027")
    start_date: date = Field(description="Start date of the academic year")
    end_date: date = Field(description="End date of the academic year")
    is_current: bool = Field(default=False, description="Flag indicating active institutional year")


class AcademicYearUpdateRequest(BaseModel):
    """Payload for updating an academic year."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    start_date: date | None = None
    end_date: date | None = None


class AcademicYearResponse(BaseModel):
    """Standard representation of an academic year."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    name: str
    code: str
    start_date: date
    end_date: date
    is_current: bool
    status: str
    created_at: datetime
    updated_at: datetime


class SemesterCreateRequest(BaseModel):
    """Payload for creating a semester calendar session."""

    academic_year_id: uuid.UUID = Field(description="Parent academic year ID")
    name: str = Field(min_length=1, max_length=100, description="Display name e.g. Fall 2026")
    code: str = Field(min_length=1, max_length=50, description="Unique code within academic year")
    sequence_order: int = Field(
        default=1, ge=1, description="Deterministic term sequence (1, 2, ...)"
    )
    start_date: date = Field(description="Start date of the semester")
    end_date: date = Field(description="End date of the semester")
    is_current: bool = Field(default=False, description="Flag indicating active semester")


class SemesterUpdateRequest(BaseModel):
    """Payload for updating a semester."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    sequence_order: int | None = Field(default=None, ge=1)
    start_date: date | None = None
    end_date: date | None = None


class SemesterResponse(BaseModel):
    """Standard representation of a semester."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    code: str
    sequence_order: int
    start_date: date
    end_date: date
    is_current: bool
    status: str
    created_at: datetime
    updated_at: datetime


class AcademicYearDetailResponse(AcademicYearResponse):
    """Academic year details with embedded semester list."""

    semesters: list[SemesterResponse] = Field(default_factory=list)
