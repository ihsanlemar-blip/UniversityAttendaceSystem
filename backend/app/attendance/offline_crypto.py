"""Cryptographic engine for Milestone 12: Offline Attendance & Signed Authority.

Invariants Enforced:
- INV-01: Client cannot mark itself present. Only backend verifies offline permits and evidence.
- INV-03: University server UTC clock is authoritative; monotonic anchor bounds offline session.
- INV-04: Expired dynamic offline challenges (past slot boundary or checkpoint window) rejected.
- Asymmetric Delegation: Server signs permits with Ed25519 server private key (never leaves server).
  Lecturer signs offline challenges and events with ephemeral Ed25519 key (bound in permit).
"""

import datetime
import hashlib
import json
import uuid
from typing import Any

import jwt
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from jwt.exceptions import InvalidTokenError

from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.core.exceptions import DomainException


class OfflineCryptoException(DomainException):
    """Base exception for offline cryptographic failures."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class InvalidOfflinePermitException(OfflineCryptoException):
    """Raised when an offline permit has an invalid signature, is expired, or corrupted."""

    def __init__(self, message: str = "Invalid or tampered offline attendance permit.") -> None:
        super().__init__(code="INVALID_OFFLINE_PERMIT", message=message, status_code=400)


class InvalidOfflineChallengeException(OfflineCryptoException):
    """Raised when an offline QR challenge has an invalid signature or invalid context."""

    def __init__(self, message: str = "Invalid or tampered offline presence challenge.") -> None:
        super().__init__(code="INVALID_OFFLINE_CHALLENGE", message=message, status_code=400)


class OfflineChallengeExpiredException(OfflineCryptoException):
    """Raised when an offline QR challenge has expired outside the allowable window."""

    def __init__(self, message: str = "Offline presence challenge has expired.") -> None:
        super().__init__(code="OFFLINE_CHALLENGE_EXPIRED", message=message, status_code=400)


class TamperedEventChainException(OfflineCryptoException):
    """Raised when a host session event chain has broken hashes or invalid signatures."""

    def __init__(self, message: str = "Tampered or corrupted offline event hash chain.") -> None:
        super().__init__(code="TAMPERED_EVENT_CHAIN", message=message, status_code=400)


class ClockRollbackException(OfflineCryptoException):
    """Raised when monotonic uptime decreased, indicating host reboot or tampering."""

    def __init__(self, message: str = "Host device monotonic clock rollback detected.") -> None:
        super().__init__(code="CLOCK_ROLLBACK_DETECTED", message=message, status_code=400)


# =============================================================================
# 1. Ed25519 Key Utilities
# =============================================================================


def generate_ed25519_keypair() -> tuple[str, str]:
    """Generate a fresh Ed25519 private/public keypair in PEM format.

    Returns:
        tuple[str, str]: (private_key_pem, public_key_pem)
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return priv_pem, pub_pem


def load_ed25519_private_key(key_material: str) -> ed25519.Ed25519PrivateKey:
    """Load an Ed25519 private key from PEM string or raw 32-byte hex/bytes."""
    clean = key_material.strip()
    if clean.startswith("-----BEGIN"):
        key = serialization.load_pem_private_key(clean.encode("utf-8"), password=None)
        if not isinstance(key, ed25519.Ed25519PrivateKey):
            raise OfflineCryptoException("INVALID_KEY_TYPE", "Key is not an Ed25519 private key.")
        return key

    # Raw 32-byte hex representation
    try:
        raw_bytes = bytes.fromhex(clean)
        return ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
    except Exception as exc:
        raise OfflineCryptoException(
            "MALFORMED_PRIVATE_KEY", f"Failed to load private key: {exc}"
        ) from exc


def load_ed25519_public_key(key_material: str) -> ed25519.Ed25519PublicKey:
    """Load an Ed25519 public key from PEM string or raw 32-byte hex/bytes."""
    clean = key_material.strip()
    if clean.startswith("-----BEGIN"):
        key = serialization.load_pem_public_key(clean.encode("utf-8"))
        if not isinstance(key, ed25519.Ed25519PublicKey):
            raise OfflineCryptoException("INVALID_KEY_TYPE", "Key is not an Ed25519 public key.")
        return key

    # Raw 32-byte hex representation
    try:
        raw_bytes = bytes.fromhex(clean)
        return ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)
    except Exception as exc:
        raise OfflineCryptoException(
            "MALFORMED_PUBLIC_KEY", f"Failed to load public key: {exc}"
        ) from exc


