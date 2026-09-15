"""Unit tests for Milestone 11 compact cryptographic BLE presence tokens."""

import base64
import datetime
import struct
import uuid

import pytest

from backend.app.attendance.ble import (
    BlePayloadExpiredException,
    BlePresenceEngine,
    BleSignalTooWeakException,
    BleVerificationException,
    compute_ble_rotation_slot,
)
from backend.app.core.config import get_settings


def test_compute_ble_rotation_slot_deterministic() -> None:
    """Verify rotation slot index matches integer division of UTC timestamp."""
    t0 = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)
    rot_sec = 20
    slot0 = compute_ble_rotation_slot(t0, rot_sec)
    assert slot0 == int(t0.timestamp() // 20)

    # 19 seconds later, same slot
    t1 = t0 + datetime.timedelta(seconds=19)
    assert compute_ble_rotation_slot(t1, rot_sec) == slot0

    # 20 seconds later, next slot
    t2 = t0 + datetime.timedelta(seconds=20)
    assert compute_ble_rotation_slot(t2, rot_sec) == slot0 + 1


def test_ble_token_generation_structure() -> None:
    """Verify BLE advertisement generates exactly 17 bytes binary payload."""
    uni_id = uuid.uuid4()
    sess_id = uuid.uuid4()
    cp_id = uuid.uuid4()
    cp_type = "START"
    t0 = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)

    raw, b64, hex_str, iat, exp, slot = BlePresenceEngine.generate_ble_advertisement_payload(
        university_id=uni_id,
        session_id=sess_id,
        checkpoint_id=cp_id,
        checkpoint_type=cp_type,
        current_time=t0,
        rotation_seconds=20,
    )

    assert len(raw) == 17
    assert len(base64.b64decode(b64)) == 17
    assert len(bytes.fromhex(hex_str)) == 17
    assert iat == t0
    assert exp > t0
    assert slot == int(t0.timestamp() // 20)

    # Inspect unpack
    ver, unpacked_slot = struct.unpack(">BI", raw[:5])
    assert ver == 1
    assert unpacked_slot == slot
    assert len(raw[5:]) == 12


def test_ble_token_verification_success_all_formats() -> None:
    """Verify BLE payload verifies successfully in raw bytes, base64, and hex."""
    uni_id = uuid.uuid4()
    sess_id = uuid.uuid4()
    cp_id = uuid.uuid4()
    cp_type = "MIDDLE"
    t0 = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)

    raw, b64, hex_str, _, _, slot = BlePresenceEngine.generate_ble_advertisement_payload(
        university_id=uni_id,
        session_id=sess_id,
        checkpoint_id=cp_id,
        checkpoint_type=cp_type,
        current_time=t0,
        rotation_seconds=20,
    )

    # 1. Verify raw bytes
    claims_raw = BlePresenceEngine.verify_ble_observation(
        payload_input=raw,
        expected_university_id=uni_id,
        expected_session_id=sess_id,
        expected_checkpoint_id=cp_id,
        expected_checkpoint_type=cp_type,
        current_time=t0,
        rotation_seconds=20,
    )
    assert claims_raw["slot"] == slot
    assert claims_raw["version"] == 1
    assert claims_raw["university_id"] == str(uni_id)
    assert claims_raw["session_id"] == str(sess_id)
    assert claims_raw["checkpoint_id"] == str(cp_id)
    assert claims_raw["checkpoint_type"] == cp_type

    # 2. Verify base64
    claims_b64 = BlePresenceEngine.verify_ble_observation(
        payload_input=b64,
        expected_university_id=uni_id,
        expected_session_id=sess_id,
        expected_checkpoint_id=cp_id,
        expected_checkpoint_type=cp_type,
        current_time=t0,
        rotation_seconds=20,
    )
    assert claims_b64["payload_digest"] == claims_raw["payload_digest"]

    # 3. Verify hex
    claims_hex = BlePresenceEngine.verify_ble_observation(
        payload_input=hex_str,
        expected_university_id=uni_id,
        expected_session_id=sess_id,
        expected_checkpoint_id=cp_id,
        expected_checkpoint_type=cp_type,
        current_time=t0,
        rotation_seconds=20,
    )
    assert claims_hex["payload_digest"] == claims_raw["payload_digest"]


