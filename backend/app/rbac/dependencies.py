"""RBAC authorization dependencies for enforcing granular permission gates."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_active_user
from backend.app.auth.security import log_security_event
from backend.app.core.database import get_db_session
from backend.app.core.exceptions import DomainException
from backend.app.models.user import User
from backend.app.rbac.service import RbacService


def require_permission(permission_code: str) -> Callable[..., Awaitable[User]]:
    """Dependency factory enforcing that current user holds specific scoped permission.

    Enforces deny-by-default: If the user lacks an active assignment granting the permission
    within the active university scope, returns HTTP 403 PERMISSION_DENIED.
    """

    async def _permission_checker(
        user: Annotated[User, Depends(get_current_active_user)],
        db: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        has_perm = await RbacService.has_permission(
            db=db,
            user_id=user.id,
            permission_code=permission_code,
            university_id=user.university_id,
        )

        if not has_perm:
            log_security_event(
                "PERMISSION_DENIED",
                user_id=user.id,
                university_id=user.university_id,
                details={"required_permission": permission_code},
            )
            raise DomainException(
                code="PERMISSION_DENIED",
                message=f"Permission '{permission_code}' is required to access this resource.",
                status_code=403,
            )

        return user

    return _permission_checker
