"""Authentication API router for login, refresh, session revocation, and current user profile."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_token_payload, get_current_user
from backend.app.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserMeResponse,
)
from backend.app.auth.service import AuthService
from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import HEADER_REQUEST_ID
from backend.app.core.database import get_db_session
from backend.app.models.user import User
from backend.app.rbac.service import RbacService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=StandardResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="Authenticate credentials and issue session tokens",
)
async def login(
    request: Request,
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[LoginResponse]:
    """Authenticate user with normalized username and password."""
    request_id = getattr(request.state, "request_id", request.headers.get(HEADER_REQUEST_ID, ""))
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    login_data = await AuthService.login(
        db=db,
        username=credentials.username,
        password=credentials.password,
        university_id=credentials.university_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    return StandardResponse(data=login_data)


@router.post(
    "/refresh",
    response_model=StandardResponse[TokenRefreshResponse],
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue new access token",
)
async def refresh_token(
    request: Request,
    payload: TokenRefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[TokenRefreshResponse]:
    """Rotate refresh token. Enforces reuse detection across token family."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    token_data = await AuthService.refresh_token(
        db=db,
        raw_refresh_token=payload.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(data=token_data)


@router.post(
    "/logout",
    response_model=StandardResponse[dict[str, str]],
    status_code=status.HTTP_200_OK,
    summary="Revoke current authentication session",
)
async def logout(
    token_payload: Annotated[dict[str, Any], Depends(get_current_token_payload)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> StandardResponse[dict[str, str]]:
    """Revoke the refresh session backing the current access token."""
    session_id = uuid.UUID(token_payload["sid"])
    await AuthService.logout(db, session_id)
    return StandardResponse(data={"message": "Logged out successfully."})


@router.post(
    "/logout-all",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Revoke all active sessions for current user",
)
async def logout_all(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[dict[str, Any]]:
    """Revoke all active refresh sessions belonging to authenticated user."""
    revoked_count = await AuthService.logout_all(db, current_user.id)
    return StandardResponse(
        data={"message": f"Successfully revoked {revoked_count} active sessions."}
    )


@router.get(
    "/me",
    response_model=StandardResponse[UserMeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile and permissions",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[UserMeResponse]:
    """Return authenticated identity, active roles, and effective permission capabilities."""
    roles = await RbacService.get_user_roles(db, current_user.id)
    permissions = await RbacService.get_user_permissions(db, current_user.id)

    profile = UserMeResponse(
        id=current_user.id,
        university_id=current_user.university_id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        preferred_language=current_user.preferred_language,
        status=current_user.status,
        must_change_password=current_user.must_change_password,
        roles=roles,
        permissions=sorted(permissions),
        last_login_at=current_user.last_login_at,
    )

    return StandardResponse(data=profile)


@router.post(
    "/change-password",
    response_model=StandardResponse[dict[str, str]],
    status_code=status.HTTP_200_OK,
    summary="Change account password",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[dict[str, str]]:
    """Verify current password, apply new password, and revoke other active sessions."""
    await AuthService.change_password(
        db=db,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return StandardResponse(data={"message": "Password changed successfully."})