def test_ble_token_rotation_and_expiry_zero_sleep() -> None:
    """Verify token in slot A expires when clock advances to slot B (instant test, zero sleep)."""
    uni_id = uuid.uuid4()
    sess_id = uuid.uuid4()
    cp_id = uuid.uuid4()
    cp_type = "START"
    t0 = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)

    raw_slot0, _, _, _, _, slot0 = BlePresenceEngine.generate_ble_advertisement_payload(
        university_id=uni_id,
        session_id=sess_id,
        checkpoint_id=cp_id,
        checkpoint_type=cp_type,
        current_time=t0,
        rotation_seconds=20,
    )

    # Advance clock by 20 seconds (slot 1)
    t1 = t0 + datetime.timedelta(seconds=20)
    raw_slot1, _, _, _, _, slot1 = BlePresenceEngine.generate_ble_advertisement_payload(
        university_id=uni_id,
        session_id=sess_id,
        checkpoint_id=cp_id,
        checkpoint_type=cp_type,
        current_time=t1,
        rotation_seconds=20,
    )

    assert slot1 == slot0 + 1
    assert raw_slot0 != raw_slot1

    # Verifying slot0 payload at time t1 must raise BlePayloadExpiredException
    with pytest.raises(BlePayloadExpiredException, match="has expired"):
        BlePresenceEngine.verify_ble_observation(
            payload_input=raw_slot0,
            expected_university_id=uni_id,
            expected_session_id=sess_id,
            expected_checkpoint_id=cp_id,
            expected_checkpoint_type=cp_type,
            current_time=t1,
            rotation_seconds=20,
        )

    # Verifying slot1 payload at time t1 succeeds
    verified = BlePresenceEngine.verify_ble_observation(
        payload_input=raw_slot1,
        expected_university_id=uni_id,
        expected_session_id=sess_id,
        expected_checkpoint_id=cp_id,
        expected_checkpoint_type=cp_type,
        current_time=t1,
        rotation_seconds=20,
    )
    assert verified["slot"] == slot1


def test_ble_token_tampered_tag_fails() -> None:
    """Verify changing any bit of the HMAC tag fails constant-time verification."""
    uni_id = uuid.uuid4()
    sess_id = uuid.uuid4()
    cp_id = uuid.uuid4()
    cp_type = "END"
    t0 = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)

    raw, _, _, _, _, _ = BlePresenceEngine.generate_ble_advertisement_payload(
        university_id=uni_id,
        session_id=sess_id,
        checkpoint_id=cp_id,
        checkpoint_type=cp_type,
        current_time=t0,
        rotation_seconds=20,
    )

    # Tamper last byte of the 17-byte payload
    tampered_bytes = bytearray(raw)
    tampered_bytes[-1] ^= 0xFF

    with pytest.raises(BleVerificationException, match="tag mismatch"):
        BlePresenceEngine.verify_ble_observation(
            payload_input=bytes(tampered_bytes),
            expected_university_id=uni_id,
            expected_session_id=sess_id,
            expected_checkpoint_id=cp_id,
            expected_checkpoint_type=cp_type,
            current_time=t0,
            rotation_seconds=20,
        )


