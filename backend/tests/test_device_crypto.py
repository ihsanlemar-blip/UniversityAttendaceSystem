"""Unit tests for Milestone 13 Device Cryptographic Utilities & Invariants."""

import base64
import datetime
import hashlib
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from backend.app.devices.crypto import (
    InvalidDeviceSignatureException,
    MalformedDeviceKeyException,
    build_offline_device_proof_payload,
    build_online_device_proof_payload,
    build_registration_challenge_payload,
    compute_public_key_fingerprint,
    decode_signature_bytes,
    extract_raw_public_bytes,
    generate_device_keypair,
    load_ed25519_public_key,
    sign_payload_with_private_key,
    verify_device_signature,
)


def test_ed25519_keypair_generation_and_export() -> None:
    """Verify Ed25519 keypair generation and PEM export format."""
    priv_pem, pub_pem = generate_device_keypair()

    assert priv_pem.startswith("-----" + "BEGIN " + "PRIVATE KEY-----")
    assert pub_pem.startswith("-----BEGIN PUBLIC KEY-----")

    pub_key = load_ed25519_public_key(pub_pem)
    assert isinstance(pub_key, ed25519.Ed25519PublicKey)


def test_ed25519_key_loading_formats() -> None:
    """Verify public key loading from PEM, base64 raw 32 bytes, hex, and raw bytes."""
    _, pub_pem = generate_device_keypair()
    pub_key = load_ed25519_public_key(pub_pem)

    raw_32_bytes = extract_raw_public_bytes(pub_key)
    assert len(raw_32_bytes) == 32

    # 1. From raw 32 bytes
    key_from_bytes = load_ed25519_public_key(raw_32_bytes)
    assert extract_raw_public_bytes(key_from_bytes) == raw_32_bytes

    # 2. From Base64 string
    b64_str = base64.b64encode(raw_32_bytes).decode("utf-8")
    key_from_b64 = load_ed25519_public_key(b64_str)
    assert extract_raw_public_bytes(key_from_b64) == raw_32_bytes

    # 3. From Hex string (64 characters)
    hex_str = raw_32_bytes.hex()
    key_from_hex = load_ed25519_public_key(hex_str)
    assert extract_raw_public_bytes(key_from_hex) == raw_32_bytes


def test_ed25519_key_loading_malformed() -> None:
    """Verify that invalid key material raises MalformedDeviceKeyException."""
    with pytest.raises(MalformedDeviceKeyException):
        load_ed25519_public_key("invalid_random_string_too_short")

    with pytest.raises(MalformedDeviceKeyException):
        load_ed25519_public_key(b"not_32_bytes")

    with pytest.raises(MalformedDeviceKeyException):
        load_ed25519_public_key("-----BEGIN PUBLIC KEY-----\ncorrupted\n-----END PUBLIC KEY-----")


def test_canonical_fingerprint_computation() -> None:
    """Verify SHA-256 fingerprint computation is canonical across formats."""
    _, pub_pem = generate_device_keypair()
    pub_key = load_ed25519_public_key(pub_pem)
    raw_32_bytes = extract_raw_public_bytes(pub_key)
    b64_str = base64.b64encode(raw_32_bytes).decode("utf-8")

    fp_pem = compute_public_key_fingerprint(pub_pem)
    fp_bytes = compute_public_key_fingerprint(raw_32_bytes)
    fp_b64 = compute_public_key_fingerprint(b64_str)

    expected_sha256 = hashlib.sha256(raw_32_bytes).hexdigest().lower()
    assert fp_pem == expected_sha256
    assert fp_bytes == expected_sha256
    assert fp_b64 == expected_sha256
    assert len(fp_pem) == 64


def test_registration_challenge_canonical_payload() -> None:
    """Verify deterministic canonical byte serialization of registration challenge."""
    challenge_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    univ_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    fp = "abcd" * 16
    nonce = "test-nonce-123"
    t_issue = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)
    t_exp = datetime.datetime(2026, 9, 15, 12, 5, 0, tzinfo=datetime.UTC)

    payload = build_registration_challenge_payload(
        challenge_id=challenge_id,
        university_id=univ_id,
        user_id=user_id,
        candidate_fingerprint=fp,
        nonce=nonce,
        issued_at=t_issue,
        expires_at=t_exp,
    )

    expected = (
        f"DEVICE_REGISTRATION_V1|{challenge_id}|{univ_id}|{user_id}|"
        f"{fp}|{nonce}|2026-09-15T12:00:00+00:00|2026-09-15T12:05:00+00:00"
    ).encode()
    assert payload == expected


