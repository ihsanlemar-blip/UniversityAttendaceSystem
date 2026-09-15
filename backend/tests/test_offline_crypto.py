"""Targeted tests for Milestone 12 Offline Attendance Cryptographic Engine."""

import datetime
import uuid

import pytest

from backend.app.attendance.offline_crypto import (
    ClockRollbackException,
    EventChainEngine,
    InvalidOfflinePermitException,
    OfflineChallengeEngine,
    OfflineChallengeExpiredException,
    OfflinePermitEngine,
    TamperedEventChainException,
    estimate_server_time_from_anchor,
    export_public_key_pem,
    generate_ed25519_keypair,
    load_ed25519_private_key,
    load_ed25519_public_key,
)


def test_ed25519_key_generation_and_loading() -> None:
    """Verify Ed25519 keypair generation and round-trip PEM loading."""
    priv_pem, pub_pem = generate_ed25519_keypair()

    priv_key = load_ed25519_private_key(priv_pem)
    pub_key = load_ed25519_public_key(pub_pem)

    assert priv_key is not None
    assert pub_key is not None

    exported_pub = export_public_key_pem(pub_key)
    assert exported_pub.strip() == pub_pem.strip()


def test_monotonic_clock_anchor_math() -> None:
    """Verify authoritative server time estimation from monotonic device uptime."""
    anchor_utc = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    anchor_uptime = 100_000  # 100 seconds uptime
    current_uptime = 120_000  # 20 seconds later

    estimated = estimate_server_time_from_anchor(
        anchor_server_utc=anchor_utc,
        anchor_uptime_ms=anchor_uptime,
        current_uptime_ms=current_uptime,
    )

    expected = datetime.datetime(2026, 9, 15, 10, 0, 20, tzinfo=datetime.UTC)
    assert estimated == expected


def test_monotonic_clock_rollback_detected() -> None:
    """Verify that uptime rollback (reboot) triggers ClockRollbackException."""
    anchor_utc = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    anchor_uptime = 100_000
    current_uptime = 50_000  # uptime decreased!

    with pytest.raises(ClockRollbackException):
        estimate_server_time_from_anchor(
            anchor_server_utc=anchor_utc,
            anchor_uptime_ms=anchor_uptime,
            current_uptime_ms=current_uptime,
        )


def test_offline_permit_issuance_and_verification() -> None:
    """Verify OfflinePermitEngine issue and verify flow."""
    server_priv_pem, server_pub_pem = generate_ed25519_keypair()
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()

    permit_id = uuid.uuid4()
    university_id = uuid.uuid4()
    session_id = uuid.uuid4()
    occurrence_id = uuid.uuid4()
    lecturer_id = uuid.uuid4()

    valid_from = datetime.datetime(2026, 9, 15, 8, 0, 0, tzinfo=datetime.UTC)
    valid_until = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.UTC)

    token = OfflinePermitEngine.issue_permit_token(
        permit_id=permit_id,
        university_id=university_id,
        session_id=session_id,
        occurrence_id=occurrence_id,
        lecturer_id=lecturer_id,
        temporary_host_public_key_pem=host_pub_pem,
        valid_from_utc=valid_from,
        valid_until_utc=valid_until,
        authority_epoch=1,
        roster_snapshot_digest="roster_sha256_mock",
        policy_snapshot_digest="policy_sha256_mock",
        private_key_pem=server_priv_pem,
    )

    # Valid check within window
    now = datetime.datetime(2026, 9, 15, 9, 30, 0, tzinfo=datetime.UTC)
    payload = OfflinePermitEngine.verify_permit_token(
        token=token,
        public_key_pem=server_pub_pem,
        now_utc=now,
    )

    assert payload["pid"] == str(permit_id)
    assert payload["uid"] == str(university_id)
    assert payload["sid"] == str(session_id)
    assert payload["lid"] == str(lecturer_id)
    assert payload["hpk"] == host_pub_pem.strip()
    assert payload["rsd"] == "roster_sha256_mock"
    assert payload["psd"] == "policy_sha256_mock"


