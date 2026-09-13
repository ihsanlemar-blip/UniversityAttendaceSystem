import uuid
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


def require_permission(
    permission_code: str,
    allow_scoped: bool = False,
) -> Callable[..., Awaitable[User]]:
    """Dependency factory enforcing that current user holds specific scoped permission.

    Enforces deny-by-default: If the user lacks an active assignment granting the permission
    within the active university scope, returns HTTP 403 PERMISSION_DENIED.
    If allow_scoped is True, role assignments at ACADEMIC_UNIT scope are also admitted
    (for subsequent fine-grained endpoint subtree validation).
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
            allow_scoped=allow_scoped,
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


def require_academic_unit_permission(permission_code: str) -> Callable[..., Awaitable[User]]:
    """Dependency factory enforcing that current user holds permission for a specific academic unit.

    Resolves `unit_id` from route parameters. Checks whether the user holds permission
    at the UNIVERSITY level or at an ACADEMIC_UNIT level matching unit_id or one of its ancestors.
    """

    async def _unit_permission_checker(
        unit_id: uuid.UUID,
        user: Annotated[User, Depends(get_current_active_user)],
        db: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        has_perm = await RbacService.has_academic_unit_permission(
            db=db,
            user_id=user.id,
            permission_code=permission_code,
            university_id=user.university_id,
            target_unit_id=unit_id,
        )

        if not has_perm:
            log_security_event(
                "PERMISSION_DENIED",
                user_id=user.id,
                university_id=user.university_id,
                details={
                    "required_permission": permission_code,
                    "target_unit_id": str(unit_id),
                },
            )
            raise DomainException(
                code="PERMISSION_DENIED",
                message=f"Permission '{permission_code}' is required for this academic unit.",
                status_code=403,
            )

        return user

    return _unit_permission_checker
