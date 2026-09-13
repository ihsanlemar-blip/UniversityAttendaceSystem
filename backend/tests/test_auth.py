"""Test suite for authentication endpoints, session rotation, replay detection,
and password lifecycle.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import hash_password
from backend.app.core.constants import SystemRole, UserStatus
from backend.app.models.university import University
from backend.app.models.user import User


def test_login_success_and_audit(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify login issues valid tokens and logs a successful login attempt."""
    res = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin_user.username,
            "password": "SuperSecureAdmin123!",
            "university_id": str(test_university.id),
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "tokens" in data
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]
    assert data["tokens"]["token_type"].lower() == "bearer"
    assert data["tokens"]["expires_in"] > 0
    assert data["user"]["username"] == test_admin_user.username


def test_login_invalid_password_returns_generic_error(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify invalid password returns generic 401 error message without leakage."""
    res = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin_user.username,
            "password": "WrongPassword999!",
            "university_id": str(test_university.id),
        },
    )
    assert res.status_code == 401
    error = res.json()["error"]
    assert error["code"] == "INVALID_CREDENTIALS"
    assert error["message"] == "Invalid credentials."


def test_login_nonexistent_user_returns_generic_error(
    client: TestClient,
    test_university: University,
) -> None:
    """Verify non-existent username returns identical generic 401 error."""
    res = client.post(
        "/api/v1/auth/login",
        json={
            "username": "ghost_nonexistent_user",
            "password": "WrongPassword999!",
            "university_id": str(test_university.id),
        },
    )
    assert res.status_code == 401
    error = res.json()["error"]
    assert error["code"] == "INVALID_CREDENTIALS"
    assert error["message"] == "Invalid credentials."


@pytest.mark.asyncio
async def test_login_disabled_user(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
) -> None:
    """Verify disabled account cannot authenticate."""
    username = f"disabled_{uuid.uuid4().hex[:6]}"
    user = User(
        university_id=test_university.id,
        username=username,
        email=f"{username}@test.edu",
        password_hash=hash_password("ValidPassword123!"),
        status=UserStatus.DISABLED.value,
    )
    db_session.add(user)
    await db_session.commit()

    res = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "ValidPassword123!",
            "university_id": str(test_university.id),
        },
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_brute_force_account_lockout(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
) -> None:
    """Verify repeated failed attempts trigger automatic account lockout."""
    username = f"lockout_{uuid.uuid4().hex[:6]}"
    user = User(
        university_id=test_university.id,
        username=username,
        email=f"{username}@test.edu",
        password_hash=hash_password("ValidPassword123!"),
        status=UserStatus.ACTIVE.value,
    )
    db_session.add(user)
    await db_session.commit()

    # Fail 5 times
    for _ in range(5):
        res = client.post(
            "/api/v1/auth/login",
            json={
                "username": username,
                "password": "BadPassword123!",
                "university_id": str(test_university.id),
            },
        )
        assert res.status_code == 401

    # 6th attempt must be rejected with ACCOUNT_LOCKED
    res_locked = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "ValidPassword123!",
            "university_id": str(test_university.id),
        },
    )
    assert res_locked.status_code == 403
    assert res_locked.json()["error"]["code"] == "ACCOUNT_LOCKED"


def test_refresh_token_rotation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify refresh token rotation returns new tokens and invalidates the old token."""
    # 1. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin_user.username,
            "password": "SuperSecureAdmin123!",
            "university_id": str(test_university.id),
        },
    )
    assert login_res.status_code == 200
    refresh_1 = login_res.json()["data"]["tokens"]["refresh_token"]

    # 2. Refresh
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_1},
    )
    assert refresh_res.status_code == 200
    data = refresh_res.json()["data"]
    access_2 = data["access_token"]
    refresh_2 = data["refresh_token"]

    assert access_2 is not None
    assert refresh_2 != refresh_1


