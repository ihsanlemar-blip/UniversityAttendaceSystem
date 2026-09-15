"""Cryptographic presence token engine for Milestone 10 Dynamic QR verification.

Invariants Enforced:
- INV-01: Client cannot mark itself present; only server-verified tokens grant credit.
- INV-03: University server UTC clock is sole authority for rotation and expiration.
- INV-04: Expired tokens (> rotation slot or past checkpoint close) rejected unconditionally.
- Cryptographic Separation: Uses dedicated ATTENDANCE_QR_SIGNING_KEY isolated from AUTH_SIGNING_KEY.
- Zero Student PII: Displayed classroom QR contains strictly class context, never student data.
"""

import datetime
import uuid
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError

from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.core.exceptions import DomainException


class InvalidQrTokenException(DomainException):
    """Raised when token is malformed, has invalid signature, or wrong context."""

    def __init__(self, message: str = "Invalid or malformed QR token.") -> None:
        super().__init__(code="INVALID_QR_TOKEN", message=message, status_code=400)


class QrTokenExpiredException(DomainException):
    """Raised when token rotation slot has elapsed or checkpoint window has closed."""

    def __init__(self, message: str = "QR token has expired.") -> None:
        super().__init__(code="QR_TOKEN_EXPIRED", message=message, status_code=400)


