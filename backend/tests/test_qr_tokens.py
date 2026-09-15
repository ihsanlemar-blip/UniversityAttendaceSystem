"""Unit tests for Milestone 10 Dynamic QR & Cryptographic Presence Tokens.

Validates:
- INV-01 / INV-04: Expiration, rotation, and signature enforcement.
- Cryptographic isolation: Dedicated ATTENDANCE_QR_SIGNING_KEY distinct from AUTH_SIGNING_KEY.
- Classroom shared token model: Zero student PII in claims.
- Pure unit tests with injected time (no sleep, instant execution).
"""

import datetime
import uuid

import jwt
import pytest

from backend.app.attendance.tokens import (
    InvalidQrTokenException,
    PresenceTokenEngine,
    QrTokenExpiredException,
    compute_rotation_slot,
    compute_token_expiry,
)
from backend.app.core.config import get_settings


def test_rotation_slot_computation() -> None:
    """Verify rotation slot calculates deterministic intervals."""
    t0 = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    slot_0 = compute_rotation_slot(t0, rotation_seconds=30)

    # 15 seconds later -> same slot
    t15 = t0 + datetime.timedelta(seconds=15)
    assert compute_rotation_slot(t15, rotation_seconds=30) == slot_0

    # 30 seconds later -> next slot
    t30 = t0 + datetime.timedelta(seconds=30)
    assert compute_rotation_slot(t30, rotation_seconds=30) == slot_0 + 1

    # 60 seconds later -> slot + 2
    t60 = t0 + datetime.timedelta(seconds=60)
    assert compute_rotation_slot(t60, rotation_seconds=30) == slot_0 + 2


def test_token_expiry_slot_boundary() -> None:
    """Token expiry should align to rotation slot boundary when window is wide."""
    t0 = datetime.datetime(2026, 9, 14, 10, 0, 10, tzinfo=datetime.UTC)
    # t0 is 10s into a 30s slot (slot starts at 10:00:00, ends at 10:00:30)
    exp = compute_token_expiry(t0, rotation_seconds=30, checkpoint_close_utc=None)
    expected_exp = datetime.datetime(2026, 9, 14, 10, 0, 30, tzinfo=datetime.UTC)
    assert exp == expected_exp


def test_token_expiry_checkpoint_close_truncation() -> None:
    """Token expiry must truncate to checkpoint close if closing earlier than slot end."""
    t0 = datetime.datetime(2026, 9, 14, 10, 0, 10, tzinfo=datetime.UTC)
    # Checkpoint closes at 10:00:20 (before slot end at 10:00:30)
    cp_close = datetime.datetime(2026, 9, 14, 10, 0, 20, tzinfo=datetime.UTC)
    exp = compute_token_expiry(t0, rotation_seconds=30, checkpoint_close_utc=cp_close)
    assert exp == cp_close


def test_presence_token_generation_and_claims() -> None:
    """Generate presence token and verify all standard claims and header fields."""
    u_id = uuid.uuid4()
    s_id = uuid.uuid4()
    c_id = uuid.uuid4()
    now = datetime.datetime(2026, 9, 14, 10, 0, 5, tzinfo=datetime.UTC)

    token, issued_at, expires_at, slot = PresenceTokenEngine.generate_presence_token(
        university_id=u_id,
        session_id=s_id,
        checkpoint_id=c_id,
        checkpoint_type="START",
        current_time=now,
        rotation_seconds=30,
    )

    assert isinstance(token, str)
    assert issued_at == now
    assert expires_at == datetime.datetime(2026, 9, 14, 10, 0, 30, tzinfo=datetime.UTC)

    # Header check
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "HS256"
    assert header["typ"] == "attendance_qr"
    settings = get_settings()
    assert header["kid"] == settings.ATTENDANCE_QR_SIGNING_KID

    # Payload verification
    claims = PresenceTokenEngine.verify_presence_token(
        token=token,
        expected_university_id=u_id,
        expected_session_id=s_id,
        expected_checkpoint_id=c_id,
        current_time=now + datetime.timedelta(seconds=5),
    )

    assert claims["ver"] == 1
    assert claims["typ"] == "attendance_qr"
    assert claims["uid"] == str(u_id)
    assert claims["sid"] == str(s_id)
    assert claims["cid"] == str(c_id)
    assert claims["cpt"] == "START"
    assert claims["slot"] == slot
    assert "jti" in claims

    # STRICT ZERO STUDENT PII ASSERTION
    for forbidden_field in ("student_id", "student_number", "email", "user_id", "device_id", "ip"):
        assert forbidden_field not in claims