def test_offline_permit_expired_rejected() -> None:
    """Verify expired permits are unconditionally rejected."""
    server_priv_pem, server_pub_pem = generate_ed25519_keypair()
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()

    valid_from = datetime.datetime(2026, 9, 15, 8, 0, 0, tzinfo=datetime.UTC)
    valid_until = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    token = OfflinePermitEngine.issue_permit_token(
        permit_id=uuid.uuid4(),
        university_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        occurrence_id=uuid.uuid4(),
        lecturer_id=uuid.uuid4(),
        temporary_host_public_key_pem=host_pub_pem,
        valid_from_utc=valid_from,
        valid_until_utc=valid_until,
        private_key_pem=server_priv_pem,
    )

    after_expiry = datetime.datetime(2026, 9, 15, 10, 0, 1, tzinfo=datetime.UTC)
    with pytest.raises(InvalidOfflinePermitException, match="Permit has expired"):
        OfflinePermitEngine.verify_permit_token(
            token=token,
            public_key_pem=server_pub_pem,
            now_utc=after_expiry,
        )


def test_offline_challenge_generation_and_verification() -> None:
    """Verify lecturer dynamic QR challenge generation and student verification."""
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()
    host_priv = load_ed25519_private_key(host_priv_pem)

    permit_id = uuid.uuid4()
    host_session_id = uuid.uuid4()

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 5, tzinfo=datetime.UTC)
    token, slot, iat, exp, ble_tag = OfflineChallengeEngine.generate_challenge(
        permit_id=permit_id,
        host_session_id=host_session_id,
        checkpoint_type="START",
        host_private_key=host_priv,
        current_time=t0,
        rotation_seconds=20,
    )

    assert len(ble_tag) == 12

    # Verify at t0 + 2s (same slot)
    payload = OfflineChallengeEngine.verify_challenge(
        token=token,
        host_public_key_material=host_pub_pem,
        current_time=t0 + datetime.timedelta(seconds=2),
        rotation_seconds=20,
    )

    assert payload["pid"] == str(permit_id)
    assert payload["hid"] == str(host_session_id)
    assert payload["cpt"] == "START"
    assert payload["slot"] == slot
    assert payload["ble"] == ble_tag.hex()


def test_offline_challenge_expiry() -> None:
    """Verify that challenges outside tolerance window raise OfflineChallengeExpiredException."""
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()
    host_priv = load_ed25519_private_key(host_priv_pem)

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    token, slot, iat, exp, _ = OfflineChallengeEngine.generate_challenge(
        permit_id=uuid.uuid4(),
        host_session_id=uuid.uuid4(),
        checkpoint_type="START",
        host_private_key=host_priv,
        current_time=t0,
        rotation_seconds=20,
    )

    # Fast-forward 3 slots (60 seconds) with tolerance=1
    t_future = t0 + datetime.timedelta(seconds=60)
    with pytest.raises(OfflineChallengeExpiredException):
        OfflineChallengeEngine.verify_challenge(
            token=token,
            host_public_key_material=host_pub_pem,
            current_time=t_future,
            rotation_seconds=20,
            tolerance_steps=1,
        )


