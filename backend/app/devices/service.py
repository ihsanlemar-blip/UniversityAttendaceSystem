"""Domain service for Milestone 13: Student Device Registration & Primary Device Trust."""

import datetime
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.core.constants import (
    DeviceReplacementStatus,
    DeviceRole,
    DeviceStatus,
    DeviceTrustEventType,
)
from backend.app.core.exceptions import ConflictException, DomainException, NotFoundException
from backend.app.devices.crypto import (
    build_online_device_proof_payload,
    build_registration_challenge_payload,
    compute_public_key_fingerprint,
    load_ed25519_public_key,
    verify_device_signature,
)
from backend.app.devices.schemas import (
    DeviceProofSchema,
    DeviceRegistrationChallengeRequest,
    DeviceRegistrationChallengeResponse,
    DeviceRegistrationConfirmRequest,
    DeviceReplacementCreateRequest,
    DeviceReplacementResponse,
    DeviceReplacementReviewRequest,
    DeviceStatusUpdateRequest,
    StudentDeviceStatusResponse,
    TrustedDeviceResponse,
)
from backend.app.models.student import Student
from backend.app.models.trusted_device import (
    DeviceRegistrationChallenge,
    DeviceReplacementRequest,
    DeviceTrustEvent,
    TrustedDevice,
)
from backend.app.models.user import User


