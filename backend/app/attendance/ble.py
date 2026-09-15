"""Cryptographic presence engine for Milestone 11 Bluetooth Low Energy (BLE) verification.

Invariants Enforced:
- INV-01: Client cannot mark itself present; only server-verified evidence grants credit.
- INV-03: University server UTC clock is sole authority for rotation and expiration.
- INV-04: Expired rotation slots or closed checkpoints rejected unconditionally.
- Cryptographic Separation: Uses dedicated ATTENDANCE_BLE_SIGNING_KEY isolated from
  AUTH_SIGNING_KEY and ATTENDANCE_QR_SIGNING_KEY.
- Zero Student PII: Broadcast contains strictly session/checkpoint context, never student data.
- Constant-Time Comparison: All authentication tag evaluations use hmac.compare_digest.
"""

import base64
import binascii
import datetime
import hashlib
import hmac
import struct
import uuid
from typing import Any

from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.core.exceptions import DomainException


class BleVerificationException(DomainException):
    """Raised when BLE payload is malformed, has invalid tag, or context mismatch."""

    def __init__(self, message: str = "Invalid or tampered BLE presence payload.") -> None:
        super().__init__(code="INVALID_BLE_PAYLOAD", message=message, status_code=400)


class BlePayloadExpiredException(DomainException):
    """Raised when BLE rotation slot has elapsed or checkpoint window closed."""

    def __init__(self, message: str = "BLE presence payload has expired.") -> None:
        super().__init__(code="BLE_PAYLOAD_EXPIRED", message=message, status_code=400)


class BleProtocolUnsupportedException(DomainException):
    """Raised when BLE payload protocol version is unsupported."""

    def __init__(self, message: str = "Unsupported BLE protocol version.") -> None:
        super().__init__(
            code="BLE_PROTOCOL_VERSION_UNSUPPORTED",
            message=message,
            status_code=400,
        )


class BleSignalTooWeakException(DomainException):
    """Raised when observed RSSI is weaker than configured policy threshold."""

    def __init__(self, message: str = "Observed BLE signal is below proximity threshold.") -> None:
        super().__init__(code="BLE_SIGNAL_TOO_WEAK", message=message, status_code=400)


