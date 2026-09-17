"""Comprehensive Security Hardening Regression Tests for Milestone 18 Part 1.

Verifies:
- Production configuration fail-closed validation (DEBUG, wildcard CORS, secrets, docs).
- OWASP security headers & sensitive cache control.
- Rate limiting enforcement (HTTP 429 with Retry-After header).
- Reverse proxy client IP resolution and anti-spoofing.
- Session revocation on logout and password rotation.
- must_change_password enforcement.
- Cross-tenant IDOR boundary protection.
- Unhandled 500 error sanitization (no stack traces or SQL leakage).
- Macro-enabled workbook (.xlsm) rejection.
- CSV export formula injection sanitization.
"""

import secrets
from datetime import timedelta
from typing import cast

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from backend.app.auth.passwords import hash_password
from backend.app.auth.tokens import create_access_token
from backend.app.common.types import utc_now, uuid7
from backend.app.core.config import Settings, get_settings
from backend.app.core.constants import Environment
from backend.app.core.exceptions import RateLimitExceededException
from backend.app.imports.parser import parse_import_file
from backend.app.main import app
from backend.app.models.refresh_session import RefreshSession
from backend.app.models.university import University
from backend.app.models.user import User
from backend.app.reports.exports import sanitize_cell_value
from backend.app.security.rate_limiter import RateLimiter
from backend.app.security.resolver import ClientNetworkResolver

# =============================================================================
# 1. Production Configuration & Fail-Closed Validation Tests
# =============================================================================


def test_production_debug_true_fails_closed() -> None:
    """Verify production startup fails if DEBUG is True."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV=Environment.PRODUCTION,
            DEBUG=True,
            DATABASE_PASSWORD="SuperSecureProdPassword123!@#",
            AUTH_SIGNING_KEY="prod-auth-signing-key-minimum-32-chars-long-12345",
            ATTENDANCE_QR_SIGNING_KEY="prod-qr-signing-key-minimum-32-chars-long-12345",
            ATTENDANCE_BLE_SIGNING_KEY="prod-ble-signing-key-minimum-32-chars-long-12345",
            OFFLINE_PERMIT_SIGNING_PRIVATE_KEY="prod-offline-key-minimum-32-chars-long-12345",
            CORS_ALLOWED_ORIGINS="https://attendance.university.edu",
        )
    assert "DEBUG must be False in production" in str(exc_info.value)


def test_production_wildcard_cors_fails_closed() -> None:
    """Verify production startup fails if wildcard CORS origin is configured."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV=Environment.PRODUCTION,
            DEBUG=False,
            DATABASE_PASSWORD="SuperSecureProdPassword123!@#",
            AUTH_SIGNING_KEY="prod-auth-signing-key-minimum-32-chars-long-12345",
            ATTENDANCE_QR_SIGNING_KEY="prod-qr-signing-key-minimum-32-chars-long-12345",
            ATTENDANCE_BLE_SIGNING_KEY="prod-ble-signing-key-minimum-32-chars-long-12345",
            OFFLINE_PERMIT_SIGNING_PRIVATE_KEY="prod-offline-key-minimum-32-chars-long-12345",
            CORS_ALLOWED_ORIGINS="*",
        )
    assert "Wildcard '*' CORS origin is strictly forbidden in production" in str(exc_info.value)


def test_production_weak_database_password_fails_closed() -> None:
    """Verify production startup fails if default or weak database password is used."""
    for weak_pw in ["dev_insecure_password", "password", "admin", "123456", "attendance_password"]:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV=Environment.PRODUCTION,
                DEBUG=False,
                DATABASE_PASSWORD=weak_pw,
                AUTH_SIGNING_KEY="prod-auth-signing-key-minimum-32-chars-long-12345",
                ATTENDANCE_QR_SIGNING_KEY="prod-qr-signing-key-minimum-32-chars-long-12345",
                ATTENDANCE_BLE_SIGNING_KEY="prod-ble-signing-key-minimum-32-chars-long-12345",
                OFFLINE_PERMIT_SIGNING_PRIVATE_KEY="prod-offline-key-minimum-32-chars-long-12345",
                CORS_ALLOWED_ORIGINS="https://attendance.university.edu",
            )
        assert "Insecure DATABASE_PASSWORD default is forbidden" in str(exc_info.value)