def test_token_expiration_rejection() -> None:
    """Verify that a token presented at or after its exp timestamp is rejected with
    QR_TOKEN_EXPIRED.
    """
    u_id = uuid.uuid4()
    s_id = uuid.uuid4()
    c_id = uuid.uuid4()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)

    token, _, exp_dt, _ = PresenceTokenEngine.generate_presence_token(
        university_id=u_id,
        session_id=s_id,
        checkpoint_id=c_id,
        checkpoint_type="START",
        current_time=now,
        rotation_seconds=30,
    )

    # 1 second before expiry -> valid
    valid_time = exp_dt - datetime.timedelta(seconds=1)
    claims = PresenceTokenEngine.verify_presence_token(token=token, current_time=valid_time)
    assert claims["cpt"] == "START"

    # Exactly at expiry -> rejected
    with pytest.raises(QrTokenExpiredException) as exc_info:
        PresenceTokenEngine.verify_presence_token(token=token, current_time=exp_dt)
    assert exc_info.value.code == "QR_TOKEN_EXPIRED"

    # 10 seconds past expiry -> rejected
    past_time = exp_dt + datetime.timedelta(seconds=10)
    with pytest.raises(QrTokenExpiredException) as exc_info:
        PresenceTokenEngine.verify_presence_token(token=token, current_time=past_time)
    assert exc_info.value.code == "QR_TOKEN_EXPIRED"


def test_token_tampering_rejection() -> None:
    """Tampering with token characters must result in INVALID_QR_TOKEN."""
    u_id = uuid.uuid4()
    s_id = uuid.uuid4()
    c_id = uuid.uuid4()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)

    token, _, _, _ = PresenceTokenEngine.generate_presence_token(
        university_id=u_id,
        session_id=s_id,
        checkpoint_id=c_id,
        checkpoint_type="START",
        current_time=now,
    )

    # Corrupt last character of signature
    tampered_sig = token[:-1] + ("x" if token[-1] != "x" else "y")
    with pytest.raises(InvalidQrTokenException) as exc_info:
        PresenceTokenEngine.verify_presence_token(token=tampered_sig, current_time=now)
    assert exc_info.value.code == "INVALID_QR_TOKEN"

    # Completely garbage string
    with pytest.raises(InvalidQrTokenException) as exc_info:
        PresenceTokenEngine.verify_presence_token(token="not.a.valid.jwt", current_time=now)
    assert exc_info.value.code == "INVALID_QR_TOKEN"


def test_cryptographic_key_isolation() -> None:
    """Token signed with AUTH_SIGNING_KEY cannot be accepted as an attendance QR token."""
    settings = get_settings()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    payload = {
        "ver": 1,
        "typ": "attendance_qr",
        "iss": settings.ATTENDANCE_QR_ISSUER,
        "aud": settings.ATTENDANCE_QR_AUDIENCE,
        "uid": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "cid": str(uuid.uuid4()),
        "cpt": "START",
        "slot": 12345,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(now.timestamp()) + 30,
        "jti": str(uuid.uuid4()),
    }

    # Malicious or confused actor signs attendance claims using the AUTH secret
    bad_token = jwt.encode(
        payload,
        settings.AUTH_SIGNING_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "attendance_qr", "kid": settings.ATTENDANCE_QR_SIGNING_KID},
    )

    with pytest.raises(InvalidQrTokenException) as exc_info:
        PresenceTokenEngine.verify_presence_token(token=bad_token, current_time=now)
    assert exc_info.value.code == "INVALID_QR_TOKEN"


def test_context_mismatch_rejection() -> None:
    """Token issued for one session/checkpoint/university cannot be used for another."""
    u1, u2 = uuid.uuid4(), uuid.uuid4()
    s1, s2 = uuid.uuid4(), uuid.uuid4()
    c1, c2 = uuid.uuid4(), uuid.uuid4()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)

    token, _, _, _ = PresenceTokenEngine.generate_presence_token(
        university_id=u1,
        session_id=s1,
        checkpoint_id=c1,
        checkpoint_type="START",
        current_time=now,
    )

    # University mismatch
    with pytest.raises(InvalidQrTokenException):
        PresenceTokenEngine.verify_presence_token(
            token=token, expected_university_id=u2, current_time=now
        )

    # Session mismatch
    with pytest.raises(InvalidQrTokenException):
        PresenceTokenEngine.verify_presence_token(
            token=token, expected_session_id=s2, current_time=now
        )

    # Checkpoint mismatch
    with pytest.raises(InvalidQrTokenException):
        PresenceTokenEngine.verify_presence_token(
            token=token, expected_checkpoint_id=c2, current_time=now
        )


