"""Pytest fixtures for database, async sessions, and test client."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure testing environment
os.environ["APP_ENV"] = "testing"

from backend.app.auth.passwords import hash_password
from backend.app.core.constants import ScopeType, SystemRole, UserStatus
from backend.app.core.database import get_sessionmaker
from backend.app.main import app
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.rbac.seeding import seed_system_rbac


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Yield an AsyncSession for testing and rollback changes after test."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seed_data() -> None:
    """Ensure system RBAC roles and permissions are seeded for the test session."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        await seed_system_rbac(session)
        await session.commit()


@pytest_asyncio.fixture(scope="session")
async def test_university() -> University:
    """Fixture providing a persistent active test university."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        stmt = select(University).where(University.code == "HU_TEST")
        result = await session.execute(stmt)
        uni = result.scalar_one_or_none()
        if not uni:
            uni = University(
                name="Herat University Test",
                code="HU_TEST",
                timezone="Asia/Kabul",
                default_language="en",
                status="ACTIVE",
            )
            session.add(uni)
            await session.commit()
            await session.refresh(uni)
        return uni


@pytest_asyncio.fixture(scope="session")
async def second_university() -> University:
    """Fixture providing a second university for cross-tenant isolation testing."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        stmt = select(University).where(University.code == "KU_TEST")
        result = await session.execute(stmt)
        uni = result.scalar_one_or_none()
        if not uni:
            uni = University(
                name="Kabul University Test",
                code="KU_TEST",
                timezone="Asia/Kabul",
                default_language="ps",
                status="ACTIVE",
            )
            session.add(uni)
            await session.commit()
            await session.refresh(uni)
        return uni


@pytest_asyncio.fixture(scope="session")
async def test_admin_user(test_university: University) -> User:
    """Fixture providing an active Super Admin user with full RBAC access."""
    username = "test_super_admin"
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        stmt = select(User).where(
            User.university_id == test_university.id, User.username == username
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                university_id=test_university.id,
                username=username,
                email="admin@test.edu",
                password_hash=hash_password("SuperSecureAdmin123!"),
                status=UserStatus.ACTIVE.value,
                must_change_password=False,
            )
            session.add(user)
            await session.flush()

            # Find SUPER_ADMIN role
            role_stmt = select(Role).where(Role.code == SystemRole.SUPER_ADMIN.value)
            role_res = await session.execute(role_stmt)
            super_admin_role = role_res.scalar_one()

            assignment = RoleAssignment(
                user_id=user.id,
                role_id=super_admin_role.id,
                university_id=test_university.id,
                scope_type=ScopeType.UNIVERSITY.value,
                scope_id=test_university.id,
            )
            session.add(assignment)
            await session.commit()
            await session.refresh(user)

        return user
