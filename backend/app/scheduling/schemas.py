"""Pydantic schemas for Timetable recurring rules and ClassOccurrence meetings."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import TimetableStatus

# --- Timetable Schemas ---


class TimetableCreateRequest(BaseModel):
    """Payload to define a new recurring weekly timetable schedule rule."""

    course_offering_id: uuid.UUID = Field(..., description="Target course offering ID")
    room_id: uuid.UUID | None = Field(None, description="Optional designated room/facility ID")
    lecturer_id: uuid.UUID | None = Field(
        None, description="Optional designated instructor ID (must be assigned to offering)"
    )
    weekday: int = Field(
        ...,
        ge=1,
        le=7,
        description="ISO weekday index (1 = Monday, 2 = Tuesday, ..., 7 = Sunday)",
    )
    start_time: datetime.time = Field(..., description="Local session start time (HH:MM:SS)")
    end_time: datetime.time = Field(..., description="Local session end time (HH:MM:SS)")
    effective_from: datetime.date | None = Field(
        None, description="Optional start date for rule effectiveness"
    )
    effective_to: datetime.date | None = Field(
        None, description="Optional end date for rule effectiveness"
    )


class TimetableUpdateRequest(BaseModel):
    """Payload to update an existing recurring timetable schedule rule."""

    room_id: uuid.UUID | None = None
    lecturer_id: uuid.UUID | None = None
    weekday: int | None = Field(None, ge=1, le=7)
    start_time: datetime.time | None = None
    end_time: datetime.time | None = None
    effective_from: datetime.date | None = None
    effective_to: datetime.date | None = None
    status: TimetableStatus | None = None


class TimetableResponse(BaseModel):
    """Standard representation of a recurring weekly timetable rule."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    course_offering_id: uuid.UUID
    room_id: uuid.UUID | None
    lecturer_id: uuid.UUID | None
    weekday: int
    start_time: datetime.time
    end_time: datetime.time
    effective_from: datetime.date | None
    effective_to: datetime.date | None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class TimetableDetailResponse(TimetableResponse):
    """Detailed timetable rule representation with curriculum and room metadata."""

    course_name: str | None = None
    course_code: str | None = None
    section_name: str | None = None
    room_number: str | None = None
    building_name: str | None = None
    lecturer_name: str | None = None


# --- ClassOccurrence Schemas ---


class ClassOccurrenceResponse(BaseModel):
    """Standard representation of a concrete calendar class occurrence meeting."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    course_offering_id: uuid.UUID
    timetable_id: uuid.UUID | None
    room_id: uuid.UUID | None
    lecturer_id: uuid.UUID | None
    substitute_lecturer_id: uuid.UUID | None
    local_date: datetime.date
    scheduled_start_utc: datetime.datetime
    scheduled_end_utc: datetime.datetime
    status: str
    cancellation_reason: str | None
    rescheduled_from_id: uuid.UUID | None
    rescheduled_to_id: uuid.UUID | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ClassOccurrenceDetailResponse(ClassOccurrenceResponse):
    """Detailed concrete meeting representation with academic context."""

    course_name: str | None = None
    course_code: str | None = None
    section_name: str | None = None
    room_number: str | None = None
    building_name: str | None = None
    lecturer_name: str | None = None
    substitute_lecturer_name: str | None = None


class OccurrenceCancelRequest(BaseModel):
    """Payload to administratively cancel a scheduled class meeting."""

    reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Justification for cancelling the class occurrence",
    )


class OccurrenceRescheduleRequest(BaseModel):
    """Payload to reschedule a single concrete class meeting."""

    new_date: datetime.date = Field(..., description="Target rescheduled calendar date")
    new_start_time: datetime.time = Field(..., description="Target local session start time")
    new_end_time: datetime.time = Field(..., description="Target local session end time")
    new_room_id: uuid.UUID | None = Field(None, description="Optional changed room ID")
    substitute_lecturer_id: uuid.UUID | None = Field(
        None, description="Optional substitute lecturer ID"
    )
    reason: str | None = Field(
        None,
        max_length=500,
        description="Optional justification for rescheduling",
    )


class OccurrenceGenerationResponse(BaseModel):
    """Result report from deterministic occurrence generation."""

    timetable_id: uuid.UUID | None = None
    semester_id: uuid.UUID | None = None
    generated_count: int
    existing_count: int
    message: str
