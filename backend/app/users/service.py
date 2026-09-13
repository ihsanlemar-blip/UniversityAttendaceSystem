"""User management domain service for account lifecycle operations."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import hash_password, validate_password_policy
from backend.app.auth.security import log_security_event
from backend.app.common.types import utc_now
from backend.app.core.constants import RevocationReason, UserStatus
from backend.app.core.exceptions import ConflictException, NotFoundException
from backend.app.models.refresh_session import RefreshSession
from backend.app.models.user import User


class UserService:
    """Service handling user account lifecycle and credentials."""

    @staticmethod
    async def create_user(
        db: AsyncSession,
        university_id: uuid.UUID,
        username: str,
        password: str,
        email: str | None = None,
        phone: str | None = None,
        preferred_language: str = "en",
        must_change_password: bool = False,
        creator_id: uuid.UUID | None = None,
    ) -> User:
        """Create new user account in target university."""
        normalized_username = username.strip().lower()

        # Check unique constraint (university_id, username)
        stmt = select(User).where(
            User.university_id == university_id,
            User.username == normalized_username,
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise ConflictException(
                f"Username '{normalized_username}' is already taken in this university.",
                details={"username": normalized_username},
            )

        validate_password_policy(password)
        pw_hash = hash_password(password)

        user = User(
            university_id=university_id,
            username=normalized_username,
            password_hash=pw_hash,
            email=email.strip().lower() if email else None,
            phone=phone.strip() if phone else None,
            preferred_language=preferred_language,
            status=UserStatus.ACTIVE.value,
            must_change_password=must_change_password,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        log_security_event(
            "USER_CREATED",
            user_id=user.id,
            university_id=university_id,
            details={"created_by": str(creator_id) if creator_id else None},
        )
        return user

    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> User:
        """Fetch user by ID enforcing tenant isolation."""
        stmt = select(User).where(User.id == user_id, User.university_id == university_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise NotFoundException("User", user_id)
        return user

    @staticmethod
    async def list_users(
        db: AsyncSession,
        university_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[User], int]:
        """Fetch paginated list of users in university."""
        count_stmt = select(func.count(User.id)).where(User.university_id == university_id)
        count_res = await db.execute(count_stmt)
        total = count_res.scalar_one()

        stmt = (
            select(User)
            .where(User.university_id == university_id)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        users = list(res.scalars().all())
        return users, total

    @staticmethod
    async def disable_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        university_id: uuid.UUID,
        disabled_by: uuid.UUID | None,
        reason: str | None = None,
    ) -> User:
        """Disable user account and revoke all active authentication sessions."""
        user = await UserService.get_user_by_id(db, user_id, university_id)
        user.status = UserStatus.DISABLED.value

        # Revoke all active sessions
        stmt_revoke = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user.id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(
                revoked_at=utc_now(),
                revocation_reason=RevocationReason.ADMIN_REVOKED.value,
            )
        )
        await db.execute(stmt_revoke)
        await db.commit()
        await db.refresh(user)

        log_security_event(
            "ACCOUNT_DISABLED",
            user_id=user.id,
            university_id=university_id,
            details={"disabled_by": str(disabled_by) if disabled_by else None, "reason": reason},
        )
        return user

    @staticmethod
    async def enable_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        university_id: uuid.UUID,
        enabled_by: uuid.UUID | None,
    ) -> User:
        """Re-enable disabled or locked user account."""
        user = await UserService.get_user_by_id(db, user_id, university_id)
        user.status = UserStatus.ACTIVE.value
        user.failed_login_attempts = 0
        user.locked_until = None

        await db.commit()
        await db.refresh(user)

        log_security_event(
            "ACCOUNT_ENABLED",
            user_id=user.id,
            university_id=university_id,
            details={"enabled_by": str(enabled_by) if enabled_by else None},
        )
        return user

    @staticmethod
    async def admin_reset_password(
        db: AsyncSession,
        user_id: uuid.UUID,
        university_id: uuid.UUID,
        new_password: str,
        reset_by: uuid.UUID | None,
    ) -> User:
        """Administratively reset user password, enforce must_change_password, and
        revoke sessions.
        """
        user = await UserService.get_user_by_id(db, user_id, university_id)
        validate_password_policy(new_password)

        now = utc_now()
        user.password_hash = hash_password(new_password)
        user.must_change_password = True
        user.password_changed_at = now
        user.failed_login_attempts = 0
        user.locked_until = None

        # Revoke all active sessions
        stmt_revoke = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user.id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(
                revoked_at=now,
                revocation_reason=RevocationReason.ADMIN_REVOKED.value,
            )
        )
        await db.execute(stmt_revoke)
        await db.commit()
        await db.refresh(user)

        log_security_event(
            "PASSWORD_RESET",
            user_id=user.id,
            university_id=university_id,
            details={"reset_by": str(reset_by) if reset_by else None},
        )
        return user