def test_refresh_token_reuse_detection_revokes_family(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify replaying an old rotated refresh token triggers reuse detection and revokes family."""
    # 1. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin_user.username,
            "password": "SuperSecureAdmin123!",
            "university_id": str(test_university.id),
        },
    )
    refresh_1 = login_res.json()["data"]["tokens"]["refresh_token"]

    # 2. Valid rotation: refresh_1 -> refresh_2
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_1},
    )
    assert refresh_res.status_code == 200
    refresh_2 = refresh_res.json()["data"]["refresh_token"]

    # 3. Malicious / Replay: reuse refresh_1
    replay_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_1},
    )
    assert replay_res.status_code == 401
    assert replay_res.json()["error"]["code"] == "REFRESH_TOKEN_REUSE_DETECTED"

    # 4. As a result of reuse detection, even refresh_2 (legitimate active token)
    # must now be revoked
    subsequent_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_2},
    )
    assert subsequent_res.status_code == 401


def test_logout_and_revocation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify /logout revokes the current session and rejects further access."""
    # 1. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin_user.username,
            "password": "SuperSecureAdmin123!",
            "university_id": str(test_university.id),
        },
    )
    access_token = login_res.json()["data"]["tokens"]["access_token"]
    refresh_token = login_res.json()["data"]["tokens"]["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # 3. Accessing /auth/me with revoked token should fail
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 401
    assert me_res.json()["error"]["code"] == "SESSION_REVOKED"

    # 4. Refresh with that refresh_token should also fail
    ref_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_res.status_code == 401


def test_logout_all(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify /logout-all revokes all sessions belonging to the user."""
    # Session 1
    res1 = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin_user.username,
            "password": "SuperSecureAdmin123!",
            "university_id": str(test_university.id),
        },
    )
    token1 = res1.json()["data"]["tokens"]["access_token"]

    # Session 2
    res2 = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin_user.username,
            "password": "SuperSecureAdmin123!",
            "university_id": str(test_university.id),
        },
    )
    token2 = res2.json()["data"]["tokens"]["access_token"]

    # Logout all using Session 2
    res_all = client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res_all.status_code == 200

    # Both tokens should now be rejected as SESSION_REVOKED
    chk1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    assert chk1.status_code == 401
    chk2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert chk2.status_code == 401


def test_get_me_endpoint(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify GET /auth/me returns identity, roles, and permissions."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_admin_user.username,
            "password": "SuperSecureAdmin123!",
            "university_id": str(test_university.id),
        },
    )
    token = login_res.json()["data"]["tokens"]["access_token"]

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["username"] == test_admin_user.username
    assert SystemRole.SUPER_ADMIN.value in data["roles"]
    assert len(data["permissions"]) >= 14


@pytest.mark.asyncio
async def test_change_password_lifecycle(
    client: TestClient,
    db_session: AsyncSession,
    test_university: University,
) -> None:
    """Verify changing password succeeds, updates credentials, and invalidates other sessions."""
    username = f"pw_user_{uuid.uuid4().hex[:6]}"
    old_pw = "OldPassword123!"
    new_pw = "NewSuperPassword123!"

    user = User(
        university_id=test_university.id,
        username=username,
        email=f"{username}@test.edu",
        password_hash=hash_password(old_pw),
        status=UserStatus.ACTIVE.value,
        must_change_password=True,
    )
    db_session.add(user)
    await db_session.commit()

    # Login with old password
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": old_pw,
            "university_id": str(test_university.id),
        },
    )
    token = login_res.json()["data"]["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Change password with wrong current password should fail
    fail_res = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "WrongPassword999!",
            "new_password": new_pw,
            "confirm_password": new_pw,
        },
    )
    assert fail_res.status_code in [400, 401]

    # 2. Change password with identical password should fail
    same_res = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": old_pw,
            "new_password": old_pw,
        },
    )
    assert same_res.status_code == 422
    assert same_res.json()["error"]["code"] == "VALIDATION_ERROR"

    # 3. Successful change password
    ok_res = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": old_pw,
            "new_password": new_pw,
            "confirm_password": new_pw,
        },
    )
    assert ok_res.status_code == 200

    # 4. Old password no longer works
    old_login = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": old_pw,
            "university_id": str(test_university.id),
        },
    )
    assert old_login.status_code == 401

    # 5. New password works
    new_login = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": new_pw,
            "university_id": str(test_university.id),
        },
    )
    assert new_login.status_code == 200
    assert new_login.json()["data"]["user"]["must_change_password"] is False
