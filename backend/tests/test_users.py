"""Test suite for user management endpoints, tenant isolation, lifecycle,
and password change gates.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import hash_password
from backend.app.core.constants import UserStatus
from backend.app.models.university import University
from backend.app.models.user import User


def get_admin_headers(
    client: TestClient, admin_user: User, university: University
) -> dict[str, str]:
    """Helper to log in admin and return bearer authorization headers."""
    res = client.post(
        "/api/v1/auth/login",
        json={
            "username": admin_user.username,
            "password": "SuperSecureAdmin123!",
            "university_id": str(university.id),
        },
    )
    assert res.status_code == 200
    token = res.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_user_success(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify administrator can create a new user in the university."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    username = f"newuser_{uuid.uuid4().hex[:6]}"

    res = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": username,
            "password": "TemporaryPassword123!",
            "email": f"{username}@test.edu",
            "preferred_language": "en",
            "must_change_password": True,
        },
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["username"] == username
    assert data["status"] == UserStatus.ACTIVE.value
    assert data["must_change_password"] is True
    assert data["university_id"] == str(test_university.id)


def test_duplicate_username_same_university_conflict(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify creating duplicate username in same university returns 409 Conflict."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    username = f"dupuser_{uuid.uuid4().hex[:6]}"

    # 1. Create first user
    res1 = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": username,
            "password": "TemporaryPassword123!",
            "email": f"{username}@test.edu",
        },
    )
    assert res1.status_code == 201

    # 2. Attempt duplicate creation
    res2 = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": username,
            "password": "TemporaryPassword123!",
            "email": f"{username}_alt@test.edu",
        },
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_same_username_different_university_allowed(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    second_university: University,
    test_admin_user: User,
) -> None:
    """Verify same username can exist across different universities (multi-tenant uniqueness)."""
    headers_uni1 = get_admin_headers(client, test_admin_user, test_university)
    shared_username = f"shared_{uuid.uuid4().hex[:6]}"

    # Create in university 1
    res1 = client.post(
        "/api/v1/users",
        headers=headers_uni1,
        json={
            "username": shared_username,
            "password": "TemporaryPassword123!",
            "email": f"{shared_username}@uni1.edu",
        },
    )
    assert res1.status_code == 201

    # Directly create user with same username in university 2
    user_uni2 = User(
        university_id=second_university.id,
        username=shared_username,
        email=f"{shared_username}@uni2.edu",
        password_hash=hash_password("TemporaryPassword123!"),
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(user_uni2)
    await db_session.commit()
    await db_session.refresh(user_uni2)

    assert user_uni2.id is not None
    assert user_uni2.username == shared_username
    assert user_uni2.university_id == second_university.id


def test_list_users_pagination(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify paginated listing of users within university scope."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    res = client.get("/api/v1/users?skip=0&limit=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["page"] == 1
    assert data["total_count"] >= 1


@pytest.mark.asyncio
async def test_get_user_cross_tenant_isolation(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
    second_university: University,
    test_admin_user: User,
) -> None:
    """Verify administrator cannot access user account belonging to another university."""
    headers = get_admin_headers(client, test_admin_user, test_university)

    # Create user in second university
    foreign_user = User(
        university_id=second_university.id,
        username=f"foreign_{uuid.uuid4().hex[:6]}",
        email=f"foreign_{uuid.uuid4().hex[:6]}@test.edu",
        password_hash=hash_password("TemporaryPassword123!"),
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(foreign_user)
    await db_session.commit()
    await db_session.refresh(foreign_user)

    # Administrator in test_university attempts to fetch foreign_user
    res = client.get(f"/api/v1/users/{foreign_user.id}", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_disable_and_enable_user_lifecycle(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify administrator can disable and re-enable a user account."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    username = f"toggle_{uuid.uuid4().hex[:6]}"

    # Create user
    create_res = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": username,
            "password": "TemporaryPassword123!",
            "email": f"{username}@test.edu",
        },
    )
    user_id = create_res.json()["data"]["id"]

    # Disable user
    dis_res = client.post(
        f"/api/v1/users/{user_id}/disable",
        headers=headers,
        json={"reason": "Audit hold"},
    )
    assert dis_res.status_code == 200
    assert dis_res.json()["data"]["status"] == UserStatus.DISABLED.value

    # Re-enable user
    en_res = client.post(f"/api/v1/users/{user_id}/enable", headers=headers)
    assert en_res.status_code == 200
    assert en_res.json()["data"]["status"] == UserStatus.ACTIVE.value


def test_admin_reset_password(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify administrator reset sets new password and forces must_change_password."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    username = f"reset_{uuid.uuid4().hex[:6]}"
    new_admin_pw = "ResetSecretPass123!"

    # Create user
    create_res = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": username,
            "password": "InitialPassword123!",
            "email": f"{username}@test.edu",
        },
    )
    user_id = create_res.json()["data"]["id"]

    # Admin reset
    reset_res = client.post(
        f"/api/v1/users/{user_id}/reset-password",
        headers=headers,
        json={"new_password": new_admin_pw},
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["data"]["must_change_password"] is True

    # User can log in with new password
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": new_admin_pw,
            "university_id": str(test_university.id),
        },
    )
    assert login_res.status_code == 200
    assert login_res.json()["data"]["user"]["must_change_password"] is True


def test_must_change_password_gate_enforcement(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify must_change_password blocks regular routes but permits password change."""
    headers_admin = get_admin_headers(client, test_admin_user, test_university)
    username = f"mustchange_{uuid.uuid4().hex[:6]}"
    temp_pw = "MustChangePass123!"
    final_pw = "FinalSecurePass123!"

    # Create user with must_change_password=True
    client.post(
        "/api/v1/users",
        headers=headers_admin,
        json={
            "username": username,
            "password": temp_pw,
            "email": f"{username}@test.edu",
            "must_change_password": True,
        },
    )

    # User logs in
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": temp_pw,
            "university_id": str(test_university.id),
        },
    )
    user_token = login_res.json()["data"]["tokens"]["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Calling standard route (e.g. /users) is blocked with 403 PASSWORD_CHANGE_REQUIRED
    blocked_res = client.get("/api/v1/users", headers=user_headers)
    assert blocked_res.status_code == 403
    assert blocked_res.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    # User CAN call /auth/change-password
    pw_change_res = client.post(
        "/api/v1/auth/change-password",
        headers=user_headers,
        json={
            "current_password": temp_pw,
            "new_password": final_pw,
        },
    )
    assert pw_change_res.status_code == 200

    # Login with new password -> must_change_password is now False
    new_login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": final_pw,
            "university_id": str(test_university.id),
        },
    )
    assert new_login_res.status_code == 200
    assert new_login_res.json()["data"]["user"]["must_change_password"] is False