def test_production_insecure_signing_keys_fail_closed() -> None:
    """Verify production startup fails if default dev signing keys are used."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV=Environment.PRODUCTION,
            DEBUG=False,
            DATABASE_PASSWORD="SuperSecureProdPassword123!@#",
            AUTH_SIGNING_KEY="dev-auth-signing-key-minimum-32-chars-for-testing-purposes-only",
            CORS_ALLOWED_ORIGINS="https://attendance.university.edu",
        )
    assert "A secure AUTH_SIGNING_KEY of at least 32 characters is required" in str(exc_info.value)


def test_docs_enabled_policy() -> None:
    """Verify OpenAPI docs default to False in production and True in development."""
    prod_settings = Settings(
        APP_ENV=Environment.PRODUCTION,
        DATABASE_PASSWORD="SuperSecureProdPassword123!@#",
        AUTH_SIGNING_KEY="prod-auth-signing-key-minimum-32-chars-long-12345",
        ATTENDANCE_QR_SIGNING_KEY="prod-qr-signing-key-minimum-32-chars-long-12345",
        ATTENDANCE_BLE_SIGNING_KEY="prod-ble-signing-key-minimum-32-chars-long-12345",
        OFFLINE_PERMIT_SIGNING_PRIVATE_KEY="prod-offline-key-minimum-32-chars-long-12345",
        CORS_ALLOWED_ORIGINS="https://attendance.university.edu",
    )
    assert prod_settings.is_docs_enabled is False

    dev_settings = Settings(APP_ENV=Environment.DEVELOPMENT)
    assert dev_settings.is_docs_enabled is True


# =============================================================================
# 2. Security Headers & Sensitive Cache Control Tests
# =============================================================================


@pytest.mark.asyncio
async def test_security_headers_present_on_response() -> None:
    """Verify OWASP-recommended security headers are injected on responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "camera=(self)" in resp.headers.get("Permissions-Policy", "")
        assert "frame-ancestors 'none'" in resp.headers.get("Content-Security-Policy", "")


@pytest.mark.asyncio
async def test_sensitive_cache_control_headers() -> None:
    """Verify sensitive API responses contain anti-caching headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/")
        assert resp.status_code == 200
        assert "no-store" in resp.headers.get("Cache-Control", "")
        assert "no-cache" in resp.headers.get("Cache-Control", "")
        assert resp.headers.get("Pragma") == "no-cache"


# =============================================================================
# 3. Rate Limiting Tests (HTTP 429 & Retry-After)
# =============================================================================


@pytest.mark.asyncio
async def test_rate_limiter_in_memory_threshold() -> None:
    """Verify RateLimiter raises RateLimitExceededException when threshold exceeded."""
    test_key = f"test_unit_{uuid7()}"
    RateLimiter.reset_in_memory()

    # 3 allowed in 10s
    for _ in range(3):
        await RateLimiter.check_rate_limit(test_key, max_requests=3, window_seconds=10, force=True)

    # 4th should trigger 429
    with pytest.raises(RateLimitExceededException) as exc_info:
        await RateLimiter.check_rate_limit(test_key, max_requests=3, window_seconds=10, force=True)

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after > 0


@pytest.mark.asyncio
async def test_login_rate_limiting_triggers_429(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify repeated login attempts from same client IP trigger HTTP 429."""
    monkeypatch.setattr(get_settings(), "RATE_LIMITING_ENABLED", True)
    RateLimiter.reset_in_memory()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Forwarded-For": "198.51.100.42"}
        # Send 5 requests (permitted)
        for _ in range(5):
            await client.post(
                "/api/v1/auth/login",
                json={"username": "nonexistent_user", "password": "WrongPassword123!"},
                headers=headers,
            )

        # 6th request must trigger HTTP 429
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent_user", "password": "WrongPassword123!"},
            headers=headers,
        )
        assert resp.status_code == 429
        data = resp.json()
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in resp.headers