class DeviceTrustService:
    """Core domain service for student device registration, proof of possession, and lifecycle."""

    # =========================================================================
    # 1. Device Queries & Status
    # =========================================================================

    @staticmethod
    async def get_student_active_device(
        db: AsyncSession,
        student_id: uuid.UUID,
        university_id: uuid.UUID,
    ) -> TrustedDevice | None:
        """Fetch the single ACTIVE primary device for a student."""
        stmt = select(TrustedDevice).where(
            TrustedDevice.student_id == student_id,
            TrustedDevice.university_id == university_id,
            TrustedDevice.status == DeviceStatus.ACTIVE.value,
            TrustedDevice.device_role == DeviceRole.PRIMARY.value,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_student_device_status(
        db: AsyncSession,
        current_user: User,
    ) -> StudentDeviceStatusResponse:
        """Return aggregated device status for the authenticated student."""
        student_stmt = select(Student).where(
            Student.user_id == current_user.id,
            Student.university_id == current_user.university_id,
        )
        s_res = await db.execute(student_stmt)
        student = s_res.scalar_one_or_none()
        if not student:
            return StudentDeviceStatusResponse(has_active_device=False)

        active_dev = await DeviceTrustService.get_student_active_device(
            db=db,
            student_id=student.id,
            university_id=current_user.university_id,
        )

        active_dev_dto: TrustedDeviceResponse | None = None
        if active_dev:
            active_dev_dto = TrustedDeviceResponse.model_validate(active_dev)
            fp = active_dev.public_key_fingerprint
            active_dev_dto.short_fingerprint = f"{fp[:6]}...{fp[-6:]}".upper()

        # Check pending replacement
        repl_stmt = (
            select(DeviceReplacementRequest)
            .where(
                DeviceReplacementRequest.student_id == student.id,
                DeviceReplacementRequest.status == DeviceReplacementStatus.PENDING.value,
            )
            .order_by(DeviceReplacementRequest.requested_at.desc())
        )
        r_res = await db.execute(repl_stmt)
        pending_repl = r_res.scalar_one_or_none()

        pending_repl_dto: DeviceReplacementResponse | None = None
        if pending_repl:
            pending_repl_dto = DeviceReplacementResponse.model_validate(pending_repl)

        return StudentDeviceStatusResponse(
            has_active_device=active_dev is not None,
            active_device=active_dev_dto,
            pending_replacement=pending_repl_dto,
        )

    # =========================================================================
    # 2. Device Registration Challenge & Confirmation
    # =========================================================================

    @staticmethod
    async def request_registration_challenge(
        db: AsyncSession,
        current_user: User,
        payload: DeviceRegistrationChallengeRequest,
        current_time: datetime.datetime | None = None,
    ) -> DeviceRegistrationChallengeResponse:
        """Issue a short-lived, single-use cryptographic registration challenge."""
        now = current_time or utc_now()
        settings = get_settings()

        # 1. Resolve student profile
        student_stmt = select(Student).where(
            Student.user_id == current_user.id,
            Student.university_id == current_user.university_id,
        )
        s_res = await db.execute(student_stmt)
        student = s_res.scalar_one_or_none()
        if not student:
            raise DomainException(
                code="NOT_A_STUDENT",
                message="Only enrolled students may register a primary attendance device.",
                status_code=403,
            )

        # 2. Validate and fingerprint candidate public key
        load_ed25519_public_key(payload.public_key)
        fingerprint = compute_public_key_fingerprint(payload.public_key)

        # 3. Verify public key is not already bound to another student (Section 25)
        existing_stmt = select(TrustedDevice).where(
            TrustedDevice.public_key_fingerprint == fingerprint,
            TrustedDevice.student_id != student.id,
        )
        existing_res = await db.execute(existing_stmt)
        if existing_res.scalar_one_or_none():
            raise ConflictException(
                code="DEVICE_ALREADY_BOUND_TO_ANOTHER_ACCOUNT",
                message="This device installation is already bound to another student account.",
            )

        # 4. Generate challenge
        challenge_id = uuid.uuid4()
        nonce = secrets.token_hex(32)
        expires_at = now + datetime.timedelta(
            seconds=settings.DEVICE_REGISTRATION_CHALLENGE_LIFETIME_SECONDS
        )

        canonical_bytes = build_registration_challenge_payload(
            challenge_id=challenge_id,
            university_id=current_user.university_id,
            user_id=current_user.id,
            candidate_fingerprint=fingerprint,
            nonce=nonce,
            issued_at=now,
            expires_at=expires_at,
        )
        canonical_str = canonical_bytes.decode("utf-8")

        challenge = DeviceRegistrationChallenge(
            id=challenge_id,
            university_id=current_user.university_id,
            user_id=current_user.id,
            student_id=student.id,
            candidate_public_key=payload.public_key.strip(),
            candidate_fingerprint=fingerprint,
            candidate_installation_id=payload.installation_id,
            platform=payload.platform,
            device_label=payload.device_label,
            app_version=payload.app_version,
            purpose="DEVICE_REGISTRATION",
            nonce=nonce,
            canonical_challenge=canonical_str,
            expires_at=expires_at,
            created_at=now,
        )
        db.add(challenge)
        await db.commit()

        return DeviceRegistrationChallengeResponse(
            challenge_id=challenge_id,
            canonical_challenge=canonical_str,
            expires_at=expires_at,
            candidate_fingerprint=fingerprint,
        )

    @staticmethod
    async def confirm_initial_registration(
        db: AsyncSession,
        current_user: User,
        payload: DeviceRegistrationConfirmRequest,
        current_time: datetime.datetime | None = None,
    ) -> TrustedDeviceResponse:
        """Confirm initial device registration with Ed25519 proof of possession."""
        now = current_time or utc_now()

        # 1. Resolve student profile
        student_stmt = select(Student).where(
            Student.user_id == current_user.id,
            Student.university_id == current_user.university_id,
        )
        s_res = await db.execute(student_stmt)
        student = s_res.scalar_one_or_none()
        if not student:
            raise DomainException(
                code="NOT_A_STUDENT",
                message="Only enrolled students may register a primary attendance device.",
                status_code=403,
            )

        # 2. Fetch challenge
        c_stmt = (
            select(DeviceRegistrationChallenge)
            .where(
                DeviceRegistrationChallenge.id == payload.challenge_id,
                DeviceRegistrationChallenge.user_id == current_user.id,
                DeviceRegistrationChallenge.university_id == current_user.university_id,
            )
            .with_for_update()
        )
        c_res = await db.execute(c_stmt)
        challenge = c_res.scalar_one_or_none()
        if not challenge:
            raise NotFoundException("DeviceRegistrationChallenge", payload.challenge_id)

        if challenge.used_at is not None:
            raise DomainException(
                code="DEVICE_REGISTRATION_CHALLENGE_USED",
                message="This registration challenge has already been used.",
                status_code=400,
            )

        if now >= challenge.expires_at:
            raise DomainException(
                code="DEVICE_REGISTRATION_CHALLENGE_EXPIRED",
                message="The registration challenge has expired.",
                status_code=400,
            )

        # 3. Verify asymmetric signature
        verify_device_signature(
            public_key_material=challenge.candidate_public_key,
            message_bytes=challenge.canonical_challenge.encode("utf-8"),
            signature_input=payload.signature,
        )

        # 4. Enforce ONE ACTIVE primary device rule
        existing_active = await DeviceTrustService.get_student_active_device(
            db=db,
            student_id=student.id,
            university_id=current_user.university_id,
        )
        if existing_active:
            raise DomainException(
                code="DEVICE_REPLACEMENT_REQUIRED",
                message=(
                    "Student already has an active primary device. "
                    "A device replacement request is required to activate a new phone."
                ),
                status_code=409,
            )

        # 5. Check if key already registered to another account
        bound_stmt = select(TrustedDevice).where(
            TrustedDevice.public_key_fingerprint == challenge.candidate_fingerprint,
            TrustedDevice.student_id != student.id,
        )
        bound_res = await db.execute(bound_stmt)
        if bound_res.scalar_one_or_none():
            raise ConflictException(
                code="DEVICE_ALREADY_BOUND_TO_ANOTHER_ACCOUNT",
                message="This device installation is already bound to another student account.",
            )

        # 6. Create or activate TrustedDevice
        device = TrustedDevice(
            id=uuid.uuid4(),
            university_id=current_user.university_id,
            user_id=current_user.id,
            student_id=student.id,
            device_role=DeviceRole.PRIMARY.value,
            public_key=challenge.candidate_public_key,
            public_key_fingerprint=challenge.candidate_fingerprint,
            installation_id=challenge.candidate_installation_id,
            platform=challenge.platform,
            device_label=challenge.device_label,
            app_version=challenge.app_version,
            status=DeviceStatus.ACTIVE.value,
            activated_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(device)

        # Mark challenge used
        challenge.used_at = now

        # 7. Audit log event
        audit_event = DeviceTrustEvent(
            id=uuid.uuid4(),
            university_id=current_user.university_id,
            target_user_id=current_user.id,
            target_student_id=student.id,
            device_id=device.id,
            event_type=DeviceTrustEventType.DEVICE_ACTIVATED.value,
            actor_user_id=current_user.id,
            reason="Initial self-registration verified via cryptographic proof of possession.",
            event_metadata={
                "fingerprint": challenge.candidate_fingerprint,
                "platform": challenge.platform,
                "device_label": challenge.device_label,
            },
            created_at=now,
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(device)

        dto = TrustedDeviceResponse.model_validate(device)
        dto.short_fingerprint = (
            f"{device.public_key_fingerprint[:6]}...{device.public_key_fingerprint[-6:]}".upper()
        )
        return dto

    # =========================================================================
    # 3. Device Replacement Workflow
    # =========================================================================

    @staticmethod
    async def request_device_replacement(
        db: AsyncSession,
        current_user: User,
        payload: DeviceReplacementCreateRequest,
        current_time: datetime.datetime | None = None,
    ) -> DeviceReplacementResponse:
        """Student initiates a replacement request for an existing active device."""
        now = current_time or utc_now()

        # 1. Resolve student profile
        student_stmt = select(Student).where(
            Student.user_id == current_user.id,
            Student.university_id == current_user.university_id,
        )
        s_res = await db.execute(student_stmt)
        student = s_res.scalar_one_or_none()
        if not student:
            raise DomainException(
                code="NOT_A_STUDENT", message="Only enrolled students may request replacement."
            )

        # 2. Check current active device
        active_device = await DeviceTrustService.get_student_active_device(
            db=db,
            student_id=student.id,
            university_id=current_user.university_id,
        )
        if not active_device:
            raise DomainException(
                code="NO_ACTIVE_DEVICE",
                message=(
                    "Student has no active registered device. Please perform initial registration."
                ),
                status_code=400,
            )

        # 3. Ensure no competing pending request
        pending_stmt = select(DeviceReplacementRequest).where(
            DeviceReplacementRequest.student_id == student.id,
            DeviceReplacementRequest.status == DeviceReplacementStatus.PENDING.value,
        )
        pending_res = await db.execute(pending_stmt)
        if pending_res.scalar_one_or_none():
            raise ConflictException(
                code="DEVICE_REPLACEMENT_PENDING",
                message="A device replacement request is already pending review.",
            )

        # 4. Fetch and verify candidate challenge
        c_stmt = (
            select(DeviceRegistrationChallenge)
            .where(
                DeviceRegistrationChallenge.id == payload.candidate_challenge_id,
                DeviceRegistrationChallenge.user_id == current_user.id,
                DeviceRegistrationChallenge.university_id == current_user.university_id,
            )
            .with_for_update()
        )
        c_res = await db.execute(c_stmt)
        challenge = c_res.scalar_one_or_none()
        if not challenge:
            raise NotFoundException("DeviceRegistrationChallenge", payload.candidate_challenge_id)

        if challenge.used_at is not None:
            raise DomainException(
                code="DEVICE_REGISTRATION_CHALLENGE_USED",
                message="Candidate challenge has already been used.",
                status_code=400,
            )

        if now >= challenge.expires_at:
            raise DomainException(
                code="DEVICE_REGISTRATION_CHALLENGE_EXPIRED",
                message="Candidate challenge has expired.",
                status_code=400,
            )

        # Verify candidate proof of possession
        verify_device_signature(
            public_key_material=challenge.candidate_public_key,
            message_bytes=challenge.canonical_challenge.encode("utf-8"),
            signature_input=payload.candidate_signature,
        )

        # Verify not same device
        if challenge.candidate_fingerprint == active_device.public_key_fingerprint:
            raise DomainException(
                code="SAME_DEVICE_REPLACEMENT",
                message="Candidate device key is already registered as your active device.",
                status_code=400,
            )

        # Verify candidate key not bound to another student
        bound_stmt = select(TrustedDevice).where(
            TrustedDevice.public_key_fingerprint == challenge.candidate_fingerprint,
            TrustedDevice.student_id != student.id,
        )
        bound_res = await db.execute(bound_stmt)
        if bound_res.scalar_one_or_none():
            raise ConflictException(
                code="DEVICE_ALREADY_BOUND_TO_ANOTHER_ACCOUNT",
                message="Candidate device is already bound to another student account.",
            )

        challenge.used_at = now

        # Create replacement request
        request = DeviceReplacementRequest(
            id=uuid.uuid4(),
            university_id=current_user.university_id,
            student_id=student.id,
            student_user_id=current_user.id,
            old_device_id=active_device.id,
            candidate_public_key=challenge.candidate_public_key,
            candidate_fingerprint=challenge.candidate_fingerprint,
            candidate_installation_id=challenge.candidate_installation_id,
            candidate_platform=challenge.platform,
            candidate_device_label=challenge.device_label,
            candidate_app_version=challenge.app_version,
            reason=payload.reason.strip(),
            status=DeviceReplacementStatus.PENDING.value,
            requested_at=now,
        )
        db.add(request)

        # Audit event
        audit_event = DeviceTrustEvent(
            id=uuid.uuid4(),
            university_id=current_user.university_id,
            target_user_id=current_user.id,
            target_student_id=student.id,
            device_id=active_device.id,
            replacement_request_id=request.id,
            event_type=DeviceTrustEventType.DEVICE_REPLACEMENT_REQUESTED.value,
            actor_user_id=current_user.id,
            reason=payload.reason.strip(),
            event_metadata={"candidate_fingerprint": challenge.candidate_fingerprint},
            created_at=now,
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(request)

        dto = DeviceReplacementResponse.model_validate(request)
        dto.old_device_fingerprint = active_device.public_key_fingerprint
        return dto

    @staticmethod
    async def approve_device_replacement(
        db: AsyncSession,
        request_id: uuid.UUID,
        reviewer_user: User,
        payload: DeviceReplacementReviewRequest,
        current_time: datetime.datetime | None = None,
    ) -> DeviceReplacementResponse:
        """Authorized staff reviews and atomically approves a device replacement request."""
        now = current_time or utc_now()

        req_stmt = (
            select(DeviceReplacementRequest)
            .where(
                DeviceReplacementRequest.id == request_id,
                DeviceReplacementRequest.university_id == reviewer_user.university_id,
            )
            .with_for_update()
        )
        r_res = await db.execute(req_stmt)
        repl_request = r_res.scalar_one_or_none()
        if not repl_request:
            raise NotFoundException("DeviceReplacementRequest", request_id)

        if repl_request.status != DeviceReplacementStatus.PENDING.value:
            raise DomainException(
                code="REPLACEMENT_NOT_PENDING",
                message=f"Request is already {repl_request.status}.",
                status_code=400,
            )

        # 1. Fetch and lock old active device
        old_dev_stmt = (
            select(TrustedDevice)
            .where(
                TrustedDevice.id == repl_request.old_device_id,
                TrustedDevice.university_id == reviewer_user.university_id,
            )
            .with_for_update()
        )
        old_res = await db.execute(old_dev_stmt)
        old_device = old_res.scalar_one_or_none()
        if not old_device:
            raise NotFoundException("TrustedDevice", repl_request.old_device_id)

        # 2. Deactivate old active device to satisfy partial unique index
        new_device_id = uuid.uuid4()
        old_device.status = DeviceStatus.REPLACED.value
        old_device.replaced_at = now
        old_device.updated_at = now
        await db.flush()

        # 3. Create and activate candidate device
        new_device = TrustedDevice(
            id=new_device_id,
            university_id=reviewer_user.university_id,
            user_id=repl_request.student_user_id,
            student_id=repl_request.student_id,
            device_role=DeviceRole.PRIMARY.value,
            public_key=repl_request.candidate_public_key,
            public_key_fingerprint=repl_request.candidate_fingerprint,
            installation_id=repl_request.candidate_installation_id,
            platform=repl_request.candidate_platform,
            device_label=repl_request.candidate_device_label,
            app_version=repl_request.candidate_app_version,
            status=DeviceStatus.ACTIVE.value,
            activated_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(new_device)
        await db.flush()

        # 4. Bind foreign key linkage to new device
        old_device.replaced_by_device_id = new_device.id

        # 4. Mark request approved
        repl_request.status = DeviceReplacementStatus.APPROVED.value
        repl_request.reviewed_at = now
        repl_request.reviewed_by_user_id = reviewer_user.id
        repl_request.review_note = payload.review_note
        repl_request.approved_device_id = new_device.id

        # 5. Append audit event
        audit_event = DeviceTrustEvent(
            id=uuid.uuid4(),
            university_id=reviewer_user.university_id,
            target_user_id=repl_request.student_user_id,
            target_student_id=repl_request.student_id,
            device_id=new_device.id,
            replacement_request_id=repl_request.id,
            event_type=DeviceTrustEventType.DEVICE_REPLACEMENT_APPROVED.value,
            actor_user_id=reviewer_user.id,
            reason=payload.review_note or "Device replacement approved by university staff.",
            event_metadata={
                "old_device_id": str(old_device.id),
                "new_device_id": str(new_device.id),
                "candidate_fingerprint": repl_request.candidate_fingerprint,
            },
            created_at=now,
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(repl_request)

        dto = DeviceReplacementResponse.model_validate(repl_request)
        dto.old_device_fingerprint = old_device.public_key_fingerprint
        return dto

    @staticmethod
    async def reject_device_replacement(
        db: AsyncSession,
        request_id: uuid.UUID,
        reviewer_user: User,
        payload: DeviceReplacementReviewRequest,
        current_time: datetime.datetime | None = None,
    ) -> DeviceReplacementResponse:
        """Authorized staff rejects a device replacement request with note."""
        now = current_time or utc_now()

        req_stmt = (
            select(DeviceReplacementRequest)
            .where(
                DeviceReplacementRequest.id == request_id,
                DeviceReplacementRequest.university_id == reviewer_user.university_id,
            )
            .with_for_update()
        )
        r_res = await db.execute(req_stmt)
        repl_request = r_res.scalar_one_or_none()
        if not repl_request:
            raise NotFoundException("DeviceReplacementRequest", request_id)

        if repl_request.status != DeviceReplacementStatus.PENDING.value:
            raise DomainException(
                code="REPLACEMENT_NOT_PENDING",
                message=f"Request is already {repl_request.status}.",
                status_code=400,
            )

        repl_request.status = DeviceReplacementStatus.REJECTED.value
        repl_request.reviewed_at = now
        repl_request.reviewed_by_user_id = reviewer_user.id
        repl_request.review_note = payload.review_note

        audit_event = DeviceTrustEvent(
            id=uuid.uuid4(),
            university_id=reviewer_user.university_id,
            target_user_id=repl_request.student_user_id,
            target_student_id=repl_request.student_id,
            device_id=repl_request.old_device_id,
            replacement_request_id=repl_request.id,
            event_type=DeviceTrustEventType.DEVICE_REPLACEMENT_REJECTED.value,
            actor_user_id=reviewer_user.id,
            reason=payload.review_note or "Device replacement rejected.",
            created_at=now,
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(repl_request)
        return DeviceReplacementResponse.model_validate(repl_request)

    # =========================================================================
    # 4. Lost & Administrative Lifecycle Operations
    # =========================================================================

    @staticmethod
    async def report_device_lost(
        db: AsyncSession,
        current_user: User,
        current_time: datetime.datetime | None = None,
    ) -> TrustedDeviceResponse:
        """Student reports active device lost/stolen, immediately transitioning to SUSPENDED."""
        now = current_time or utc_now()

        student_stmt = select(Student).where(
            Student.user_id == current_user.id,
            Student.university_id == current_user.university_id,
        )
        s_res = await db.execute(student_stmt)
        student = s_res.scalar_one_or_none()
        if not student:
            raise DomainException(
                code="NOT_A_STUDENT", message="Only enrolled students may report lost devices."
            )

        active_device = await DeviceTrustService.get_student_active_device(
            db=db,
            student_id=student.id,
            university_id=current_user.university_id,
        )
        if not active_device:
            raise DomainException(
                code="NO_ACTIVE_DEVICE", message="No active device found to report lost."
            )

        active_device.status = DeviceStatus.SUSPENDED.value
        active_device.suspended_at = now
        active_device.updated_at = now

        audit_event = DeviceTrustEvent(
            id=uuid.uuid4(),
            university_id=current_user.university_id,
            target_user_id=current_user.id,
            target_student_id=student.id,
            device_id=active_device.id,
            event_type=DeviceTrustEventType.DEVICE_SUSPENDED.value,
            actor_user_id=current_user.id,
            reason="Student reported device lost or stolen. Attendance check-in disabled.",
            created_at=now,
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(active_device)

        dto = TrustedDeviceResponse.model_validate(active_device)
        fp = active_device.public_key_fingerprint
        dto.short_fingerprint = f"{fp[:6]}...{fp[-6:]}".upper()
        return dto

    @staticmethod
    async def suspend_device(
        db: AsyncSession,
        device_id: uuid.UUID,
        actor_user: User,
        payload: DeviceStatusUpdateRequest,
        current_time: datetime.datetime | None = None,
    ) -> TrustedDeviceResponse:
        """Administratively suspend a registered student device."""
        now = current_time or utc_now()

        stmt = select(TrustedDevice).where(
            TrustedDevice.id == device_id,
            TrustedDevice.university_id == actor_user.university_id,
        )
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()
        if not device:
            raise NotFoundException("TrustedDevice", device_id)

        device.status = DeviceStatus.SUSPENDED.value
        device.suspended_at = now
        device.updated_at = now

        audit_event = DeviceTrustEvent(
            id=uuid.uuid4(),
            university_id=actor_user.university_id,
            target_user_id=device.user_id,
            target_student_id=device.student_id,
            device_id=device.id,
            event_type=DeviceTrustEventType.DEVICE_SUSPENDED.value,
            actor_user_id=actor_user.id,
            reason=payload.reason,
            created_at=now,
        )
        db.add(audit_event)
        await db.commit()
        await db.refresh(device)

        dto = TrustedDeviceResponse.model_validate(device)
        dto.short_fingerprint = (
            f"{device.public_key_fingerprint[:6]}...{device.public_key_fingerprint[-6:]}".upper()
        )
        return dto

    @staticmethod
    async def revoke_device(
        db: AsyncSession,
        device_id: uuid.UUID,
        actor_user: User,
        payload: DeviceStatusUpdateRequest,
        current_time: datetime.datetime | None = None,
    ) -> TrustedDeviceResponse:
        """Administratively revoke or mark a student device compromised."""
        now = current_time or utc_now()

        stmt = select(TrustedDevice).where(
            TrustedDevice.id == device_id,
            TrustedDevice.university_id == actor_user.university_id,
        )
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()
        if not device:
            raise NotFoundException("TrustedDevice", device_id)

        device.status = DeviceStatus.REVOKED.value
        device.revoked_at = now
        device.updated_at = now

        audit_event = DeviceTrustEvent(
            id=uuid.uuid4(),
            university_id=actor_user.university_id,
            target_user_id=device.user_id,
            target_student_id=device.student_id,
            device_id=device.id,
            event_type=DeviceTrustEventType.DEVICE_REVOKED.value,
            actor_user_id=actor_user.id,
            reason=payload.reason,
            created_at=now,
        )
        db.add(audit_event)
        await db.commit()
        await db.refresh(device)

        dto = TrustedDeviceResponse.model_validate(device)
        dto.short_fingerprint = (
            f"{device.public_key_fingerprint[:6]}...{device.public_key_fingerprint[-6:]}".upper()
        )
        return dto

    # =========================================================================
    # 5. Online Presence Device Proof Verification
    # =========================================================================

    @staticmethod
    async def verify_online_attendance_proof(
        db: AsyncSession,
        current_user: User,
        device_proof: DeviceProofSchema | None,
        student_id: uuid.UUID | None = None,
        qr_token: str | None = None,
        ble_payload: str | None = None,
        current_time: datetime.datetime | None = None,
    ) -> TrustedDevice:
        """Centralized verification of student device proof for online attendance.

        Invariants Enforced:
        - Authenticated Student must have an ACTIVE registered primary device.
        - The submitted device_id must match the student's ACTIVE device.
        - Signature must verify over canonical payload using the stored public key.
        """
        # 1. Look up student profile if not explicitly provided
        if student_id is None:
            stu_stmt = select(Student.id).where(Student.user_id == current_user.id)
            stu_res = await db.execute(stu_stmt)
            student_id = stu_res.scalar_one_or_none()
            if not student_id:
                raise DomainException(
                    code="STUDENT_PROFILE_REQUIRED",
                    message="Authenticated user does not possess an active student profile.",
                    status_code=403,
                )

        # 2. Look up student's active device
        active_device = await DeviceTrustService.get_student_active_device(
            db=db,
            student_id=student_id,
            university_id=current_user.university_id,
        )
        if not active_device:
            raise DomainException(
                code="TRUSTED_DEVICE_REQUIRED",
                message="Attendance check-in requires an active registered primary mobile device.",
                status_code=403,
            )

        if not device_proof:
            raise DomainException(
                code="DEVICE_PROOF_REQUIRED",
                message="Missing cryptographic device proof of possession.",
                status_code=403,
            )

        # 2. Check device ID match
        if active_device.id != device_proof.device_id:
            raise DomainException(
                code="DEVICE_PROOF_INVALID",
                message="Submitted device proof does not match student's registered active device.",
                status_code=403,
            )

        # 3. Check status
        if active_device.status != DeviceStatus.ACTIVE.value:
            raise DomainException(
                code="DEVICE_NOT_ACTIVE",
                message=(
                    f"Registered device is currently {active_device.status}. "
                    "Attendance not permitted."
                ),
                status_code=403,
            )

        # 4. Construct canonical payload and verify signature
        canonical_bytes = build_online_device_proof_payload(
            user_id=current_user.id,
            university_id=current_user.university_id,
            device_id=active_device.id,
            proof_id=device_proof.proof_id,
            qr_token=qr_token,
            ble_payload=ble_payload,
        )

        verify_device_signature(
            public_key_material=active_device.public_key,
            message_bytes=canonical_bytes,
            signature_input=device_proof.signature,
        )

        return active_device
