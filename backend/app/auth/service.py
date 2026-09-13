"""Authentication service implementing secure login, session rotation, and logout."""

import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import hash_password, validate_password_policy, verify_password
from backend.app.auth.schemas import (
    LoginResponse,
    TokenRefreshResponse,
    TokenResponse,
    UserSummary,
)
from backend.app.auth.security import log_security_event
from backend.app.auth.tokens import (
    TokenExpiredException,
    TokenInvalidException,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from backend.app.common.types import utc_now, uuid7
from backend.app.core.config import get_settings
from backend.app.core.constants import RevocationReason, UserStatus
from backend.app.core.exceptions import DomainException, ValidationException
from backend.app.models.login_attempt import LoginAttempt
from backend.app.models.refresh_session import RefreshSession
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.rbac.service import RbacService


class AuthService:
    """Core authentication domain service."""

    @staticmethod
    async def login(
        db: AsyncSession,
        username: str,
        password: str,
        university_id: uuid.UUID | None,
        ip_address: str | None,
        user_agent: str | None,
        request_id: str,
    ) -> LoginResponse:
        """Authenticate user credentials and issue session tokens.

        Guarantees enumeration prevention by returning generic 'Invalid credentials.'
        """
        settings = get_settings()
        normalized_username = username.strip().lower()

        # Resolve university
        if university_id:
            target_uni = await db.get(University, university_id)
        else:
            # Single-university default
            stmt_uni = select(University).limit(1)
            res_uni = await db.execute(stmt_uni)
            target_uni = res_uni.scalar_one_or_none()

        if not target_uni:
            raise DomainException(
                code="INVALID_CREDENTIALS",
                message="Invalid credentials.",
                status_code=401,
            )

        # Look up user
        stmt_user = select(User).where(
            User.university_id == target_uni.id,
            User.username == normalized_username,
        )
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()

        if not user:
            # Record failed login attempt and log security event
            attempt = LoginAttempt(
                university_id=target_uni.id,
                user_id=None,
                normalized_username=normalized_username,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason_internal="USER_NOT_FOUND",
            )
            db.add(attempt)
            await db.commit()
            log_security_event(
                "LOGIN_FAILURE",
                university_id=target_uni.id,
                details={"username": normalized_username, "reason": "USER_NOT_FOUND"},
            )
            raise DomainException(
                code="INVALID_CREDENTIALS",
                message="Invalid credentials.",
                status_code=401,
            )

        # Check account status
        if user.status == UserStatus.DISABLED.value:
            log_security_event(
                "LOGIN_FAILURE",
                user_id=user.id,
                university_id=target_uni.id,
                details={"reason": "ACCOUNT_DISABLED"},
            )
            raise DomainException(
                code="ACCOUNT_DISABLED",
                message="Account is disabled. Contact your administrator.",
                status_code=403,
            )

        now = utc_now()
        # Check lockout expiry
        if user.locked_until and user.locked_until > now:
            log_security_event(
                "LOGIN_FAILURE",
                user_id=user.id,
                university_id=target_uni.id,
                details={"reason": "ACCOUNT_LOCKED", "locked_until": user.locked_until.isoformat()},
            )
            raise DomainException(
                code="ACCOUNT_LOCKED",
                message="Account is temporarily locked due to excessive failed attempts.",
                status_code=403,
            )

        # Verify password
        is_valid, updated_hash = verify_password(password, user.password_hash)
        if not is_valid:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.AUTH_MAX_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.AUTH_LOCKOUT_DURATION_MINUTES)
                log_security_event(
                    "ACCOUNT_LOCKED",
                    user_id=user.id,
                    university_id=target_uni.id,
                    details={"attempts": user.failed_login_attempts},
                )

            attempt = LoginAttempt(
                university_id=target_uni.id,
                user_id=user.id,
                normalized_username=normalized_username,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason_internal="PASSWORD_MISMATCH",
            )
            db.add(attempt)
            await db.commit()
            log_security_event(
                "LOGIN_FAILURE",
                user_id=user.id,
                university_id=target_uni.id,
                details={"reason": "PASSWORD_MISMATCH"},
            )
            raise DomainException(
                code="INVALID_CREDENTIALS",
                message="Invalid credentials.",
                status_code=401,
            )

        # Transparently upgrade hash if algorithm parameters have updated
        if updated_hash:
            user.password_hash = updated_hash

        # Reset failed attempts and clear lockout
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now

        # Record successful attempt
        attempt = LoginAttempt(
            university_id=target_uni.id,
            user_id=user.id,
            normalized_username=normalized_username,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            failure_reason_internal=None,
        )
        db.add(attempt)

        # Generate refresh session
        raw_refresh_token, token_hash = generate_refresh_token()
        session_id = uuid7()
        family_id = uuid7()
        refresh_expires = now + timedelta(days=settings.AUTH_REFRESH_TOKEN_DAYS)

        session = RefreshSession(
            id=session_id,
            user_id=user.id,
            family_id=family_id,
            token_hash=token_hash,
            expires_at=refresh_expires,
            last_used_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(session)

        # Fetch roles
        roles = await RbacService.get_user_roles(db, user.id)

        # Generate access token
        access_token = create_access_token(
            user_id=user.id,
            session_id=session_id,
            university_id=target_uni.id,
            roles=roles,
        )

        await db.commit()
        await db.refresh(user)

        log_security_event(
            "LOGIN_SUCCESS",
            user_id=user.id,
            university_id=target_uni.id,
            details={"session_id": str(session_id)},
        )

        return LoginResponse(
            user=UserSummary(
                id=user.id,
                university_id=user.university_id,
                username=user.username,
                email=user.email,
                preferred_language=user.preferred_language,
                status=user.status,
                must_change_password=user.must_change_password,
                roles=roles,
            ),
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=raw_refresh_token,
                token_type="bearer",
                expires_in=settings.AUTH_ACCESS_TOKEN_MINUTES * 60,
            ),
        )

    @staticmethod
    async def refresh_token(
        db: AsyncSession,
        raw_refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> TokenRefreshResponse:
        """Rotate refresh token and issue new access token.

        Enforces refresh token replay / reuse detection.
        """
        settings = get_settings()
        token_hash = hash_refresh_token(raw_refresh_token)

        stmt = select(RefreshSession).where(RefreshSession.token_hash == token_hash)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise TokenInvalidException("Invalid refresh token.")

        # REPLAY / REUSE DETECTION
        if session.revoked_at is not None:
            # Suspicious reuse detected! Invalidate the entire token family
            log_security_event(
                "REFRESH_TOKEN_REUSE_DETECTED",
                user_id=session.user_id,
                details={
                    "family_id": str(session.family_id),
                    "revoked_session_id": str(session.id),
                    "revocation_reason": session.revocation_reason,
                },
            )
            # Revoke all sessions in this family
            stmt_revoke_family = (
                update(RefreshSession)
                .where(
                    RefreshSession.family_id == session.family_id,
                    RefreshSession.revoked_at.is_(None),
                )
                .values(
                    revoked_at=utc_now(),
                    revocation_reason=RevocationReason.REUSE_DETECTED.value,
                )
            )
            await db.execute(stmt_revoke_family)
            await db.commit()

            raise DomainException(
                code="REFRESH_TOKEN_REUSE_DETECTED",
                message="Suspicious token reuse detected. All related sessions have been revoked.",
                status_code=401,
            )

        now = utc_now()
        if session.expires_at <= now:
            raise TokenExpiredException("Refresh token has expired.")

        # Verify user active status
        user = await db.get(User, session.user_id)
        if not user or user.status != UserStatus.ACTIVE.value:
            session.revoked_at = now
            session.revocation_reason = "USER_INACTIVE"
            await db.commit()
            raise DomainException(
                code="ACCOUNT_DISABLED",
                message="User account is inactive or disabled.",
                status_code=403,
            )

        # Valid rotation:
        # 1. Issue descendant refresh session in the same family first
        new_session_id = uuid7()
        new_raw_token, new_token_hash = generate_refresh_token()
        new_expires = now + timedelta(days=settings.AUTH_REFRESH_TOKEN_DAYS)

        new_session = RefreshSession(
            id=new_session_id,
            user_id=user.id,
            family_id=session.family_id,
            token_hash=new_token_hash,
            expires_at=new_expires,
            last_used_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(new_session)
        await db.flush()

        # 2. Mark current session as rotated and link to descendant
        session.revoked_at = now
        session.revocation_reason = RevocationReason.ROTATED.value
        session.last_used_at = now
        session.replaced_by_id = new_session.id

        # 3. Issue new access token
        roles = await RbacService.get_user_roles(db, user.id)
        access_token = create_access_token(
            user_id=user.id,
            session_id=new_session_id,
            university_id=user.university_id,
            roles=roles,
        )

        await db.commit()

        log_security_event(
            "SESSION_REFRESHED",
            user_id=user.id,
            university_id=user.university_id,
            details={"old_session_id": str(session.id), "new_session_id": str(new_session_id)},
        )

        return TokenRefreshResponse(
            access_token=access_token,
            refresh_token=new_raw_token,
            token_type="bearer",
            expires_in=settings.AUTH_ACCESS_TOKEN_MINUTES * 60,
        )

    @staticmethod
    async def logout(db: AsyncSession, session_id: uuid.UUID) -> None:
        """Revoke current refresh session on explicit logout."""
        session = await db.get(RefreshSession, session_id)
        if session and session.revoked_at is None:
            session.revoked_at = utc_now()
            session.revocation_reason = RevocationReason.LOGOUT.value
            await db.commit()
            log_security_event(
                "SESSION_REVOKED",
                user_id=session.user_id,
                details={"session_id": str(session_id), "reason": "LOGOUT"},
            )

    @staticmethod
    async def logout_all(db: AsyncSession, user_id: uuid.UUID) -> int:
        """Revoke all active sessions for a user."""
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(
                revoked_at=utc_now(),
                revocation_reason=RevocationReason.LOGOUT_ALL.value,
            )
        )
        res = await db.execute(stmt)
        await db.commit()
        count = res.rowcount  # type: ignore[attr-defined]
        log_security_event(
            "SESSION_REVOKED",
            user_id=user_id,
            details={"revoked_count": count, "reason": "LOGOUT_ALL"},
        )
        return count

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change user password, clear must_change_password, and revoke other sessions."""
        is_valid, _ = verify_password(current_password, user.password_hash)
        if not is_valid:
            raise DomainException(
                code="INVALID_CREDENTIALS",
                message="Current password is incorrect.",
                status_code=400,
            )

        validate_password_policy(new_password)
        if current_password == new_password:
            raise ValidationException(
                "New password must be different from current password.",
                details={"field": "new_password"},
            )

        now = utc_now()
        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        user.password_changed_at = now

        # Revoke all active sessions
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user.id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(
                revoked_at=now,
                revocation_reason=RevocationReason.PASSWORD_CHANGED.value,
            )
        )
        await db.execute(stmt)
        await db.commit()

        log_security_event(
            "PASSWORD_CHANGED",
            user_id=user.id,
            university_id=user.university_id,
        )