def compute_ble_rotation_slot(now: datetime.datetime, rotation_seconds: int) -> int:
    """Compute deterministic rotation slot index from authoritative server UTC time."""
    if rotation_seconds <= 0:
        raise ValueError("rotation_seconds must be positive.")
    return int(now.timestamp() // rotation_seconds)


def compute_ble_token_expiry(
    now: datetime.datetime,
    rotation_seconds: int,
    checkpoint_close_utc: datetime.datetime | None = None,
) -> datetime.datetime:
    """Compute authoritative BLE payload expiration timestamp."""
    slot = compute_ble_rotation_slot(now, rotation_seconds)
    slot_end_ts = (slot + 1) * rotation_seconds
    slot_end_dt = datetime.datetime.fromtimestamp(slot_end_ts, tz=datetime.UTC)

    if checkpoint_close_utc is not None and checkpoint_close_utc < slot_end_dt:
        return checkpoint_close_utc
    return slot_end_dt


class BlePresenceEngine:
    """Compact cryptographic BLE presence advertisement and verification engine.

    Binary payload structure (17 bytes total):
    - Byte 0: Protocol version (uint8)
    - Bytes 1-4: Rotation slot (uint32 big-endian)
    - Bytes 5-16: 96-bit truncated HMAC-SHA256 authentication tag (12 bytes)
    """

    PAYLOAD_LENGTH: int = 17
    TAG_LENGTH: int = 12

    @staticmethod
    def _build_hmac_context(
        version: int,
        university_id: uuid.UUID,
        session_id: uuid.UUID,
        checkpoint_id: uuid.UUID,
        checkpoint_type: str,
        rotation_slot: int,
    ) -> bytes:
        """Construct deterministic binary context for HMAC-SHA256 authentication tag."""
        return (
            struct.pack(">B", version)
            + university_id.bytes
            + session_id.bytes
            + checkpoint_id.bytes
            + checkpoint_type.encode("utf-8")
            + struct.pack(">I", rotation_slot)
        )

    @staticmethod
    def generate_ble_advertisement_payload(
        university_id: uuid.UUID,
        session_id: uuid.UUID,
        checkpoint_id: uuid.UUID,
        checkpoint_type: str,
        checkpoint_close_utc: datetime.datetime | None = None,
        current_time: datetime.datetime | None = None,
        rotation_seconds: int | None = None,
    ) -> tuple[bytes, str, str, datetime.datetime, datetime.datetime, int]:
        """Generate a compact HMAC-signed BLE advertisement payload for classroom broadcast.

        Returns:
            (raw_bytes, payload_base64, payload_hex, issued_at_utc, expires_at_utc, rotation_slot)
        """
        settings = get_settings()
        rot_sec = rotation_seconds or settings.ATTENDANCE_BLE_ROTATION_SECONDS
        now = current_time or utc_now()
        slot = compute_ble_rotation_slot(now, rot_sec)
        exp_dt = compute_ble_token_expiry(now, rot_sec, checkpoint_close_utc)
        version = settings.ATTENDANCE_BLE_PROTOCOL_VERSION

        context = BlePresenceEngine._build_hmac_context(
            version=version,
            university_id=university_id,
            session_id=session_id,
            checkpoint_id=checkpoint_id,
            checkpoint_type=checkpoint_type,
            rotation_slot=slot,
        )

        key = settings.ATTENDANCE_BLE_SIGNING_KEY.encode("utf-8")
        full_tag = hmac.new(key, context, hashlib.sha256).digest()
        auth_tag = full_tag[: BlePresenceEngine.TAG_LENGTH]

        raw_payload = struct.pack(">BI", version, slot) + auth_tag
        payload_base64 = base64.b64encode(raw_payload).decode("ascii")
        payload_hex = raw_payload.hex()

        return raw_payload, payload_base64, payload_hex, now, exp_dt, slot

    @staticmethod
    def decode_raw_payload(payload_input: bytes | str) -> bytes:
        """Decode base64, hex, or raw bytes into 17-byte binary payload."""
        if isinstance(payload_input, bytes):
            return payload_input
        payload_str = payload_input.strip()

        # Try base64 decoding first
        try:
            decoded = base64.b64decode(payload_str, validate=True)
            if len(decoded) == BlePresenceEngine.PAYLOAD_LENGTH:
                return decoded
        except binascii.Error, ValueError:
            pass

        # Try hex decoding
        try:
            decoded = bytes.fromhex(payload_str)
            if len(decoded) == BlePresenceEngine.PAYLOAD_LENGTH:
                return decoded
        except ValueError:
            pass

        # If length matches directly (unpadded base64 or other)
        try:
            decoded = base64.urlsafe_b64decode(payload_str + "==")
            if len(decoded) == BlePresenceEngine.PAYLOAD_LENGTH:
                return decoded
        except binascii.Error, ValueError:
            pass

        raise BleVerificationException("Malformed or unparseable BLE payload format.")

    @staticmethod
    def verify_ble_observation(
        payload_input: bytes | str,
        expected_university_id: uuid.UUID,
        expected_session_id: uuid.UUID,
        expected_checkpoint_id: uuid.UUID,
        expected_checkpoint_type: str,
        current_time: datetime.datetime | None = None,
        observed_rssi: int | None = None,
        min_rssi: int | None = None,
        rotation_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Validate and authenticate a student-observed BLE presence payload.

        Enforces:
        - 17-byte compact binary structure
        - Protocol version matching (ver == 1)
        - Server UTC clock authoritative rotation slot matching
        - Constant-time HMAC-SHA256 authentication tag comparison
        - Full cryptographic context binding (university, session, checkpoint, type, slot)
        - Optional RSSI policy threshold verification
        """
        settings = get_settings()
        now = current_time or utc_now()
        rot_sec = rotation_seconds or settings.ATTENDANCE_BLE_ROTATION_SECONDS

        raw_payload = BlePresenceEngine.decode_raw_payload(payload_input)
        if len(raw_payload) != BlePresenceEngine.PAYLOAD_LENGTH:
            raise BleVerificationException(
                f"Invalid BLE payload length ({len(raw_payload)} bytes). "
                f"Expected {BlePresenceEngine.PAYLOAD_LENGTH} bytes."
            )

        version, slot = struct.unpack(">BI", raw_payload[:5])
        auth_tag = raw_payload[5:]

        # 1. Verify protocol version
        if version != settings.ATTENDANCE_BLE_PROTOCOL_VERSION:
            raise BleProtocolUnsupportedException(
                f"Unsupported BLE protocol version {version}. "
                f"Expected {settings.ATTENDANCE_BLE_PROTOCOL_VERSION}."
            )

        # 2. Verify rotation slot against authoritative server UTC clock
        current_slot = compute_ble_rotation_slot(now, rot_sec)
        if slot != current_slot:
            if slot < current_slot:
                raise BlePayloadExpiredException(
                    f"BLE payload slot {slot} has expired (current server slot: {current_slot})."
                )
            raise BleVerificationException(
                f"BLE payload slot {slot} is in the future (current server slot: {current_slot})."
            )

        # 3. Reconstruct context and verify HMAC tag using constant-time comparison
        expected_context = BlePresenceEngine._build_hmac_context(
            version=version,
            university_id=expected_university_id,
            session_id=expected_session_id,
            checkpoint_id=expected_checkpoint_id,
            checkpoint_type=expected_checkpoint_type,
            rotation_slot=slot,
        )

        key = settings.ATTENDANCE_BLE_SIGNING_KEY.encode("utf-8")
        expected_full_tag = hmac.new(key, expected_context, hashlib.sha256).digest()
        expected_tag = expected_full_tag[: BlePresenceEngine.TAG_LENGTH]

        if not hmac.compare_digest(auth_tag, expected_tag):
            raise BleVerificationException(
                "BLE authentication tag mismatch or cryptographic context mismatch."
            )

        # 4. Evaluate RSSI threshold policy if configured
        effective_min_rssi = min_rssi if min_rssi is not None else settings.ATTENDANCE_BLE_MIN_RSSI
        if effective_min_rssi is not None and observed_rssi is not None:
            if observed_rssi < effective_min_rssi:
                raise BleSignalTooWeakException(
                    f"Observed RSSI ({observed_rssi} dBm) is below proximity threshold "
                    f"({effective_min_rssi} dBm)."
                )

        payload_digest = hashlib.sha256(raw_payload).hexdigest()

        return {
            "version": version,
            "slot": slot,
            "university_id": str(expected_university_id),
            "session_id": str(expected_session_id),
            "checkpoint_id": str(expected_checkpoint_id),
            "checkpoint_type": expected_checkpoint_type,
            "payload_digest": payload_digest,
            "rssi": observed_rssi,
        }