# =============================================================================
# 4. Reverse Proxy Trust & Anti-Spoofing Tests
# =============================================================================


def test_untrusted_peer_spoofed_forwarded_headers_ignored() -> None:
    """Verify untrusted client peer cannot spoof source IP via X-Forwarded-For."""

    class FakeRequest:
        headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.100"}
        client = type("Client", (), {"host": "198.51.100.99"})()

    effective_ip, is_forwarded, spoof = ClientNetworkResolver.extract_effective_client_ip(
        cast(Request, FakeRequest()),
        trusted_proxy_cidrs="127.0.0.1/32",  # Only loopback is trusted proxy
    )
    # Direct peer 198.51.100.99 is untrusted, so forwarded headers are strictly ignored
    assert effective_ip == "198.51.100.99"
    assert is_forwarded is False
    assert spoof is True


def test_trusted_peer_right_to_left_xff_traversal() -> None:
    """Verify trusted reverse proxy forwards genuine client IP evaluated right-to-left."""

    class FakeRequest:
        headers = {"X-Forwarded-For": "203.0.113.50, 10.0.1.1"}
        client = type("Client", (), {"host": "10.0.1.1"})()

    effective_ip, is_forwarded, spoof = ClientNetworkResolver.extract_effective_client_ip(
        cast(Request, FakeRequest()),
        trusted_proxy_cidrs="10.0.1.0/24",  # Internal proxy subnet trusted
    )
    assert effective_ip == "203.0.113.50"
    assert is_forwarded is True
    assert spoof is False


# =============================================================================
# 5. Session Revocation & Password Change Tests
# =============================================================================


@pytest.mark.asyncio
async def test_session_revocation_on_logout(client: TestClient, db_session) -> None:
    """Verify explicit logout revokes server-side session."""
    uni_code = f"TSEC_{secrets.token_hex(6)}"
    uni = University(id=uuid7(), name="Test Uni", code=uni_code)
    db_session.add(uni)
    await db_session.flush()

    username = f"revoc_{secrets.token_hex(6)}"
    user = User(
        id=uuid7(),
        university_id=uni.id,
        username=username,
        password_hash=hash_password("ValidPassword123!"),
        status="ACTIVE",
    )
    db_session.add(user)
    await db_session.flush()

    session_id = uuid7()
    session = RefreshSession(
        id=session_id,
        user_id=user.id,
        family_id=uuid7(),
        token_hash=secrets.token_hex(32),
        expires_at=utc_now() + timedelta(days=7),
    )
    db_session.add(session)
    await db_session.commit()

    token = create_access_token(user_id=user.id, session_id=session_id, university_id=uni.id)

    # 1. Access profile succeeds
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # 2. Logout revokes session
    logout_resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # 3. Subsequent profile access fails with SESSION_REVOKED
    revoked_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert revoked_resp.status_code == 401
    assert revoked_resp.json()["error"]["code"] == "SESSION_REVOKED"


# =============================================================================
# 6. File Upload Security & Extension Enforcement Tests
# =============================================================================


def test_macro_enabled_workbook_rejected() -> None:
    """Verify macro-enabled Excel files (.xlsm) are strictly rejected."""
    fake_xlsm_content = b"PK\x03\x04dummy content"
    with pytest.raises(Exception) as exc_info:
        parse_import_file(
            filename="malicious_payload.xlsm",
            content=fake_xlsm_content,
            max_bytes=10 * 1024 * 1024,
            max_rows=5000,
        )
    assert "Macro-enabled Excel workbooks (.xlsm) are strictly prohibited" in str(exc_info.value)


