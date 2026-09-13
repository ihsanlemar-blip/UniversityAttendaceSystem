"""Test suite for Super Admin bootstrap CLI command and university provisioning."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.cli.bootstrap_admin import bootstrap_super_admin, parse_args
from backend.app.core.constants import SystemRole
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.rbac.service import RbacService


@pytest.mark.asyncio
async def test_bootstrap_super_admin_execution(db_session: AsyncSession) -> None:
    """Verify bootstrap provisions university, seeds RBAC, and creates Super Admin."""
    uni_code = f"BT_{uuid.uuid4().hex[:4].upper()}"
    admin_user = f"bt_admin_{uuid.uuid4().hex[:6]}"
    admin_pass = "BootstrapSecurePass123!"

    # Run bootstrap
    await bootstrap_super_admin(
        username=admin_user,
        password=admin_pass,
        university_code=uni_code,
        university_name="Bootstrap Test University",
        email=f"{admin_user}@test.edu",
    )

    # Verify university created
    stmt_uni = select(University).where(University.code == uni_code)
    res_uni = await db_session.execute(stmt_uni)
    uni = res_uni.scalar_one_or_none()
    assert uni is not None
    assert uni.name == "Bootstrap Test University"

    # Verify user created
    stmt_user = select(User).where(User.university_id == uni.id, User.username == admin_user)
    res_user = await db_session.execute(stmt_user)
    user = res_user.scalar_one_or_none()
    assert user is not None
    assert user.must_change_password is False

    # Verify Super Admin role assigned
    roles = await RbacService.get_user_roles(db_session, user.id)
    assert SystemRole.SUPER_ADMIN.value in roles

    # Verify user holds permissions
    perms = await RbacService.get_user_permissions(db_session, user.id)
    assert len(perms) >= 14


@pytest.mark.asyncio
async def test_bootstrap_super_admin_idempotency(db_session: AsyncSession) -> None:
    """Verify running bootstrap command multiple times is safely idempotent."""
    uni_code = f"IDEM_{uuid.uuid4().hex[:4].upper()}"
    admin_user = f"idem_admin_{uuid.uuid4().hex[:6]}"
    admin_pass = "IdempotentPass123!"

    # First run
    await bootstrap_super_admin(
        username=admin_user,
        password=admin_pass,
        university_code=uni_code,
        university_name="Idempotent Test University",
    )

    # Second run with same parameters must not fail
    await bootstrap_super_admin(
        username=admin_user,
        password=admin_pass,
        university_code=uni_code,
        university_name="Idempotent Test University",
    )


def test_parse_args_explicit_options() -> None:
    """Verify CLI parser requires explicit institutional options and rejects password flag."""
    import sys
    from unittest.mock import patch

    with patch.object(
        sys,
        "argv",
        [
            "bootstrap_admin",
            "--username",
            "sysadmin",
            "--university-code",
            "HU",
            "--university-name",
            "Herat University",
            "--password-stdin",
        ],
    ):
        args = parse_args()
        assert args.username == "sysadmin"
        assert args.university_code == "HU"
        assert args.university_name == "Herat University"
        assert args.password_stdin is True


def test_parse_args_rejects_command_line_password() -> None:
    """Verify passing password directly as command line argument is rejected for security."""
    import sys
    from unittest.mock import patch

    with patch.object(
        sys,
        "argv",
        [
            "bootstrap_admin",
            "--username",
            "sysadmin",
            "--university-code",
            "HU",
            "--university-name",
            "Herat University",
            "--password",
            "ExposedPass123!",
        ],
    ):
        with pytest.raises(SystemExit):
            parse_args()


def test_get_bootstrap_password_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify password is read safely from environment variable."""
    from backend.app.cli.bootstrap_admin import get_bootstrap_password

    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "EnvSecretPass123!")
    pw = get_bootstrap_password(use_stdin=False, username="sysadmin")
    assert pw == "EnvSecretPass123!"


def test_get_bootstrap_password_from_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify password is read safely from stdin with --password-stdin flag."""
    import io
    import sys

    from backend.app.cli.bootstrap_admin import get_bootstrap_password

    monkeypatch.setattr(sys, "stdin", io.StringIO("StdinSecretPass456!\n"))
    pw = get_bootstrap_password(use_stdin=True, username="sysadmin")
    assert pw == "StdinSecretPass456!"
