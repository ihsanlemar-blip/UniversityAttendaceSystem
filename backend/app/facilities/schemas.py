"""Pydantic schemas for campus Building and Room facilities."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import BuildingStatus, RoomStatus, RoomType

# --- Building Schemas ---


class BuildingCreateRequest(BaseModel):
    """Payload to register a new campus building."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Institutional building code (e.g. MAIN, ENG-A)",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Official building name (e.g. Main Academic Complex)",
    )


class BuildingUpdateRequest(BaseModel):
    """Payload to update an existing campus building."""

    name: str | None = Field(None, min_length=1, max_length=255)
    status: BuildingStatus | None = None


class BuildingResponse(BaseModel):
    """Standard representation of a campus building."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    code: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


# --- Room Schemas ---


class RoomCreateRequest(BaseModel):
    """Payload to register a new room or classroom facility."""

    building_id: uuid.UUID = Field(..., description="Target campus building ID")
    room_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Room identifier within the building (e.g. 101, A-202, LAB-3)",
    )
    name: str | None = Field(
        None,
        max_length=255,
        description="Descriptive room name (e.g. Central Auditorium)",
    )
    capacity: int | None = Field(
        None,
        gt=0,
        description="Maximum seating capacity of the room",
    )
    room_type: str = Field(
        default=RoomType.CLASSROOM.value,
        description="Room classification type (CLASSROOM, LABORATORY, LECTURE_HALL, etc.)",
    )
    floor: str | None = Field(
        None,
        max_length=20,
        description="Floor designation (e.g. 1st Floor, Basement)",
    )


class RoomUpdateRequest(BaseModel):
    """Payload to update an existing room facility."""

    room_number: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, max_length=255)
    capacity: int | None = Field(None, gt=0)
    room_type: str | None = None
    floor: str | None = Field(None, max_length=20)
    status: RoomStatus | None = None


class RoomResponse(BaseModel):
    """Standard representation of a room facility."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    building_id: uuid.UUID
    room_number: str
    name: str | None
    capacity: int | None
    room_type: str
    floor: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class RoomDetailResponse(RoomResponse):
    """Detailed room representation including building metadata."""

    building_name: str | None = None
    building_code: str | None = None