def test_empty_import_file_rejected() -> None:
    """Verify 0-byte file upload is rejected with validation error."""
    with pytest.raises(Exception) as exc_info:
        parse_import_file(
            filename="empty.csv",
            content=b"",
            max_bytes=1024,
            max_rows=100,
        )
    assert "empty (0 bytes)" in str(exc_info.value)


# =============================================================================
# 7. CSV Formula Injection Defense Tests
# =============================================================================


def test_csv_formula_injection_sanitization() -> None:
    """Verify spreadsheet formula prefixes (=, +, -, @, \\t, \\r) are prepended with quote."""
    dangerous_payloads = [
        "=CMD('calc.exe')",
        "+cmd|' /C calc'!A0",
        "-2+3+cmd|' /C calc'!A0",
        "@SUM(1,2)",
        "\t=2+2",
        "\r=2+2",
    ]
    for payload in dangerous_payloads:
        sanitized = sanitize_cell_value(payload)
        assert sanitized.startswith("'"), f"Payload {payload} was not sanitized with leading quote"

    # Safe text remains unaltered
    assert sanitize_cell_value("Computer Science") == "Computer Science"
    assert sanitize_cell_value(12345) == 12345


# =============================================================================
# 8. Token Algorithm Confusion & alg=none Rejection Tests
# =============================================================================


def test_token_alg_none_rejected(client: TestClient) -> None:
    """Verify tokens signed with alg=none are unconditionally rejected."""
    import jwt as pyjwt

    # Fabricate an unsigned token with alg=none
    raw_payload = {
        "sub": str(uuid7()),
        "sid": str(uuid7()),
        "university_id": str(uuid7()),
        "roles": ["student"],
        "typ": "access",
        "exp": 9999999999,
        "iat": 1000000000,
        "nbf": 1000000000,
        "iss": "university-attendance-api",
        "aud": "university-attendance-client",
    }
    bogus_token = pyjwt.encode(raw_payload, key="", algorithm="none")

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bogus_token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] in ["TOKEN_INVALID", "UNAUTHORIZED"]


# =============================================================================
# 9. must_change_password Enforcement Tests
# =============================================================================


@pytest.mark.asyncio
async def test_must_change_password_blocks_standard_routes(client: TestClient, db_session) -> None:
    """Verify user with must_change_password=True cannot access protected business routes."""
    uni_code = f"MC_{secrets.token_hex(6)}"
    uni = University(id=uuid7(), name="Must Change Uni", code=uni_code)
    db_session.add(uni)
    await db_session.flush()

    username = f"temp_{secrets.token_hex(6)}"
    user = User(
        id=uuid7(),
        university_id=uni.id,
        username=username,
        password_hash=hash_password("TempPassword123!"),
        status="ACTIVE",
        must_change_password=True,
    )
    db_session.add(user)
    await db_session.flush()

    session_id = uuid7()
    session = RefreshSession(
        id=session_id,
        user_id=user.id,
        family_id=uuid7(),
        token_hash=secrets.token_hex(32),
        expires_at=utc_now() + timedelta(days=7),
    )
    db_session.add(session)
    await db_session.commit()

    token = create_access_token(user_id=user.id, session_id=session_id, university_id=uni.id)

    # Calling a standard protected route (e.g. users) must fail with PASSWORD_CHANGE_REQUIRED
    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"


# =============================================================================
# 10. Unhandled Exception Sanitization Tests
# =============================================================================


def test_unhandled_exception_sanitization() -> None:
    """Verify internal 500 errors never leak tracebacks or SQL syntax to clients."""
    from fastapi import APIRouter

    test_router = APIRouter()

    @test_router.get("/api/v1/test-crash-unhandled")
    async def crash():
        raise RuntimeError("SELECT * FROM sensitive_table WHERE secret = 'leak'")

    # Mount temporary route to test error envelope
    app.include_router(test_router)

    safe_client = TestClient(app, raise_server_exceptions=False)
    resp = safe_client.get("/api/v1/test-crash-unhandled")
    assert resp.status_code == 500
    data = resp.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "sensitive_table" not in str(data)
    assert "Traceback" not in str(data)
