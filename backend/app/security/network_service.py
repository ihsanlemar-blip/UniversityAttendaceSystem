"""Campus Network Service managing zones and the short-lived network challenge lifecycle."""

import datetime
import ipaddress
import logging
import uuid

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.core.constants import (
    AttendanceSessionStatus,
    DeviceStatus,
    NetworkChallengeStatus,
    NetworkZoneStatus,
)
from backend.app.core.exceptions import (
    ConflictException,
    DomainException,
    NotFoundException,
)
from backend.app.devices.service import DeviceTrustService
from backend.app.models.attendance_checkpoint import AttendanceCheckpoint
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.campus_network import CampusNetworkChallenge, CampusNetworkZone
from backend.app.models.class_occurrence import ClassOccurrence
from backend.app.models.room import Room
from backend.app.models.student import Student
from backend.app.models.trusted_device import TrustedDevice
from backend.app.models.user import User
from backend.app.security.crypto import (
    generate_challenge_nonce,
    verify_network_proof_signature,
)
from backend.app.security.resolver import ClientNetworkResolver
from backend.app.security.schemas import (
    CampusNetworkZoneCreateRequest,
    CampusNetworkZoneResponse,
    CampusNetworkZoneUpdateRequest,
    NetworkChallengeResponse,
    NetworkProofSchema,
)

logger = logging.getLogger(__name__)


