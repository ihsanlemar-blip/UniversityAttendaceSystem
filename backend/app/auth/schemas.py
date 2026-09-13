"""Pydantic schemas for authentication requests and responses."""

import uuid

from pydantic import BaseModel, Field

from backend.app.common.types import UTCDateTime


class LoginRequest(BaseModel):
    """User credentials for authentication."""

    username: str = Field(..., min_length=1, max_length=50, description="Normalized username")
    password: str = Field(..., min_length=1, max_length=128, description="Plaintext password")
    university_id: uuid.UUID | None = Field(
        default=None,
        description="Target university ID. Defaults to active university in single-tenant setup.",
    )


class TokenResponse(BaseModel):
    """Issued access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiration window in seconds")


class UserSummary(BaseModel):
    """Authenticated user summary representation."""

    id: uuid.UUID
    university_id: uuid.UUID
    username: str
    email: str | None = None
    preferred_language: str
    status: str
    must_change_password: bool
    roles: list[str] = Field(default_factory=list)


class LoginResponse(BaseModel):
    """Successful authentication response envelope."""

    user: UserSummary
    tokens: TokenResponse


class TokenRefreshRequest(BaseModel):
    """Request envelope containing opaque refresh token."""

    refresh_token: str = Field(..., min_length=1, description="Raw refresh token")


class TokenRefreshResponse(BaseModel):
    """Token response on successful refresh rotation."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    """User request to update account password."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserMeResponse(BaseModel):
    """Detailed authenticated user profile with roles and effective permissions."""

    id: uuid.UUID
    university_id: uuid.UUID
    username: str
    email: str | None = None
    phone: str | None = None
    preferred_language: str
    status: str
    must_change_password: bool
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    last_login_at: UTCDateTime | None = None