def test_offline_challenge_expiration_boundaries() -> None:
    """Verify exact expiration boundary conditions: exp - 1s, exp exact, exp + 1s."""
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()
    host_priv = load_ed25519_private_key(host_priv_pem)

    t0 = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    token, slot, iat, exp_dt, _ = OfflineChallengeEngine.generate_challenge(
        permit_id=uuid.uuid4(),
        host_session_id=uuid.uuid4(),
        checkpoint_type="START",
        host_private_key=host_priv,
        current_time=t0,
        rotation_seconds=20,
    )

    # 1. exp - 1 second: MUST be valid
    t_valid = exp_dt - datetime.timedelta(seconds=1)
    verified = OfflineChallengeEngine.verify_challenge(
        token=token,
        host_public_key_material=host_pub_pem,
        current_time=t_valid,
        rotation_seconds=20,
        tolerance_steps=1,
    )
    assert verified["slot"] == slot

    # 2. exp exact: MUST be rejected
    with pytest.raises(OfflineChallengeExpiredException):
        OfflineChallengeEngine.verify_challenge(
            token=token,
            host_public_key_material=host_pub_pem,
            current_time=exp_dt,
            rotation_seconds=20,
            tolerance_steps=1,
        )

    # 3. exp + 1 second: MUST be rejected
    t_expired = exp_dt + datetime.timedelta(seconds=1)
    with pytest.raises(OfflineChallengeExpiredException):
        OfflineChallengeEngine.verify_challenge(
            token=token,
            host_public_key_material=host_pub_pem,
            current_time=t_expired,
            rotation_seconds=20,
            tolerance_steps=1,
        )


def test_offline_challenge_future_slot_rejected() -> None:
    """Verify that a challenge generated for a future slot is unconditionally rejected (INV-04)."""
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()
    host_priv = load_ed25519_private_key(host_priv_pem)

    t_now = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)
    # Generate token in future slot (+20s)
    t_future = t_now + datetime.timedelta(seconds=20)
    token, future_slot, _, _, _ = OfflineChallengeEngine.generate_challenge(
        permit_id=uuid.uuid4(),
        host_session_id=uuid.uuid4(),
        checkpoint_type="START",
        host_private_key=host_priv,
        current_time=t_future,
        rotation_seconds=20,
    )

    # Verifying at t_now (where expected_slot = future_slot - 1) MUST fail
    with pytest.raises(OfflineChallengeExpiredException, match="from the future"):
        OfflineChallengeEngine.verify_challenge(
            token=token,
            host_public_key_material=host_pub_pem,
            current_time=t_now,
            rotation_seconds=20,
            tolerance_steps=1,
        )


def test_event_chain_verification_and_tamper_detection() -> None:
    """Verify hash-chain formation and tamper-detection in EventChainEngine."""
    host_priv_pem, host_pub_pem = generate_ed25519_keypair()
    host_priv = load_ed25519_private_key(host_priv_pem)

    # Build 3 events
    events: list[dict] = []
    prev_hash = EventChainEngine.GENESIS_PREV_HASH

    event_types = ["SESSION_START", "CHECKPOINT_OPEN", "SESSION_END"]
    base_time = datetime.datetime(2026, 9, 15, 10, 0, 0, tzinfo=datetime.UTC)

    for seq, ev_type in enumerate(event_types):
        occ_iso = (base_time + datetime.timedelta(minutes=seq * 5)).isoformat()
        payload = {"data": f"payload_seq_{seq}"}
        ev_hash = EventChainEngine.compute_event_hash(
            prev_event_hash=prev_hash,
            sequence_number=seq,
            event_type=ev_type,
            payload=payload,
            occurred_at_iso=occ_iso,
        )
        sig = EventChainEngine.sign_event_hash(ev_hash, host_priv)
        events.append(
            {
                "sequence_number": seq,
                "event_type": ev_type,
                "prev_event_hash": prev_hash,
                "event_hash": ev_hash,
                "payload": payload,
                "signature": sig,
                "occurred_at_utc": occ_iso,
            }
        )
        prev_hash = ev_hash

    # Valid chain verification
    assert EventChainEngine.verify_event_chain(events, host_pub_pem) is True

    # Tampering payload of event 1
    tampered_events = [dict(e) for e in events]
    tampered_events[1]["payload"] = {"data": "tampered_data"}
    with pytest.raises(TamperedEventChainException, match="Hash mismatch"):
        EventChainEngine.verify_event_chain(tampered_events, host_pub_pem)

    # Tampering sequence number
    bad_seq_events = [dict(e) for e in events]
    bad_seq_events[2]["sequence_number"] = 99
    with pytest.raises(TamperedEventChainException, match="Invalid sequence number"):
        EventChainEngine.verify_event_chain(bad_seq_events, host_pub_pem)