def test_algorithm_none_rejection() -> None:
    """Tokens forged with alg: none must be rejected."""
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    payload = {
        "ver": 1,
        "typ": "attendance_qr",
        "uid": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "cid": str(uuid.uuid4()),
        "cpt": "START",
        "slot": 1,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(now.timestamp()) + 30,
        "jti": str(uuid.uuid4()),
    }
    none_token = jwt.encode(payload, key="", algorithm="none")

    with pytest.raises(InvalidQrTokenException):
        PresenceTokenEngine.verify_presence_token(token=none_token, current_time=now)


def test_unsupported_version_rejection() -> None:
    """Tokens with version != 1 must be rejected."""
    settings = get_settings()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    payload = {
        "ver": 2,  # Unsupported version
        "typ": "attendance_qr",
        "iss": settings.ATTENDANCE_QR_ISSUER,
        "aud": settings.ATTENDANCE_QR_AUDIENCE,
        "uid": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "cid": str(uuid.uuid4()),
        "cpt": "START",
        "slot": 1,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(now.timestamp()) + 30,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(
        payload,
        settings.ATTENDANCE_QR_SIGNING_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "attendance_qr", "kid": settings.ATTENDANCE_QR_SIGNING_KID},
    )

    with pytest.raises(InvalidQrTokenException) as exc_info:
        PresenceTokenEngine.verify_presence_token(token=token, current_time=now)
    assert "Unsupported token version" in exc_info.value.message


def test_wrong_typ_and_issuer_and_audience_rejections() -> None:
    """Tokens with invalid typ, issuer, or audience must be rejected."""
    settings = get_settings()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    base_payload = {
        "ver": 1,
        "typ": "attendance_qr",
        "iss": settings.ATTENDANCE_QR_ISSUER,
        "aud": settings.ATTENDANCE_QR_AUDIENCE,
        "uid": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "cid": str(uuid.uuid4()),
        "cpt": "START",
        "slot": 1,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(now.timestamp()) + 30,
        "jti": str(uuid.uuid4()),
    }

    # Wrong header typ
    token_bad_hdr_typ = jwt.encode(
        base_payload,
        settings.ATTENDANCE_QR_SIGNING_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "bad_typ", "kid": settings.ATTENDANCE_QR_SIGNING_KID},
    )
    with pytest.raises(InvalidQrTokenException):
        PresenceTokenEngine.verify_presence_token(token=token_bad_hdr_typ, current_time=now)

    # Wrong issuer
    bad_iss = dict(base_payload, iss="untrusted-issuer")
    token_bad_iss = jwt.encode(
        bad_iss,
        settings.ATTENDANCE_QR_SIGNING_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "attendance_qr", "kid": settings.ATTENDANCE_QR_SIGNING_KID},
    )
    with pytest.raises(InvalidQrTokenException):
        PresenceTokenEngine.verify_presence_token(token=token_bad_iss, current_time=now)

    # Wrong audience
    bad_aud = dict(base_payload, aud="wrong-audience")
    token_bad_aud = jwt.encode(
        bad_aud,
        settings.ATTENDANCE_QR_SIGNING_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "attendance_qr", "kid": settings.ATTENDANCE_QR_SIGNING_KID},
    )
    with pytest.raises(InvalidQrTokenException):
        PresenceTokenEngine.verify_presence_token(token=token_bad_aud, current_time=now)


def test_future_not_yet_valid_token_rejection() -> None:
    """Tokens with nbf in the future relative to server time must be rejected."""
    settings = get_settings()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    future_nbf = now + datetime.timedelta(seconds=60)
    payload = {
        "ver": 1,
        "typ": "attendance_qr",
        "iss": settings.ATTENDANCE_QR_ISSUER,
        "aud": settings.ATTENDANCE_QR_AUDIENCE,
        "uid": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "cid": str(uuid.uuid4()),
        "cpt": "START",
        "slot": 1,
        "iat": int(now.timestamp()),
        "nbf": int(future_nbf.timestamp()),
        "exp": int(future_nbf.timestamp()) + 30,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(
        payload,
        settings.ATTENDANCE_QR_SIGNING_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "attendance_qr", "kid": settings.ATTENDANCE_QR_SIGNING_KID},
    )

    with pytest.raises(InvalidQrTokenException) as exc_info:
        PresenceTokenEngine.verify_presence_token(token=token, current_time=now)
    assert exc_info.value.code == "INVALID_QR_TOKEN"


