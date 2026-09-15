"""Cryptographic utilities for Milestone 13: Student Device Registration & Primary Device Trust.

Invariants Enforced:
- Asymmetric proof of possession using Ed25519.
- Device private key never touches the backend.
- Canonical serialization of challenge and presence proof payloads.
- Canonical SHA-256 public key fingerprinting.
"""

import base64
import binascii
import datetime
import hashlib
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from backend.app.core.exceptions import DomainException


class DeviceCryptoException(DomainException):
    """Base exception for device cryptographic failures."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class InvalidDeviceSignatureException(DeviceCryptoException):
    """Raised when an Ed25519 device proof or registration signature is invalid."""

    def __init__(self, message: str = "Invalid device cryptographic signature.") -> None:
        super().__init__(code="DEVICE_PROOF_INVALID", message=message, status_code=403)


class MalformedDeviceKeyException(DeviceCryptoException):
    """Raised when an Ed25519 public key cannot be parsed."""

    def __init__(self, message: str = "Malformed or unsupported device public key.") -> None:
        super().__init__(code="MALFORMED_DEVICE_KEY", message=message, status_code=400)


# =============================================================================
# 1. Ed25519 Key Loading & Fingerprinting
# =============================================================================


def load_ed25519_public_key(
    key_material: str | bytes | ed25519.Ed25519PublicKey,
) -> ed25519.Ed25519PublicKey:
    """Load an Ed25519 public key from PEM, base64 raw 32-bytes, hex, or bytes."""
    if isinstance(key_material, ed25519.Ed25519PublicKey):
        return key_material

    if isinstance(key_material, bytes):
        if len(key_material) == 32:
            try:
                return ed25519.Ed25519PublicKey.from_public_bytes(key_material)
            except Exception as exc:
                raise MalformedDeviceKeyException(f"Failed to load raw 32-byte key: {exc}") from exc
        # Try decoding as string
        try:
            key_material = key_material.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MalformedDeviceKeyException("Non-UTF8 key material.") from exc

    clean = key_material.strip()
    if clean.startswith("-----BEGIN"):
        try:
            key = serialization.load_pem_public_key(clean.encode("utf-8"))
            if not isinstance(key, ed25519.Ed25519PublicKey):
                raise MalformedDeviceKeyException("Key is not an Ed25519 public key.")
            return key
        except Exception as exc:
            raise MalformedDeviceKeyException(f"Failed to parse PEM public key: {exc}") from exc

    # Try base64 decoding (standard 32-byte Ed25519 public key)
    try:
        decoded_b64 = base64.b64decode(clean, validate=True)
        if len(decoded_b64) == 32:
            return ed25519.Ed25519PublicKey.from_public_bytes(decoded_b64)
    except ValueError, binascii.Error:
        pass

    # Try hex decoding (64 hex characters = 32 bytes)
    try:
        if len(clean) == 64:
            decoded_hex = bytes.fromhex(clean)
            return ed25519.Ed25519PublicKey.from_public_bytes(decoded_hex)
    except ValueError:
        pass

    raise MalformedDeviceKeyException(
        "Unsupported public key format. Expected PEM, Base64, or Hex."
    )


def extract_raw_public_bytes(key_material: str | bytes | ed25519.Ed25519PublicKey) -> bytes:
    """Extract canonical 32 raw public bytes from an Ed25519 public key."""
    key = load_ed25519_public_key(key_material)
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def compute_public_key_fingerprint(
    key_material: str | bytes | ed25519.Ed25519PublicKey,
) -> str:
    """Compute canonical SHA-256 fingerprint over the 32 raw public key bytes.

    Returns 64-character lowercase hex string.
    """
    raw_bytes = extract_raw_public_bytes(key_material)
    return hashlib.sha256(raw_bytes).hexdigest().lower()


def export_public_key_pem(key: ed25519.Ed25519PublicKey) -> str:
    """Export an Ed25519 public key to standard SubjectPublicKeyInfo PEM."""
    return key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


# =============================================================================
# 2. Canonical Payload Serialization
# =============================================================================


def build_registration_challenge_payload(
    challenge_id: uuid.UUID | str,
    university_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    candidate_fingerprint: str,
    nonce: str,
    issued_at: datetime.datetime,
    expires_at: datetime.datetime,
) -> bytes:
    """Construct deterministic canonical bytes for device registration challenge signing.

    Format:
    DEVICE_REGISTRATION_V1|{challenge_id}|{university_id}|{user_id}|{fingerprint}|{nonce}|{issued_at}|{expires_at}
    """
    issued_iso = issued_at.astimezone(datetime.UTC).isoformat()
    expires_iso = expires_at.astimezone(datetime.UTC).isoformat()
    canonical_str = (
        f"DEVICE_REGISTRATION_V1|{challenge_id}|{university_id}|{user_id}|"
        f"{candidate_fingerprint.lower()}|{nonce}|{issued_iso}|{expires_iso}"
    )
    return canonical_str.encode("utf-8")


def build_online_device_proof_payload(
    user_id: uuid.UUID | str,
    university_id: uuid.UUID | str,
    device_id: uuid.UUID | str,
    proof_id: uuid.UUID | str,
    qr_token: str | None = None,
    ble_payload: str | None = None,
) -> bytes:
    """Construct deterministic canonical bytes for online attendance presence check-in.

    Format:
    DEVICE_PROOF_V1|ONLINE_PRESENCE_CHECKIN|{user_id}|{university_id}|{device_id}|{proof_id}|{qr_digest}|{ble_digest}
    """
    qr_digest = ""
    if qr_token and qr_token.strip():
        qr_digest = hashlib.sha256(qr_token.strip().encode("utf-8")).hexdigest()
    ble_digest = ""
    if ble_payload and ble_payload.strip():
        ble_digest = hashlib.sha256(ble_payload.strip().encode("utf-8")).hexdigest()

    canonical_str = (
        f"DEVICE_PROOF_V1|ONLINE_PRESENCE_CHECKIN|{user_id}|{university_id}|"
        f"{device_id}|{proof_id}|{qr_digest}|{ble_digest}"
    )
    return canonical_str.encode("utf-8")


def build_offline_device_proof_payload(
    user_id: uuid.UUID | str,
    university_id: uuid.UUID | str,
    device_id: uuid.UUID | str,
    claim_id: uuid.UUID | str,
    permit_id: uuid.UUID | str,
    authority_epoch: int,
    host_session_id: uuid.UUID | str | None,
    checkpoint_type: str,
    qr_challenge_token: str,
    ble_payload: str | None = None,
) -> bytes:
    """Construct deterministic canonical bytes for offline attendance claim capture.

    Format:
    DEVICE_PROOF_V1|OFFLINE_ATTENDANCE_CLAIM|{user_id}|{university_id}|{device_id}|{claim_id}|{permit_id}|{authority_epoch}|{host_session_id}|{checkpoint_type}|{qr_digest}|{ble_digest}
    """
    qr_digest = hashlib.sha256(qr_challenge_token.strip().encode("utf-8")).hexdigest()
    ble_digest = ""
    if ble_payload and ble_payload.strip():
        ble_digest = hashlib.sha256(ble_payload.strip().encode("utf-8")).hexdigest()

    host_str = str(host_session_id) if host_session_id else ""
    canonical_str = (
        f"DEVICE_PROOF_V1|OFFLINE_ATTENDANCE_CLAIM|{user_id}|{university_id}|"
        f"{device_id}|{claim_id}|{permit_id}|{authority_epoch}|{host_str}|"
        f"{checkpoint_type.upper()}|{qr_digest}|{ble_digest}"
    )
    return canonical_str.encode("utf-8")


# =============================================================================
# 3. Signature Verification
# =============================================================================


def decode_signature_bytes(signature_input: str | bytes) -> bytes:
    """Decode signature from base64, hex, or raw 64 bytes."""
    if isinstance(signature_input, bytes):
        if len(signature_input) == 64:
            return signature_input
        try:
            signature_input = signature_input.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidDeviceSignatureException("Non-UTF8 signature string.") from exc

    clean = signature_input.strip()

    # Try Base64
    try:
        decoded_b64 = base64.b64decode(clean, validate=True)
        if len(decoded_b64) == 64:
            return decoded_b64
    except ValueError, binascii.Error:
        pass

    # Try Hex (128 hex characters = 64 bytes)
    try:
        if len(clean) == 128:
            return bytes.fromhex(clean)
    except ValueError:
        pass

    raise InvalidDeviceSignatureException(
        "Invalid signature encoding. Expected 64 bytes in Base64 or Hex format."
    )


def verify_device_signature(
    public_key_material: str | bytes | ed25519.Ed25519PublicKey,
    message_bytes: bytes,
    signature_input: str | bytes,
) -> bool:
    """Verify an Ed25519 signature over canonical message bytes.

    Raises:
        InvalidDeviceSignatureException: If verification fails.
    """
    pub_key = load_ed25519_public_key(public_key_material)
    sig_bytes = decode_signature_bytes(signature_input)

    try:
        pub_key.verify(sig_bytes, message_bytes)
        return True
    except InvalidSignature as exc:
        raise InvalidDeviceSignatureException(
            "Device proof signature verification failed."
        ) from exc


# =============================================================================
# 4. Key Generation & Signing Helpers (Testing & Simulations)
# =============================================================================


def generate_device_keypair() -> tuple[str, str]:
    """Generate an Ed25519 keypair for unit tests and diagnostics.

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

    pub_pem = export_public_key_pem(public_key)
    return priv_pem, pub_pem


def sign_payload_with_private_key(
    private_key_material: str | bytes | ed25519.Ed25519PrivateKey,
    payload_bytes: bytes,
) -> str:
    """Sign message bytes with Ed25519 private key and return base64 signature."""
    if isinstance(private_key_material, ed25519.Ed25519PrivateKey):
        priv_key = private_key_material
    elif isinstance(private_key_material, bytes) and len(private_key_material) == 32:
        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_material)
    else:
        clean = (
            private_key_material.decode("utf-8")
            if isinstance(private_key_material, bytes)
            else private_key_material.strip()
        )
        if clean.startswith("-----BEGIN"):
            loaded_key = serialization.load_pem_private_key(clean.encode("utf-8"), password=None)
            if not isinstance(loaded_key, ed25519.Ed25519PrivateKey):
                raise MalformedDeviceKeyException("PEM does not contain an Ed25519 private key.")
            priv_key = loaded_key
        elif len(clean) == 64:
            priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(clean))
        else:
            decoded_b64 = base64.b64decode(clean, validate=True)
            priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(decoded_b64)

    sig = priv_key.sign(payload_bytes)
    return base64.b64encode(sig).decode("utf-8")
