"""Cryptographic utilities for Milestone 14 Campus Network Presence Proofs.

Invariants Enforced:
- Network challenges are signed by the student's existing registered M13 Ed25519 key.
- Deterministic canonical payload serialization matching section 35 of specifications.
- Cryptographically secure random nonces.
"""

import datetime
import hashlib
import secrets
import uuid

from backend.app.devices.crypto import verify_device_signature


def generate_challenge_nonce() -> tuple[str, str]:
    """Generate a cryptographically secure 64-character hex nonce and its SHA-256 hash.

    Returns:
        tuple[nonce, nonce_hash]
    """
    nonce = secrets.token_hex(32)
    nonce_hash = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    return nonce, nonce_hash


def build_network_challenge_payload(
    challenge_id: uuid.UUID | str,
    nonce: str,
    user_id: uuid.UUID | str,
    university_id: uuid.UUID | str,
    trusted_device_id: uuid.UUID | str,
    attendance_session_id: uuid.UUID | str,
    attendance_checkpoint_id: uuid.UUID | str,
    network_zone_id: uuid.UUID | str,
    issued_at: datetime.datetime,
    expires_at: datetime.datetime,
) -> bytes:
    """Construct deterministic canonical bytes for campus network challenge signing.

    Format per section 35:
    NETWORK_PRESENCE_V1|{challenge_id}|{nonce}|{user_id}|{university_id}|{trusted_device_id}|{attendance_session_id}|{attendance_checkpoint_id}|{network_zone_id}|{issued_iso}|{expires_iso}
    """
    issued_iso = issued_at.astimezone(datetime.UTC).isoformat()
    expires_iso = expires_at.astimezone(datetime.UTC).isoformat()

    canonical_str = (
        f"NETWORK_PRESENCE_V1|{challenge_id}|{nonce}|{user_id}|{university_id}|"
        f"{trusted_device_id}|{attendance_session_id}|{attendance_checkpoint_id}|"
        f"{network_zone_id}|{issued_iso}|{expires_iso}"
    )
    return canonical_str.encode("utf-8")


def verify_network_proof_signature(
    device_public_key: str,
    challenge_id: uuid.UUID | str,
    nonce: str,
    user_id: uuid.UUID | str,
    university_id: uuid.UUID | str,
    trusted_device_id: uuid.UUID | str,
    attendance_session_id: uuid.UUID | str,
    attendance_checkpoint_id: uuid.UUID | str,
    network_zone_id: uuid.UUID | str,
    issued_at: datetime.datetime,
    expires_at: datetime.datetime,
    signature: str,
) -> bool:
    """Verify Ed25519 signature of student device over the canonical network challenge payload."""
    message_bytes = build_network_challenge_payload(
        challenge_id=challenge_id,
        nonce=nonce,
        user_id=user_id,
        university_id=university_id,
        trusted_device_id=trusted_device_id,
        attendance_session_id=attendance_session_id,
        attendance_checkpoint_id=attendance_checkpoint_id,
        network_zone_id=network_zone_id,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    return verify_device_signature(
        public_key_material=device_public_key,
        message_bytes=message_bytes,
        signature_input=signature,
    )


# Milestone 14 canonical aliases
canonical_network_proof_bytes = build_network_challenge_payload
verify_network_presence_signature = verify_network_proof_signature
