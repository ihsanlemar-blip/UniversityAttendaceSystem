"""User account management API router."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.pagination import PaginatedResponse
from backend.app.common.schemas import StandardResponse
from backend.app.core.database import get_db_session
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission
from backend.app.users.schemas import (
    AdminResetPasswordRequest,
    CreateUserRequest,
    DisableUserRequest,
    UserDetailResponse,
)
from backend.app.users.service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


@router.post(
    "",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create new user account",
)
async def create_user(
    payload: CreateUserRequest,
    current_user: Annotated[User, Depends(require_permission("users.create"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[UserDetailResponse]:
    """Create a new user account within current university."""
    user = await UserService.create_user(
        db=db,
        university_id=current_user.university_id,
        username=payload.username,
        password=payload.password,
        email=payload.email,
        phone=payload.phone,
        preferred_language=payload.preferred_language,
        must_change_password=payload.must_change_password,
        creator_id=current_user.id,
    )
    return StandardResponse(data=UserDetailResponse.model_validate(user, from_attributes=True))


@router.get(
    "",
    response_model=PaginatedResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="List users in university",
)
async def list_users(
    current_user: Annotated[User, Depends(require_permission("users.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedResponse[UserDetailResponse]:
    """Fetch paginated list of users in current university scope."""
    users, total = await UserService.list_users(
        db=db,
        university_id=current_user.university_id,
        skip=skip,
        limit=limit,
    )
    items = [UserDetailResponse.model_validate(u, from_attributes=True) for u in users]
    return PaginatedResponse.create(
        items=items, total=total, page=(skip // limit) + 1, page_size=limit
    )


@router.get(
    "/{user_id}",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user account details",
)
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("users.read"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[UserDetailResponse]:
    """Fetch single user account enforcing tenant isolation."""
    user = await UserService.get_user_by_id(db, user_id, current_user.university_id)
    return StandardResponse(data=UserDetailResponse.model_validate(user, from_attributes=True))


@router.post(
    "/{user_id}/disable",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Disable user account and revoke active sessions",
)
async def disable_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("users.disable"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    payload: DisableUserRequest | None = None,
) -> StandardResponse[UserDetailResponse]:
    """Disable user account and revoke all active sessions."""
    reason = payload.reason if payload else None
    user = await UserService.disable_user(
        db=db,
        user_id=user_id,
        university_id=current_user.university_id,
        disabled_by=current_user.id,
        reason=reason,
    )
    return StandardResponse(data=UserDetailResponse.model_validate(user, from_attributes=True))


@router.post(
    "/{user_id}/enable",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Re-enable user account",
)
async def enable_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("users.enable"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[UserDetailResponse]:
    """Re-enable a disabled or locked user account."""
    user = await UserService.enable_user(
        db=db,
        user_id=user_id,
        university_id=current_user.university_id,
        enabled_by=current_user.id,
    )
    return StandardResponse(data=UserDetailResponse.model_validate(user, from_attributes=True))


@router.post(
    "/{user_id}/reset-password",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Administratively reset user password",
)
async def admin_reset_password(
    user_id: uuid.UUID,
    payload: AdminResetPasswordRequest,
    current_user: Annotated[User, Depends(require_permission("users.reset_password"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> StandardResponse[UserDetailResponse]:
    """Reset user password, enforce must_change_password=True, and revoke active sessions."""
    user = await UserService.admin_reset_password(
        db=db,
        user_id=user_id,
        university_id=current_user.university_id,
        new_password=payload.new_password,
        reset_by=current_user.id,
    )
    return StandardResponse(data=UserDetailResponse.model_validate(user, from_attributes=True))