def compute_rotation_slot(now: datetime.datetime, rotation_seconds: int) -> int:
    """Compute deterministic rotation slot index from authoritative server time."""
    if rotation_seconds <= 0:
        raise ValueError("rotation_seconds must be positive.")
    return int(now.timestamp() // rotation_seconds)


def compute_token_expiry(
    now: datetime.datetime,
    rotation_seconds: int,
    checkpoint_close_utc: datetime.datetime | None = None,
) -> datetime.datetime:
    """Compute authoritative token expiration timestamp.

    Tokens expire at the boundary of the current rotation slot, or when the
    checkpoint window closes, whichever occurs first.
    """
    slot = compute_rotation_slot(now, rotation_seconds)
    slot_end_ts = (slot + 1) * rotation_seconds
    slot_end_dt = datetime.datetime.fromtimestamp(slot_end_ts, tz=datetime.UTC)

    if checkpoint_close_utc is not None and checkpoint_close_utc < slot_end_dt:
        return checkpoint_close_utc
    return slot_end_dt


class PresenceTokenEngine:
    """HMAC-signed short-lived dynamic QR presence token generation and verification."""

    @staticmethod
    def generate_presence_token(
        university_id: uuid.UUID,
        session_id: uuid.UUID,
        checkpoint_id: uuid.UUID,
        checkpoint_type: str,
        checkpoint_close_utc: datetime.datetime | None = None,
        current_time: datetime.datetime | None = None,
        rotation_seconds: int | None = None,
    ) -> tuple[str, datetime.datetime, datetime.datetime, int]:
        """Generate a signed dynamic QR presence token for classroom projection.

        Returns: (token_string, issued_at_utc, expires_at_utc, rotation_slot)
        """
        settings = get_settings()
        rot_sec = rotation_seconds or settings.ATTENDANCE_QR_ROTATION_SECONDS
        now = current_time or utc_now()
        slot = compute_rotation_slot(now, rot_sec)
        exp_dt = compute_token_expiry(now, rot_sec, checkpoint_close_utc)

        now_ts = int(now.timestamp())
        exp_ts = int(exp_dt.timestamp())

        payload: dict[str, Any] = {
            "ver": 1,
            "typ": "attendance_qr",
            "iss": settings.ATTENDANCE_QR_ISSUER,
            "aud": settings.ATTENDANCE_QR_AUDIENCE,
            "uid": str(university_id),
            "sid": str(session_id),
            "cid": str(checkpoint_id),
            "cpt": checkpoint_type,
            "slot": slot,
            "iat": now_ts,
            "nbf": now_ts,
            "exp": exp_ts,
            "jti": str(uuid.uuid4()),
        }

        headers = {
            "alg": "HS256",
            "typ": "attendance_qr",
            "kid": settings.ATTENDANCE_QR_SIGNING_KID,
        }

        token = jwt.encode(
            payload,
            settings.ATTENDANCE_QR_SIGNING_KEY,
            algorithm="HS256",
            headers=headers,
        )
        return token, now, exp_dt, slot

    @staticmethod
    def verify_presence_token(
        token: str,
        expected_university_id: uuid.UUID | None = None,
        expected_session_id: uuid.UUID | None = None,
        expected_checkpoint_id: uuid.UUID | None = None,
        expected_checkpoint_type: str | None = None,
        current_time: datetime.datetime | None = None,
    ) -> dict[str, Any]:
        """Validate and decode a dynamic attendance QR token.

        Enforces:
        - Strict algorithm enforcement (HS256 only)
        - Header typ and kid verification
        - HMAC signature verification using dedicated key
        - Issuer, audience, and required claims validation
        - Version validation (ver == 1)
        - Authoritative server-clock expiration and not-before checks
        - Tenant and context matching (university_id, session_id, checkpoint_id, checkpoint_type)
        """
        settings = get_settings()
        now = current_time or utc_now()
        now_ts = int(now.timestamp())

        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as e:
            raise InvalidQrTokenException("Malformed token header.") from e

        if unverified_header.get("alg") != "HS256":
            raise InvalidQrTokenException(
                f"Unsupported algorithm '{unverified_header.get('alg')}'. Only HS256 is permitted."
            )

        if unverified_header.get("typ") != "attendance_qr":
            raise InvalidQrTokenException(
                f"Invalid token typ '{unverified_header.get('typ')}'. Expected 'attendance_qr'."
            )

        kid = unverified_header.get("kid")
        if not kid or kid != settings.ATTENDANCE_QR_SIGNING_KID:
            raise InvalidQrTokenException("Invalid or missing key ID (kid).")

        try:
            # Decode with verify_exp=False to evaluate exp against authoritative server time
            payload = jwt.decode(
                token,
                settings.ATTENDANCE_QR_SIGNING_KEY,
                algorithms=["HS256"],
                issuer=settings.ATTENDANCE_QR_ISSUER,
                audience=settings.ATTENDANCE_QR_AUDIENCE,
                options={
                    "require": [
                        "ver",
                        "typ",
                        "uid",
                        "sid",
                        "cid",
                        "cpt",
                        "slot",
                        "iat",
                        "nbf",
                        "exp",
                        "jti",
                    ],
                    "verify_exp": False,
                    "verify_nbf": False,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )
        except jwt.InvalidIssuerError as e:
            raise InvalidQrTokenException("Invalid token issuer.") from e
        except jwt.InvalidAudienceError as e:
            raise InvalidQrTokenException("Invalid token audience.") from e
        except jwt.InvalidSignatureError as e:
            raise InvalidQrTokenException("Token signature verification failed.") from e
        except InvalidTokenError as e:
            raise InvalidQrTokenException("Malformed or invalid token.") from e

        if payload.get("typ") != "attendance_qr":
            raise InvalidQrTokenException("Payload typ must be 'attendance_qr'.")

        if payload.get("ver") != 1:
            raise InvalidQrTokenException(
                f"Unsupported token version '{payload.get('ver')}'. Only version 1 is supported."
            )

        exp_ts = payload.get("exp")
        if exp_ts is None or now_ts >= exp_ts:
            raise QrTokenExpiredException("QR token has expired.")

        nbf_ts = payload.get("nbf")
        if nbf_ts is not None and now_ts < nbf_ts:
            raise InvalidQrTokenException("QR token is not yet active.")

        if expected_university_id and payload.get("uid") != str(expected_university_id):
            raise InvalidQrTokenException(
                "Token university does not match current university context."
            )

        if expected_session_id and payload.get("sid") != str(expected_session_id):
            raise InvalidQrTokenException("Token session does not match requested session.")

        if expected_checkpoint_id and payload.get("cid") != str(expected_checkpoint_id):
            raise InvalidQrTokenException("Token checkpoint does not match requested checkpoint.")

        if expected_checkpoint_type and payload.get("cpt") != expected_checkpoint_type:
            raise InvalidQrTokenException(
                "Token checkpoint type does not match expected checkpoint type."
            )

        return payload