def export_public_key_pem(key: ed25519.Ed25519PublicKey) -> str:
    """Export an Ed25519 public key to PEM format."""
    return key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def export_public_key_hex(key: ed25519.Ed25519PublicKey) -> str:
    """Export an Ed25519 public key to 32-byte hex format."""
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


# =============================================================================
# 2. Monotonic Clock & Anchor Math (INV-03)
# =============================================================================


def estimate_server_time_from_anchor(
    anchor_server_utc: datetime.datetime,
    anchor_uptime_ms: int,
    current_uptime_ms: int,
    max_drift_seconds: int = 300,
) -> datetime.datetime:
    """Compute authoritative server time estimate using host monotonic uptime anchor.

    Formula:
        elapsed_seconds = (current_uptime_ms - anchor_uptime_ms) / 1000.0
        estimated_server_utc = anchor_server_utc + timedelta(seconds=elapsed_seconds)

    Rejects if current_uptime_ms < anchor_uptime_ms (device rebooted).
    """
    if current_uptime_ms < anchor_uptime_ms:
        raise ClockRollbackException(
            f"Device monotonic clock rolled back: current ({current_uptime_ms}) "
            f"< anchor ({anchor_uptime_ms}). Device may have rebooted."
        )

    elapsed_seconds = (current_uptime_ms - anchor_uptime_ms) / 1000.0
    return anchor_server_utc + datetime.timedelta(seconds=elapsed_seconds)


# =============================================================================
# 3. Offline Attendance Permit Engine
# =============================================================================


