"""Pydantic schemas for RBAC roles, permissions, and scoped assignments."""

import uuid

from pydantic import BaseModel, Field

from backend.app.common.types import UTCDateTime


class RoleResponse(BaseModel):
    """Role entity representation."""

    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    is_system: bool
    created_at: UTCDateTime


class CreateRoleRequest(BaseModel):
    """Schema for creating a custom university role."""

    code: str = Field(..., min_length=2, max_length=50, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class PermissionResponse(BaseModel):
    """Permission capability representation."""

    id: uuid.UUID
    code: str
    description: str


class RolePermissionUpdateRequest(BaseModel):
    """Schema for setting permissions assigned to a role."""

    permission_ids: list[uuid.UUID] = Field(..., description="Complete set of permission UUIDs")


class RoleAssignmentResponse(BaseModel):
    """User role assignment representation."""

    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    university_id: uuid.UUID
    scope_type: str
    scope_id: uuid.UUID
    assigned_at: UTCDateTime
    assigned_by: uuid.UUID | None = None
    revoked_at: UTCDateTime | None = None
    revoked_by: uuid.UUID | None = None
    revocation_reason: str | None = None


class CreateRoleAssignmentRequest(BaseModel):
    """Request payload to assign a role to a user."""

    role_id: uuid.UUID
    scope_type: str = Field(default="UNIVERSITY")
    scope_id: uuid.UUID | None = None


class RevokeRoleAssignmentRequest(BaseModel):
    """Optional payload when revoking a role assignment."""

    reason: str | None = Field(default=None, max_length=255)