def test_checkpoint_type_mismatch_rejection() -> None:
    """Token generated for START cannot be verified against MIDDLE checkpoint type."""
    u_id = uuid.uuid4()
    s_id = uuid.uuid4()
    c_id = uuid.uuid4()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)

    token, _, _, _ = PresenceTokenEngine.generate_presence_token(
        university_id=u_id,
        session_id=s_id,
        checkpoint_id=c_id,
        checkpoint_type="START",
        current_time=now,
    )

    # Verifying with expected_checkpoint_type="START" -> passes
    claims = PresenceTokenEngine.verify_presence_token(
        token=token,
        expected_checkpoint_type="START",
        current_time=now,
    )
    assert claims["cpt"] == "START"

    # Verifying with expected_checkpoint_type="MIDDLE" -> rejected
    with pytest.raises(InvalidQrTokenException):
        PresenceTokenEngine.verify_presence_token(
            token=token,
            expected_checkpoint_type="MIDDLE",
            current_time=now,
        )


def test_kid_header_mandatory_and_validated() -> None:
    """Token must contain kid matching ATTENDANCE_QR_SIGNING_KID in protected header."""
    settings = get_settings()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)
    payload = {
        "ver": 1,
        "typ": "attendance_qr",
        "iss": settings.ATTENDANCE_QR_ISSUER,
        "aud": settings.ATTENDANCE_QR_AUDIENCE,
        "uid": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "cid": str(uuid.uuid4()),
        "cpt": "START",
        "slot": 1,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(now.timestamp()) + 30,
        "jti": str(uuid.uuid4()),
    }

    # Missing kid
    token_no_kid = jwt.encode(
        payload,
        settings.ATTENDANCE_QR_SIGNING_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "attendance_qr"},
    )
    with pytest.raises(InvalidQrTokenException) as exc_info:
        PresenceTokenEngine.verify_presence_token(token=token_no_kid, current_time=now)
    assert "key ID" in exc_info.value.message

    # Wrong kid
    token_wrong_kid = jwt.encode(
        payload,
        settings.ATTENDANCE_QR_SIGNING_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "attendance_qr", "kid": "unknown-key-id-999"},
    )
    with pytest.raises(InvalidQrTokenException) as exc_info:
        PresenceTokenEngine.verify_presence_token(token=token_wrong_kid, current_time=now)
    assert "key ID" in exc_info.value.message


def test_strict_immediate_expiration_at_exp_boundary() -> None:
    """Ensure zero post-expiry grace period: token is invalid immediately once exp is reached."""
    u_id = uuid.uuid4()
    s_id = uuid.uuid4()
    c_id = uuid.uuid4()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)

    token, _, exp_dt, _ = PresenceTokenEngine.generate_presence_token(
        university_id=u_id,
        session_id=s_id,
        checkpoint_id=c_id,
        checkpoint_type="START",
        current_time=now,
        rotation_seconds=20,
    )

    # 1 second before exp -> strictly valid
    valid_t = exp_dt - datetime.timedelta(seconds=1)
    claims = PresenceTokenEngine.verify_presence_token(token=token, current_time=valid_t)
    assert claims["cid"] == str(c_id)

    # Exactly at exp -> strictly expired immediately
    with pytest.raises(QrTokenExpiredException):
        PresenceTokenEngine.verify_presence_token(token=token, current_time=exp_dt)

    # 1 second past exp -> strictly expired immediately (no tolerance window)
    with pytest.raises(QrTokenExpiredException):
        PresenceTokenEngine.verify_presence_token(
            token=token, current_time=exp_dt + datetime.timedelta(seconds=1)
        )


def test_cryptographic_context_binding_rejection() -> None:
    """Verify cryptographic binding to university_id, session_id, and checkpoint_id."""
    u_id = uuid.uuid4()
    s_id = uuid.uuid4()
    c_id = uuid.uuid4()
    now = datetime.datetime(2026, 9, 14, 10, 0, 0, tzinfo=datetime.UTC)

    token, _, _, _ = PresenceTokenEngine.generate_presence_token(
        university_id=u_id,
        session_id=s_id,
        checkpoint_id=c_id,
        checkpoint_type="START",
        current_time=now,
    )

    # Wrong university ID -> rejected
    with pytest.raises(InvalidQrTokenException) as exc_u:
        PresenceTokenEngine.verify_presence_token(
            token=token,
            expected_university_id=uuid.uuid4(),
            current_time=now,
        )
    assert "university" in exc_u.value.message.lower()

    # Wrong session ID -> rejected
    with pytest.raises(InvalidQrTokenException) as exc_s:
        PresenceTokenEngine.verify_presence_token(
            token=token,
            expected_session_id=uuid.uuid4(),
            current_time=now,
        )
    assert "session" in exc_s.value.message.lower()

    # Wrong checkpoint ID -> rejected
    with pytest.raises(InvalidQrTokenException) as exc_c:
        PresenceTokenEngine.verify_presence_token(
            token=token,
            expected_checkpoint_id=uuid.uuid4(),
            current_time=now,
        )
    assert "checkpoint" in exc_c.value.message.lower()