class OfflinePermitEngine:
    """Asymmetric Ed25519 permit signing and verification engine."""

    @staticmethod
    def compute_roster_snapshot_digest(student_ids: list[uuid.UUID]) -> str:
        """Compute SHA-256 digest of section roster for permit binding."""
        sorted_ids = sorted(str(s) for s in student_ids)
        canonical = json.dumps(sorted_ids, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_policy_snapshot_digest(policy_data: dict[str, Any]) -> str:
        """Compute SHA-256 digest of policy rules for permit binding."""
        canonical = json.dumps(policy_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def issue_permit_token(
        permit_id: uuid.UUID,
        university_id: uuid.UUID,
        session_id: uuid.UUID,
        occurrence_id: uuid.UUID,
        lecturer_id: uuid.UUID,
        temporary_host_public_key_pem: str,
        valid_from_utc: datetime.datetime,
        valid_until_utc: datetime.datetime,
        authority_epoch: int = 1,
        roster_snapshot_digest: str = "",
        policy_snapshot_digest: str = "",
        allowed_checkpoints: list[str] | None = None,
        private_key_pem: str | None = None,
    ) -> str:
        """Generate an Ed25519-signed OfflineAttendancePermit token."""
        settings = get_settings()
        priv_key_str = private_key_pem or settings.OFFLINE_PERMIT_SIGNING_PRIVATE_KEY
        priv_key = load_ed25519_private_key(priv_key_str)

        payload: dict[str, Any] = {
            "ver": 1,
            "typ": "offline_permit",
            "iss": settings.ATTENDANCE_QR_ISSUER,
            "pid": str(permit_id),
            "uid": str(university_id),
            "sid": str(session_id),
            "cid": str(occurrence_id),
            "lid": str(lecturer_id),
            "hpk": temporary_host_public_key_pem.strip(),
            "epc": authority_epoch,
            "rsd": roster_snapshot_digest,
            "psd": policy_snapshot_digest,
            "chk": allowed_checkpoints or ["START", "MIDDLE", "END"],
            "iat": int(valid_from_utc.timestamp()),
            "nbf": int(valid_from_utc.timestamp()),
            "exp": int(valid_until_utc.timestamp()),
            "jti": str(uuid.uuid4()),
        }

        headers = {
            "alg": "EdDSA",
            "typ": "offline_permit",
            "kid": settings.OFFLINE_PERMIT_SIGNING_KID,
        }

        return jwt.encode(payload, priv_key, algorithm="EdDSA", headers=headers)

    @staticmethod
    def verify_permit_token(
        token: str,
        public_key_pem: str | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> dict[str, Any]:
        """Verify an Ed25519-signed OfflineAttendancePermit token."""
        settings = get_settings()
        pub_key_str = public_key_pem or settings.OFFLINE_PERMIT_SIGNING_PUBLIC_KEY
        pub_key = load_ed25519_public_key(pub_key_str)

        try:
            payload = jwt.decode(
                token,
                pub_key,
                algorithms=["EdDSA"],
                issuer=settings.ATTENDANCE_QR_ISSUER,
                options={"verify_exp": False},
            )
        except InvalidTokenError as exc:
            raise InvalidOfflinePermitException(
                f"Permit signature verification failed: {exc}"
            ) from exc

        # Strict expiration check against authoritative time
        now = now_utc or utc_now()
        exp_ts = payload.get("exp")
        if exp_ts and now.timestamp() > exp_ts:
            raise InvalidOfflinePermitException(
                f"Permit has expired (expired at {exp_ts}, server time {int(now.timestamp())})."
            )

        nbf_ts = payload.get("nbf")
        if nbf_ts and now.timestamp() < nbf_ts:
            raise InvalidOfflinePermitException("Permit is not yet valid (before valid_from).")

        if payload.get("typ") != "offline_permit":
            raise InvalidOfflinePermitException("Invalid token type; expected 'offline_permit'.")

        return payload


# =============================================================================
# 4. Host Challenge Engine (Offline Dynamic QR)
# =============================================================================


class OfflineChallengeEngine:
    """Lecturer ephemeral Ed25519 signed dynamic QR challenge generation and verification."""

    @staticmethod
    def compute_rotation_slot(now: datetime.datetime, rotation_seconds: int = 20) -> int:
        """Compute deterministic rotation slot index."""
        if rotation_seconds <= 0:
            raise ValueError("rotation_seconds must be positive.")
        return int(now.timestamp() // rotation_seconds)

    @staticmethod
    def generate_challenge(
        permit_id: uuid.UUID,
        host_session_id: uuid.UUID,
        checkpoint_type: str,
        host_private_key: ed25519.Ed25519PrivateKey,
        ble_tag: bytes | None = None,
        current_time: datetime.datetime | None = None,
        rotation_seconds: int = 20,
    ) -> tuple[str, int, datetime.datetime, datetime.datetime, bytes]:
        """Generate a rotating dynamic QR challenge signed by lecturer ephemeral host key.

        Returns:
            tuple[token, rotation_slot, iat_utc, exp_utc, ble_tag]
        """
        now = current_time or utc_now()
        slot = OfflineChallengeEngine.compute_rotation_slot(now, rotation_seconds)
        slot_end_ts = (slot + 1) * rotation_seconds
        exp_dt = datetime.datetime.fromtimestamp(slot_end_ts, tz=datetime.UTC)

        # 12-byte matching BLE tag
        tag = ble_tag or hashlib.sha256(f"{host_session_id}:{slot}".encode()).digest()[:12]

        payload: dict[str, Any] = {
            "ver": 1,
            "typ": "offline_qr",
            "pid": str(permit_id),
            "hid": str(host_session_id),
            "cpt": checkpoint_type,
            "slot": slot,
            "ble": tag.hex(),
            "iat": int(now.timestamp()),
            "exp": int(exp_dt.timestamp()),
            "jti": str(uuid.uuid4()),
        }

        headers = {
            "alg": "EdDSA",
            "typ": "offline_qr",
        }

        token = jwt.encode(payload, host_private_key, algorithm="EdDSA", headers=headers)
        return token, slot, now, exp_dt, tag

    @staticmethod
    def verify_challenge(
        token: str,
        host_public_key_material: str,
        current_time: datetime.datetime | None = None,
        rotation_seconds: int = 20,
        tolerance_steps: int = 1,
    ) -> dict[str, Any]:
        """Verify an offline QR challenge against the host's temporary public key."""
        pub_key = load_ed25519_public_key(host_public_key_material)

        try:
            payload = jwt.decode(
                token,
                pub_key,
                algorithms=["EdDSA"],
                options={"verify_exp": False},
            )
        except InvalidTokenError as exc:
            raise InvalidOfflineChallengeException(
                f"Challenge signature verification failed: {exc}"
            ) from exc

        if payload.get("typ") != "offline_qr":
            raise InvalidOfflineChallengeException("Invalid challenge type; expected 'offline_qr'.")

        now = current_time or utc_now()
        expected_slot = OfflineChallengeEngine.compute_rotation_slot(now, rotation_seconds)
        token_slot = payload.get("slot", -1)

        # Expiry check with tolerance steps
        min_allowed_slot = expected_slot - tolerance_steps
        max_allowed_slot = expected_slot + tolerance_steps
        if not (min_allowed_slot <= token_slot <= max_allowed_slot):
            raise OfflineChallengeExpiredException(
                f"Challenge expired: slot {token_slot} outside allowable window "
                f"[{min_allowed_slot}, {max_allowed_slot}] for current time {now.isoformat()}."
            )

        return payload


# =============================================================================
# 5. Host Event Chain Engine
# =============================================================================


class EventChainEngine:
    """Tamper-evident append-only event hash-chain verification."""

    GENESIS_PREV_HASH: str = "0" * 64

    @staticmethod
    def compute_event_hash(
        prev_event_hash: str,
        sequence_number: int,
        event_type: str,
        payload: dict[str, Any],
        occurred_at_iso: str,
    ) -> str:
        """Compute cryptographic SHA-256 hash of an event in the chain."""
        canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        raw_message = (
            f"{prev_event_hash}:{sequence_number}:{event_type}:"
            f"{canonical_payload}:{occurred_at_iso}"
        )
        return hashlib.sha256(raw_message.encode("utf-8")).hexdigest()

    @staticmethod
    def sign_event_hash(
        event_hash: str,
        host_private_key: ed25519.Ed25519PrivateKey,
    ) -> str:
        """Sign event hash using ephemeral host private key."""
        sig = host_private_key.sign(event_hash.encode("utf-8"))
        return sig.hex()

    @staticmethod
    def verify_event_signature(
        event_hash: str,
        signature_hex: str,
        host_public_key: ed25519.Ed25519PublicKey,
    ) -> bool:
        """Verify Ed25519 signature of an event hash."""
        try:
            sig = bytes.fromhex(signature_hex)
            host_public_key.verify(sig, event_hash.encode("utf-8"))
            return True
        except InvalidSignature, ValueError:
            return False

    @staticmethod
    def verify_event_chain(
        events: list[dict[str, Any]],
        host_public_key_material: str,
    ) -> bool:
        """Verify that a sequence of host events forms a valid, unbroken, signed hash chain."""
        if not events:
            return True

        pub_key = load_ed25519_public_key(host_public_key_material)
        expected_prev_hash = EventChainEngine.GENESIS_PREV_HASH

        for idx, event in enumerate(events):
            seq = event.get("sequence_number")
            if seq != idx:
                raise TamperedEventChainException(
                    f"Invalid sequence number at index {idx}: expected {idx}, got {seq}."
                )

            prev_hash = event.get("prev_event_hash")
            if prev_hash != expected_prev_hash:
                raise TamperedEventChainException(
                    f"Broken hash chain at sequence {seq}: expected prev_hash "
                    f"'{expected_prev_hash}', got '{prev_hash}'."
                )

            event_type = event.get("event_type", "")
            payload = event.get("payload", {})
            occurred_at_iso = event.get("occurred_at_utc", "")
            expected_hash = EventChainEngine.compute_event_hash(
                prev_event_hash=prev_hash,
                sequence_number=seq,
                event_type=event_type,
                payload=payload,
                occurred_at_iso=occurred_at_iso,
            )

            actual_hash = event.get("event_hash", "")
            if actual_hash != expected_hash:
                raise TamperedEventChainException(
                    f"Hash mismatch at sequence {seq}: "
                    f"expected '{expected_hash}', got '{actual_hash}'."
                )

            signature = event.get("signature", "")
            if not EventChainEngine.verify_event_signature(actual_hash, signature, pub_key):
                raise TamperedEventChainException(
                    f"Invalid signature on event hash at sequence {seq}."
                )

            expected_prev_hash = actual_hash

        return True
