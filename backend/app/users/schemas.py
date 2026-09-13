"""Pydantic schemas for user account management."""

import uuid

from pydantic import BaseModel, Field

from backend.app.common.types import UTCDateTime


class CreateUserRequest(BaseModel):
    """Payload to create a new institutional user identity."""

    username: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    preferred_language: str = Field(default="en", max_length=10)
    must_change_password: bool = Field(default=False)


class UserDetailResponse(BaseModel):
    """Detailed user account view."""

    id: uuid.UUID
    university_id: uuid.UUID
    username: str
    email: str | None = None
    phone: str | None = None
    preferred_language: str
    status: str
    must_change_password: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime
    last_login_at: UTCDateTime | None = None


class AdminResetPasswordRequest(BaseModel):
    """Administrative password reset payload."""

    new_password: str = Field(..., min_length=8, max_length=128)


class DisableUserRequest(BaseModel):
    """Optional parameters for disabling a user account."""

    reason: str | None = Field(default=None, max_length=255)
