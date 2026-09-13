"""Schemas for academic units and organizational hierarchy."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import AcademicUnitType


class AcademicUnitCreateRequest(BaseModel):
    """Payload for registering an academic unit."""

    name: str = Field(min_length=1, max_length=255, description="Official name of the unit")
    code: str = Field(min_length=1, max_length=50, description="Unique code within university")
    unit_type: AcademicUnitType = Field(
        default=AcademicUnitType.FACULTY, description="Organizational unit classification"
    )
    parent_id: uuid.UUID | None = Field(
        default=None, description="Parent unit ID (omitted for root units)"
    )
    short_name: str | None = Field(
        default=None, max_length=50, description="Optional abbreviated name"
    )
    sort_order: int = Field(default=0, ge=0, description="Display sort ordering")


class AcademicUnitUpdateRequest(BaseModel):
    """Payload for updating an academic unit's attributes."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    unit_type: AcademicUnitType | None = None
    short_name: str | None = Field(default=None, max_length=50)
    sort_order: int | None = Field(default=None, ge=0)


class AcademicUnitMoveRequest(BaseModel):
    """Payload for reparenting an academic unit."""

    parent_id: uuid.UUID | None = Field(
        default=None, description="New parent unit ID, or null to make root"
    )


class AcademicUnitResponse(BaseModel):
    """Standard representation of an academic unit."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    parent_id: uuid.UUID | None
    unit_type: str
    code: str
    name: str
    short_name: str | None
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class AcademicUnitDetailResponse(AcademicUnitResponse):
    """Detailed representation of an academic unit with ancestry path."""

    parent: AcademicUnitResponse | None = None
    children_count: int = 0
    ancestor_path: list[AcademicUnitResponse] = Field(default_factory=list)


class AcademicUnitTreeNodeResponse(BaseModel):
    """Recursive hierarchy node for tree views."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    short_name: str | None
    unit_type: str
    status: str
    sort_order: int
    children: list[AcademicUnitTreeNodeResponse] = Field(default_factory=list)