def test_ble_token_context_mismatch_fails() -> None:
    """Verify payload generated for Session A / Checkpoint A cannot be verified for
    Session B / Checkpoint B.
    """
    uni_id = uuid.uuid4()
    sess_a = uuid.uuid4()
    sess_b = uuid.uuid4()
    cp_a = uuid.uuid4()
    cp_b = uuid.uuid4()
    t0 = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)

    raw, _, _, _, _, _ = BlePresenceEngine.generate_ble_advertisement_payload(
        university_id=uni_id,
        session_id=sess_a,
        checkpoint_id=cp_a,
        checkpoint_type="START",
        current_time=t0,
        rotation_seconds=20,
    )

    # 1. Wrong session
    with pytest.raises(
        BleVerificationException, match="tag mismatch or cryptographic context mismatch"
    ):
        BlePresenceEngine.verify_ble_observation(
            payload_input=raw,
            expected_university_id=uni_id,
            expected_session_id=sess_b,
            expected_checkpoint_id=cp_a,
            expected_checkpoint_type="START",
            current_time=t0,
            rotation_seconds=20,
        )

    # 2. Wrong checkpoint
    with pytest.raises(
        BleVerificationException, match="tag mismatch or cryptographic context mismatch"
    ):
        BlePresenceEngine.verify_ble_observation(
            payload_input=raw,
            expected_university_id=uni_id,
            expected_session_id=sess_a,
            expected_checkpoint_id=cp_b,
            expected_checkpoint_type="START",
            current_time=t0,
            rotation_seconds=20,
        )

    # 3. Wrong checkpoint type
    with pytest.raises(
        BleVerificationException, match="tag mismatch or cryptographic context mismatch"
    ):
        BlePresenceEngine.verify_ble_observation(
            payload_input=raw,
            expected_university_id=uni_id,
            expected_session_id=sess_a,
            expected_checkpoint_id=cp_a,
            expected_checkpoint_type="MIDDLE",
            current_time=t0,
            rotation_seconds=20,
        )

    # 4. Wrong university
    with pytest.raises(
        BleVerificationException, match="tag mismatch or cryptographic context mismatch"
    ):
        BlePresenceEngine.verify_ble_observation(
            payload_input=raw,
            expected_university_id=uuid.uuid4(),
            expected_session_id=sess_a,
            expected_checkpoint_id=cp_a,
            expected_checkpoint_type="START",
            current_time=t0,
            rotation_seconds=20,
        )


def test_ble_token_key_separation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify verifying with wrong signing key fails completely."""
    uni_id = uuid.uuid4()
    sess_id = uuid.uuid4()
    cp_id = uuid.uuid4()
    t0 = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)

    raw, _, _, _, _, _ = BlePresenceEngine.generate_ble_advertisement_payload(
        university_id=uni_id,
        session_id=sess_id,
        checkpoint_id=cp_id,
        checkpoint_type="START",
        current_time=t0,
        rotation_seconds=20,
    )

    settings = get_settings()
    monkeypatch.setattr(
        settings, "ATTENDANCE_BLE_SIGNING_KEY", "different-secret-key-32-chars-ok!!!"
    )

    with pytest.raises(BleVerificationException, match="tag mismatch"):
        BlePresenceEngine.verify_ble_observation(
            payload_input=raw,
            expected_university_id=uni_id,
            expected_session_id=sess_id,
            expected_checkpoint_id=cp_id,
            expected_checkpoint_type="START",
            current_time=t0,
            rotation_seconds=20,
        )


def test_ble_token_rssi_policy_threshold() -> None:
    """Verify RSSI threshold checks: signals weaker than threshold are rejected."""
    uni_id = uuid.uuid4()
    sess_id = uuid.uuid4()
    cp_id = uuid.uuid4()
    t0 = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)

    raw, _, _, _, _, _ = BlePresenceEngine.generate_ble_advertisement_payload(
        university_id=uni_id,
        session_id=sess_id,
        checkpoint_id=cp_id,
        checkpoint_type="START",
        current_time=t0,
        rotation_seconds=20,
    )

    # Threshold -85 dBm: -75 dBm (stronger) passes
    res = BlePresenceEngine.verify_ble_observation(
        payload_input=raw,
        expected_university_id=uni_id,
        expected_session_id=sess_id,
        expected_checkpoint_id=cp_id,
        expected_checkpoint_type="START",
        current_time=t0,
        observed_rssi=-75,
        min_rssi=-85,
    )
    assert res["rssi"] == -75

    # -85 dBm (boundary) passes
    res = BlePresenceEngine.verify_ble_observation(
        payload_input=raw,
        expected_university_id=uni_id,
        expected_session_id=sess_id,
        expected_checkpoint_id=cp_id,
        expected_checkpoint_type="START",
        current_time=t0,
        observed_rssi=-85,
        min_rssi=-85,
    )
    assert res["rssi"] == -85

    # -92 dBm (weaker) fails with BleSignalTooWeakException
    with pytest.raises(BleSignalTooWeakException, match="below proximity threshold"):
        BlePresenceEngine.verify_ble_observation(
            payload_input=raw,
            expected_university_id=uni_id,
            expected_session_id=sess_id,
            expected_checkpoint_id=cp_id,
            expected_checkpoint_type="START",
            current_time=t0,
            observed_rssi=-92,
            min_rssi=-85,
        )