def test_online_device_proof_canonical_payload() -> None:
    """Verify deterministic canonical byte serialization of online device proof."""
    user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    univ_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    device_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    proof_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    qr_token = "valid_qr_token_abc"
    ble_payload = "valid_ble_payload_xyz"

    payload = build_online_device_proof_payload(
        user_id=user_id,
        university_id=univ_id,
        device_id=device_id,
        proof_id=proof_id,
        qr_token=qr_token,
        ble_payload=ble_payload,
    )

    qr_digest = hashlib.sha256(qr_token.encode("utf-8")).hexdigest()
    ble_digest = hashlib.sha256(ble_payload.encode("utf-8")).hexdigest()

    expected = (
        f"DEVICE_PROOF_V1|ONLINE_PRESENCE_CHECKIN|{user_id}|{univ_id}|"
        f"{device_id}|{proof_id}|{qr_digest}|{ble_digest}"
    ).encode()
    assert payload == expected


def test_offline_device_proof_canonical_payload() -> None:
    """Verify deterministic canonical byte serialization of offline device claim proof."""
    user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    univ_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    device_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    claim_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    permit_id = uuid.UUID("77777777-7777-7777-7777-777777777777")
    host_session_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
    qr_token = "offline_challenge_qr"

    payload = build_offline_device_proof_payload(
        user_id=user_id,
        university_id=univ_id,
        device_id=device_id,
        claim_id=claim_id,
        permit_id=permit_id,
        authority_epoch=1,
        host_session_id=host_session_id,
        checkpoint_type="START",
        qr_challenge_token=qr_token,
        ble_payload=None,
    )

    qr_digest = hashlib.sha256(qr_token.encode("utf-8")).hexdigest()
    expected = (
        f"DEVICE_PROOF_V1|OFFLINE_ATTENDANCE_CLAIM|{user_id}|{univ_id}|"
        f"{device_id}|{claim_id}|{permit_id}|1|{host_session_id}|START|{qr_digest}|"
    ).encode()
    assert payload == expected


def test_signature_signing_and_verification_success() -> None:
    """Verify round-trip signing and verification using Ed25519 keypair."""
    priv_pem, pub_pem = generate_device_keypair()
    message = b"CANONICAL_MESSAGE_FOR_SIGNING"

    sig_b64 = sign_payload_with_private_key(priv_pem, message)
    assert isinstance(sig_b64, str)

    is_valid = verify_device_signature(pub_pem, message, sig_b64)
    assert is_valid is True


def test_signature_verification_tampered_payload_rejected() -> None:
    """Verify that tampering with message bytes causes verification failure."""
    priv_pem, pub_pem = generate_device_keypair()
    message = b"ORIGINAL_CANONICAL_MESSAGE"
    sig_b64 = sign_payload_with_private_key(priv_pem, message)

    tampered_message = b"TAMPERED_CANONICAL_MESSAGE"
    with pytest.raises(InvalidDeviceSignatureException):
        verify_device_signature(pub_pem, tampered_message, sig_b64)


def test_signature_verification_wrong_key_rejected() -> None:
    """Verify that validating against a different public key fails."""
    priv1, pub1 = generate_device_keypair()
    _, pub2 = generate_device_keypair()
    message = b"CANONICAL_MESSAGE"
    sig_b64 = sign_payload_with_private_key(priv1, message)

    with pytest.raises(InvalidDeviceSignatureException):
        verify_device_signature(pub2, message, sig_b64)


def test_decode_signature_bytes_formats() -> None:
    """Verify decode_signature_bytes handles base64, hex, and raw 64 bytes."""
    raw_sig = ed25519.Ed25519PrivateKey.generate().sign(b"test")
    assert len(raw_sig) == 64

    # Raw bytes
    assert decode_signature_bytes(raw_sig) == raw_sig

    # Base64
    b64_sig = base64.b64encode(raw_sig).decode("utf-8")
    assert decode_signature_bytes(b64_sig) == raw_sig

    # Hex
    hex_sig = raw_sig.hex()
    assert decode_signature_bytes(hex_sig) == raw_sig

    # Malformed
    with pytest.raises(InvalidDeviceSignatureException):
        decode_signature_bytes("short")
