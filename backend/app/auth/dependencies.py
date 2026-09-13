"""FastAPI authentication dependencies for protecting routes and inspecting user context."""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.tokens import decode_access_token
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import DomainException
from backend.app.models.refresh_session import RefreshSession
from backend.app.models.user import User


async def get_token_from_header(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Extract raw bearer token from Authorization header."""
    if not authorization:
        raise DomainException(
            code="UNAUTHENTICATED",
            message="Authorization header is required.",
            status_code=401,
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise DomainException(
            code="TOKEN_INVALID",
            message="Invalid Authorization header format. Expected 'Bearer <token>'.",
            status_code=401,
        )

    return parts[1]


async def get_current_token_payload(
    token: Annotated[str, Depends(get_token_from_header)],
) -> dict[str, Any]:
    """Decode and validate JWT access token claims."""
    return decode_access_token(token)


async def get_current_user(
    payload: Annotated[dict[str, Any], Depends(get_current_token_payload)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Verify session revocation status and fetch active authenticated user entity."""
    user_id = uuid.UUID(payload["sub"])
    session_id = uuid.UUID(payload["sid"])

    # 1. Validate session state (server-side authoritative session check)
    session = await db.get(RefreshSession, session_id)
    if not session or session.revoked_at is not None or session.is_expired:
        raise DomainException(
            code="SESSION_REVOKED",
            message="Authentication session has been revoked or expired. Please log in again.",
            status_code=401,
        )

    if session.user_id != user_id:
        raise DomainException(
            code="TOKEN_INVALID",
            message="Token session does not match user.",
            status_code=401,
        )

    # 2. Fetch user
    user = await db.get(User, user_id)
    if not user or user.status != "ACTIVE":
        raise DomainException(
            code="ACCOUNT_DISABLED",
            message="User account is inactive or disabled.",
            status_code=403,
        )

    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Enforce must_change_password restriction on regular routes."""
    if user.must_change_password:
        raise DomainException(
            code="PASSWORD_CHANGE_REQUIRED",
            message="You must change your password before continuing.",
            status_code=403,
        )
    return user