class CampusNetworkService:
    """Service governing campus network zones, challenges, and network-presence verification."""

    # =========================================================================
    # 1. Campus Network Zone CRUD
    # =========================================================================

    @staticmethod
    async def create_network_zone(
        db: AsyncSession,
        university_id: uuid.UUID,
        payload: CampusNetworkZoneCreateRequest,
    ) -> CampusNetworkZoneResponse:
        """Create a new campus network zone after validating CIDR syntax and code uniqueness."""
        # Validate CIDR
        try:
            net = ipaddress.ip_network(payload.network_cidr.strip(), strict=False)
            normalized_cidr = str(net)
            ip_ver = net.version
        except ValueError as exc:
            raise DomainException(
                code="INVALID_CIDR_FORMAT",
                message=f"Provided network CIDR is malformed: {exc}",
                status_code=400,
            ) from exc

        # Check unique code
        existing_stmt = select(CampusNetworkZone).where(
            CampusNetworkZone.university_id == university_id,
            CampusNetworkZone.code == payload.code.strip(),
        )
        existing_res = await db.execute(existing_stmt)
        if existing_res.scalar_one_or_none():
            raise ConflictException(
                code="NETWORK_ZONE_CODE_EXISTS",
                message=f"Network zone with code '{payload.code}' already exists.",
            )

        zone = CampusNetworkZone(
            university_id=university_id,
            building_id=payload.building_id,
            code=payload.code.strip(),
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            network_cidr=normalized_cidr,
            ip_version=ip_ver,
            zone_type=payload.zone_type,
            status=payload.status,
            allow_student_presence=payload.allow_student_presence,
            allow_lecturer_operations=payload.allow_lecturer_operations,
            priority=payload.priority,
        )
        db.add(zone)
        await db.commit()
        await db.refresh(zone)
        return CampusNetworkZoneResponse.model_validate(zone)

    @staticmethod
    async def update_network_zone(
        db: AsyncSession,
        zone_id: uuid.UUID,
        university_id: uuid.UUID,
        payload: CampusNetworkZoneUpdateRequest,
    ) -> CampusNetworkZoneResponse:
        """Update an existing campus network zone."""
        stmt = select(CampusNetworkZone).where(
            CampusNetworkZone.id == zone_id,
            CampusNetworkZone.university_id == university_id,
        )
        res = await db.execute(stmt)
        zone = res.scalar_one_or_none()
        if not zone:
            raise NotFoundException("CampusNetworkZone", zone_id)

        if payload.name is not None:
            zone.name = payload.name.strip()
        if payload.description is not None:
            zone.description = payload.description.strip() if payload.description else None
        if payload.network_cidr is not None:
            try:
                net = ipaddress.ip_network(payload.network_cidr.strip(), strict=False)
                zone.network_cidr = str(net)
                zone.ip_version = net.version
            except ValueError as exc:
                raise DomainException(
                    code="INVALID_CIDR_FORMAT",
                    message=f"Provided network CIDR is malformed: {exc}",
                    status_code=400,
                ) from exc
        if payload.building_id is not None:
            zone.building_id = payload.building_id
        if payload.zone_type is not None:
            zone.zone_type = payload.zone_type
        if payload.status is not None:
            zone.status = payload.status
        if payload.allow_student_presence is not None:
            zone.allow_student_presence = payload.allow_student_presence
        if payload.allow_lecturer_operations is not None:
            zone.allow_lecturer_operations = payload.allow_lecturer_operations
        if payload.priority is not None:
            zone.priority = payload.priority

        zone.updated_at = utc_now()
        await db.commit()
        await db.refresh(zone)
        return CampusNetworkZoneResponse.model_validate(zone)

    @staticmethod
    async def disable_network_zone(
        db: AsyncSession,
        zone_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> CampusNetworkZoneResponse:
        """Disable a campus network zone so it no longer satisfies presence."""
        stmt = select(CampusNetworkZone).where(
            CampusNetworkZone.id == zone_id,
            CampusNetworkZone.university_id == university_id,
        )
        res = await db.execute(stmt)
        zone = res.scalar_one_or_none()
        if not zone:
            raise NotFoundException("CampusNetworkZone", zone_id)

        zone.status = NetworkZoneStatus.DISABLED.value
        zone.updated_at = utc_now()
        await db.commit()
        await db.refresh(zone)
        return CampusNetworkZoneResponse.model_validate(zone)

    @staticmethod
    async def get_network_zone(
        db: AsyncSession,
        zone_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> CampusNetworkZoneResponse:
        """Fetch single campus network zone by ID scoped to university."""
        stmt = select(CampusNetworkZone).where(
            CampusNetworkZone.id == zone_id,
            CampusNetworkZone.university_id == university_id,
        )
        res = await db.execute(stmt)
        zone = res.scalar_one_or_none()
        if not zone:
            raise NotFoundException("CampusNetworkZone", zone_id)
        return CampusNetworkZoneResponse.model_validate(zone)

    @staticmethod
    async def list_network_zones(
        db: AsyncSession,
        university_id: uuid.UUID,
        status: str | None = None,
        building_id: uuid.UUID | None = None,
    ) -> list[CampusNetworkZoneResponse]:
        """List configured campus network zones for university."""
        stmt = select(CampusNetworkZone).where(CampusNetworkZone.university_id == university_id)
        if status:
            stmt = stmt.where(CampusNetworkZone.status == status)
        if building_id:
            stmt = stmt.where(CampusNetworkZone.building_id == building_id)

        stmt = stmt.order_by(CampusNetworkZone.priority.desc(), CampusNetworkZone.code.asc())
        res = await db.execute(stmt)
        return [CampusNetworkZoneResponse.model_validate(z) for z in res.scalars().all()]

    # =========================================================================
    # 2. Short-Lived Network Challenge Issuance
    # =========================================================================

    @staticmethod
    async def issue_network_challenge(
        db: AsyncSession,
        current_user: User,
        checkpoint_id: uuid.UUID,
        request: Request,
        current_time: datetime.datetime | None = None,
    ) -> NetworkChallengeResponse:
        """Issue a short-lived cryptographic presence challenge to authenticated student.

        Invariants Enforced:
        - Authenticated user must have an active Student profile (INV-01).
        - Student must possess an ACTIVE registered primary device (M13).
        - Checkpoint and AttendanceSession must be active/open (INV-03).
        - Effective client IP is server-observed; spoofed headers rejected.
        - Resolved zone must be ACTIVE and allow student presence.
        - Challenge bound to user, device, session, checkpoint, zone with 20s TTL.
        """
        now = current_time or utc_now()
        settings = get_settings()

        # 1. Resolve student profile
        stu_stmt = select(Student).where(
            Student.user_id == current_user.id,
            Student.university_id == current_user.university_id,
        )
        stu_res = await db.execute(stu_stmt)
        student = stu_res.scalar_one_or_none()
        if not student:
            raise DomainException(
                code="NOT_A_STUDENT",
                message="Only enrolled students may request campus network challenges.",
                status_code=403,
            )

        # 2. Verify student has an ACTIVE registered primary device
        active_device = await DeviceTrustService.get_student_active_device(
            db=db,
            student_id=student.id,
            university_id=current_user.university_id,
        )
        if not active_device or active_device.status != DeviceStatus.ACTIVE.value:
            raise DomainException(
                code="TRUSTED_DEVICE_REQUIRED",
                message="An active registered primary device is required for network challenge.",
                status_code=403,
            )

        # 3. Validate checkpoint and session context
        cp_stmt = select(AttendanceCheckpoint).where(
            AttendanceCheckpoint.id == checkpoint_id,
        )
        cp_res = await db.execute(cp_stmt)
        checkpoint = cp_res.scalar_one_or_none()
        if not checkpoint:
            raise NotFoundException("AttendanceCheckpoint", checkpoint_id)

        session_stmt = select(AttendanceSession).where(
            AttendanceSession.id == checkpoint.attendance_session_id,
            AttendanceSession.university_id == current_user.university_id,
        )
        sess_res = await db.execute(session_stmt)
        session = sess_res.scalar_one_or_none()
        if not session:
            raise NotFoundException("AttendanceSession", checkpoint.attendance_session_id)

        if session.status not in (
            AttendanceSessionStatus.ACTIVE.value,
            AttendanceSessionStatus.SCHEDULED.value,
        ):
            raise DomainException(
                code="SESSION_NOT_ACTIVE",
                message=f"Attendance session is {session.status}. Challenges cannot be issued.",
                status_code=400,
            )

        # Check occurrence building for scoping
        building_id: uuid.UUID | None = None
        if session.class_occurrence_id:
            occ_stmt = select(ClassOccurrence).where(
                ClassOccurrence.id == session.class_occurrence_id
            )
            occ_res = await db.execute(occ_stmt)
            occurrence = occ_res.scalar_one_or_none()
            if occurrence and occurrence.room_id:
                room = await db.get(Room, occurrence.room_id)
                building_id = room.building_id if room else None

        # 4. Resolve effective source IP
        effective_ip, is_forwarded, spoof_detected = (
            ClientNetworkResolver.extract_effective_client_ip(request)
        )

        # 5. Resolve matching CampusNetworkZone
        zone = await ClientNetworkResolver.match_campus_network_zone(
            db=db,
            university_id=current_user.university_id,
            client_ip=effective_ip,
            preferred_building_id=building_id,
            for_lecturer=False,
            allow_vpn=False,
        )

        if not zone:
            raise DomainException(
                code="NETWORK_NOT_TRUSTED",
                message=(
                    "Request did not originate from an authorized campus network zone. "
                    "Connect to university campus Wi-Fi and try again."
                ),
                status_code=403,
            )

        # 6. Generate secure nonce and challenge
        nonce, nonce_hash = generate_challenge_nonce()
        ttl = settings.ATTENDANCE_NETWORK_CHALLENGE_TTL_SECONDS
        expires_at = now + datetime.timedelta(seconds=ttl)

        challenge = CampusNetworkChallenge(
            university_id=current_user.university_id,
            user_id=current_user.id,
            trusted_device_id=active_device.id,
            attendance_session_id=session.id,
            attendance_checkpoint_id=checkpoint.id,
            network_zone_id=zone.id,
            nonce=nonce,
            nonce_hash=nonce_hash,
            status=NetworkChallengeStatus.ISSUED.value,
            issued_at=now,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        db.add(challenge)
        await db.commit()
        await db.refresh(challenge)

        return NetworkChallengeResponse(
            challenge_id=challenge.id,
            network_zone_id=zone.id,
            network_zone_name=zone.name,
            network_zone_code=zone.code,
            nonce=nonce,
            status=challenge.status,
            issued_at=challenge.issued_at,
            expires_at=challenge.expires_at,
            ttl_seconds=ttl,
        )

    # =========================================================================
    # 3. Network Proof Verification & Single-Use Consumption
    # =========================================================================

    @staticmethod
    async def verify_and_consume_network_proof(
        db: AsyncSession,
        current_user: User,
        network_proof: NetworkProofSchema,
        expected_session_id: uuid.UUID,
        expected_checkpoint_id: uuid.UUID,
        request: Request,
        current_time: datetime.datetime | None = None,
    ) -> CampusNetworkChallenge:
        """Verify Ed25519 signature over challenge, revalidate source network,
        and consume single-use.

        Invariants Enforced:
        - Challenge must exist and belong to authenticated student & university.
        - Challenge must match expected session and checkpoint.
        - Expiration strictly verified against server UTC clock.
        - Single-use consumption: replay rejected with NETWORK_PROOF_REPLAY_ATTEMPT signal.
        - HTTP idempotent retry: if same proof_id retries, return success without double-credit.
        - Source IP revalidated at submission: client must submit from the same/allowed zone.
        """
        now = current_time or utc_now()

        # 1. Fetch challenge with write lock
        c_stmt = (
            select(CampusNetworkChallenge)
            .where(
                CampusNetworkChallenge.id == network_proof.challenge_id,
                CampusNetworkChallenge.university_id == current_user.university_id,
                CampusNetworkChallenge.user_id == current_user.id,
            )
            .with_for_update()
        )
        c_res = await db.execute(c_stmt)
        challenge = c_res.scalar_one_or_none()
        if not challenge:
            raise DomainException(
                code="NETWORK_PROOF_INVALID",
                message="Network presence challenge not found or does not belong to student.",
                status_code=403,
            )

        # 2. Context binding check
        if (
            challenge.attendance_session_id != expected_session_id
            or challenge.attendance_checkpoint_id != expected_checkpoint_id
        ):
            raise DomainException(
                code="NETWORK_PROOF_INVALID",
                message="Network challenge is not valid for this session or checkpoint.",
                status_code=403,
            )

        # 3. Check single-use consumption and idempotency
        if challenge.status == NetworkChallengeStatus.CONSUMED.value:
            if challenge.proof_id == network_proof.proof_id:
                # Idempotent HTTP retry of the same proof
                return challenge
            # Replay attempt by a different proof_id
            raise DomainException(
                code="NETWORK_CHALLENGE_CONSUMED",
                message="Campus network challenge has already been consumed.",
                status_code=403,
            )

        # 4. Check expiration
        if now >= challenge.expires_at:
            challenge.status = NetworkChallengeStatus.EXPIRED.value
            challenge.updated_at = now
            await db.flush()
            raise DomainException(
                code="NETWORK_CHALLENGE_EXPIRED",
                message="Campus network presence challenge has expired. Request a new challenge.",
                status_code=403,
            )

        # 5. Verify registered primary device match
        if challenge.trusted_device_id != network_proof.trusted_device_id:
            raise DomainException(
                code="NETWORK_PROOF_INVALID",
                message="Proof trusted_device_id does not match the challenge device binding.",
                status_code=403,
            )

        # Load device public key
        dev_stmt = select(TrustedDevice).where(TrustedDevice.id == challenge.trusted_device_id)
        dev_res = await db.execute(dev_stmt)
        trusted_dev = dev_res.scalar_one_or_none()
        if not trusted_dev or trusted_dev.status != DeviceStatus.ACTIVE.value:
            raise DomainException(
                code="DEVICE_NOT_ACTIVE",
                message="Registered device is not in ACTIVE status.",
                status_code=403,
            )

        # 6. Verify Ed25519 signature
        verify_network_proof_signature(
            device_public_key=trusted_dev.public_key,
            challenge_id=challenge.id,
            nonce=challenge.nonce,
            user_id=challenge.user_id,
            university_id=challenge.university_id,
            trusted_device_id=challenge.trusted_device_id,
            attendance_session_id=challenge.attendance_session_id,
            attendance_checkpoint_id=challenge.attendance_checkpoint_id,
            network_zone_id=challenge.network_zone_id,
            issued_at=challenge.issued_at,
            expires_at=challenge.expires_at,
            signature=network_proof.signature,
        )

        # 7. Revalidate final check-in source network (Section 36 & 37)
        effective_ip, _, _ = ClientNetworkResolver.extract_effective_client_ip(request)
        final_zone = await ClientNetworkResolver.match_campus_network_zone(
            db=db,
            university_id=current_user.university_id,
            client_ip=effective_ip,
            allow_vpn=False,
        )

        if not final_zone:
            raise DomainException(
                code="NETWORK_NOT_TRUSTED",
                message="Final check-in submission was not received from a trusted campus network.",
                status_code=403,
            )

        if final_zone.id != challenge.network_zone_id:
            raise DomainException(
                code="NETWORK_ZONE_MISMATCH",
                message=(
                    f"Check-in submission network zone ({final_zone.code}) does not match "
                    f"the challenge network zone."
                ),
                status_code=403,
            )

        # 8. Mark challenge consumed
        challenge.status = NetworkChallengeStatus.CONSUMED.value
        challenge.consumed_at = now
        challenge.proof_id = network_proof.proof_id
        challenge.updated_at = now
        await db.flush()

        return challenge
