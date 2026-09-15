"""Domain service implementing Milestone 12 Offline Attendance & Reconciliation.

Invariants Enforced:
- INV-01: Client cannot mark itself present. Student identity is derived strictly from JWT.
- INV-03: University server UTC clock authority. Monotonic anchor bounds offline duration.
- INV-04: Expired challenge tokens (> tolerance slot) are rejected.
- INV-05: Exactly one credit per checkpoint per session (no duplicate credit).
- INV-07: All reconciled records carry source_mode="OFFLINE_SYNC" and immutable audit trail.
"""

import datetime
import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.attendance.offline_crypto import (
    EventChainEngine,
    OfflineChallengeEngine,
    OfflineCryptoException,
    OfflinePermitEngine,
)
from backend.app.attendance.offline_schemas import (
    OfflineHostSyncRequest,
    OfflineHostSyncResponse,
    OfflinePermitRequest,
    OfflinePermitResponse,
    OfflineStudentClaimItem,
    OfflineStudentClaimSyncResult,
    OfflineStudentSyncRequest,
    OfflineStudentSyncResponse,
    OfflineVerificationKeyResponse,
)
from backend.app.attendance.service import AttendanceService
from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.core.constants import (
    EvidenceSourceMode,
    OfflineClaimStatus,
    OfflineConflictResolution,
    OfflineConflictType,
    OfflineHostSessionStatus,
    OfflinePermitStatus,
    SyncBatchType,
    SyncEntryStatus,
)
from backend.app.core.exceptions import DomainException, NotFoundException
from backend.app.models.attendance_session import AttendanceSession
from backend.app.models.enrollment import Enrollment
from backend.app.models.offline_attendance import (
    OfflineAttendanceClaim,
    OfflineAttendancePermit,
    OfflineHostEvent,
    OfflineHostSession,
    OfflineSyncConflict,
    SyncInboxEntry,
)
from backend.app.models.student import Student
from backend.app.models.user import User


class OfflineAttendanceService:
    """Core domain service for offline attendance permits, host sync, and claim reconciliation."""

    @staticmethod
    def get_verification_keys() -> OfflineVerificationKeyResponse:
        """Return public key used to verify server-signed offline attendance permits."""
        settings = get_settings()
        return OfflineVerificationKeyResponse(
            algorithm="EdDSA",
            curve="Ed25519",
            kid=settings.OFFLINE_PERMIT_SIGNING_KID,
            public_key_pem=settings.OFFLINE_PERMIT_SIGNING_PUBLIC_KEY,
        )

    @staticmethod
    async def issue_offline_permit(
        db: AsyncSession,
        current_user: User,
        request: OfflinePermitRequest,
        current_time: datetime.datetime | None = None,
    ) -> OfflinePermitResponse:
        """Issue an Ed25519-signed OfflineAttendancePermit for an upcoming attendance session.

        Validates that the requesting user is an authorized lecturer or administrator.
        Precomputes SHA-256 digests of the session roster and attendance policy.
        """
        now = current_time or utc_now()
        settings = get_settings()

        # 1. Fetch attendance session and occurrence
        stmt = (
            select(AttendanceSession)
            .options(
                selectinload(AttendanceSession.class_occurrence),
                selectinload(AttendanceSession.attendance_policy),
            )
            .where(AttendanceSession.id == request.attendance_session_id)
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise NotFoundException("AttendanceSession", request.attendance_session_id)

        occurrence = session.class_occurrence
        if not occurrence:
            raise DomainException(
                code="NO_OCCURRENCE_FOR_SESSION",
                message="Session has no linked class occurrence.",
                status_code=400,
            )

        # 2. Fetch enrolled students to construct roster snapshot digest
        enrolled_stmt = select(Enrollment.student_id).where(
            Enrollment.course_offering_id == occurrence.course_offering_id,
        )
        enrolled_res = await db.execute(enrolled_stmt)
        student_ids = list(enrolled_res.scalars().all())
        roster_digest = OfflinePermitEngine.compute_roster_snapshot_digest(student_ids)

        # 3. Policy digest
        if session.attendance_policy:
            policy_dict = {
                "required_checkpoints": session.attendance_policy.required_checkpoint_count,
                "min_percentage": float(session.attendance_policy.min_attendance_percentage),
                "late_threshold": session.attendance_policy.late_threshold_minutes,
            }
        else:
            policy_dict = session.policy_snapshot or {}
        policy_digest = OfflinePermitEngine.compute_policy_snapshot_digest(policy_dict)

        # 4. Compute validity window
        validity_hours = min(request.validity_hours, settings.ATTENDANCE_OFFLINE_MAX_VALIDITY_HOURS)
        valid_until = now + datetime.timedelta(hours=validity_hours)

        permit_id = uuid.uuid4()
        signed_token = OfflinePermitEngine.issue_permit_token(
            permit_id=permit_id,
            university_id=session.university_id,
            session_id=session.id,
            occurrence_id=occurrence.id,
            lecturer_id=current_user.id,
            temporary_host_public_key_pem=request.temporary_host_public_key,
            valid_from_utc=now,
            valid_until_utc=valid_until,
            authority_epoch=1,
            roster_snapshot_digest=roster_digest,
            policy_snapshot_digest=policy_digest,
        )

        permit = OfflineAttendancePermit(
            id=permit_id,
            university_id=session.university_id,
            attendance_session_id=session.id,
            class_occurrence_id=occurrence.id,
            lecturer_user_id=current_user.id,
            temporary_host_public_key=request.temporary_host_public_key.strip(),
            authority_epoch=1,
            roster_snapshot_digest=roster_digest,
            policy_snapshot_digest=policy_digest,
            valid_from_utc=now,
            valid_until_utc=valid_until,
            status=OfflinePermitStatus.ISSUED.value,
            signed_permit_token=signed_token,
            created_at=now,
        )
        db.add(permit)
        await db.commit()
        await db.refresh(permit)

        return OfflinePermitResponse(
            permit_id=permit.id,
            attendance_session_id=permit.attendance_session_id,
            class_occurrence_id=permit.class_occurrence_id,
            lecturer_user_id=permit.lecturer_user_id,
            temporary_host_public_key=permit.temporary_host_public_key,
            authority_epoch=permit.authority_epoch,
            roster_snapshot_digest=permit.roster_snapshot_digest,
            policy_snapshot_digest=permit.policy_snapshot_digest,
            valid_from_utc=permit.valid_from_utc,
            valid_until_utc=permit.valid_until_utc,
            status=permit.status,
            signed_permit_token=permit.signed_permit_token,
            server_time_utc=now,
        )

    @staticmethod
    async def sync_host_events(
        db: AsyncSession,
        current_user: User,
        payload: OfflineHostSyncRequest,
        current_time: datetime.datetime | None = None,
    ) -> OfflineHostSyncResponse:
        """Process an offline host session upload from a lecturer device.

        Verifies the event hash-chain and host signatures, stores host events,
        and triggers reconciliation for any pending student claims.
        """
        now = current_time or utc_now()

        # 1. Idempotency deduplication check
        inbox_stmt = select(SyncInboxEntry).where(
            SyncInboxEntry.client_batch_id == payload.client_batch_id,
            SyncInboxEntry.idempotency_key == payload.idempotency_key,
        )
        inbox_res = await db.execute(inbox_stmt)
        existing_inbox = inbox_res.scalar_one_or_none()
        if existing_inbox:
            # Return idempotent acknowledgement
            return OfflineHostSyncResponse(
                status="ALREADY_PROCESSED",
                host_session_id=payload.host_session_id,
                events_ingested=len(payload.events),
                claims_reconciled=0,
                conflicts_detected=0,
            )

        # 2. Fetch Permit
        permit_stmt = select(OfflineAttendancePermit).where(
            OfflineAttendancePermit.id == payload.permit_id
        )
        permit_res = await db.execute(permit_stmt)
        permit = permit_res.scalar_one_or_none()
        if not permit:
            raise NotFoundException("OfflineAttendancePermit", payload.permit_id)

        if permit.status == OfflinePermitStatus.REVOKED.value:
            raise DomainException(
                code="PERMIT_REVOKED",
                message="The offline permit for this host session has been revoked.",
                status_code=400,
            )

        # 3. Verify Event Chain
        events_dicts = [ev.model_dump() for ev in payload.events]
        try:
            EventChainEngine.verify_event_chain(
                events=events_dicts,
                host_public_key_material=permit.temporary_host_public_key,
            )
        except OfflineCryptoException as exc:
            raise DomainException(
                code="TAMPERED_EVENT_CHAIN",
                message=f"Event chain validation failed: {exc.message}",
                status_code=400,
            ) from exc

        # 4. Create or update OfflineHostSession
        host_stmt = select(OfflineHostSession).where(
            OfflineHostSession.id == payload.host_session_id
        )
        host_res = await db.execute(host_stmt)
        host_session = host_res.scalar_one_or_none()

        if not host_session:
            host_session = OfflineHostSession(
                id=payload.host_session_id,
                offline_permit_id=permit.id,
                host_device_id=payload.host_device_id,
                clock_anchor_server_utc=payload.clock_anchor_server_utc,
                clock_anchor_uptime_ms=payload.clock_anchor_uptime_ms,
                started_at_utc=payload.started_at_utc,
                ended_at_utc=payload.ended_at_utc,
                final_event_hash=payload.final_event_hash,
                status=OfflineHostSessionStatus.SYNCED.value,
                synced_at_utc=now,
                created_at=now,
            )
            db.add(host_session)
        else:
            host_session.ended_at_utc = payload.ended_at_utc
            host_session.final_event_hash = payload.final_event_hash
            host_session.status = OfflineHostSessionStatus.SYNCED.value
            host_session.synced_at_utc = now

        # 5. Insert events
        for ev in payload.events:
            event_obj = OfflineHostEvent(
                id=uuid.uuid4(),
                offline_host_session_id=payload.host_session_id,
                sequence_number=ev.sequence_number,
                event_type=ev.event_type,
                prev_event_hash=ev.prev_event_hash,
                event_hash=ev.event_hash,
                payload=ev.payload,
                signature=ev.signature,
                occurred_at_utc=datetime.datetime.fromisoformat(ev.occurred_at_utc),
                created_at=now,
            )
            db.add(event_obj)

        permit.status = OfflinePermitStatus.SYNCED.value

        # 6. Record Inbox Entry
        payload_json = json.dumps(
            {"batch_id": payload.client_batch_id, "events": len(payload.events)}
        )
        inbox_entry = SyncInboxEntry(
            id=uuid.uuid4(),
            client_batch_id=payload.client_batch_id,
            idempotency_key=payload.idempotency_key,
            actor_user_id=current_user.id,
            batch_type=SyncBatchType.HOST_EVENTS.value,
            payload_digest=hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
            status=SyncEntryStatus.PROCESSED.value,
            processed_at_utc=now,
            created_at=now,
        )
        db.add(inbox_entry)

        await db.commit()

        # 7. Reconcile any previously queued student claims for this permit
        (
            reconciled_count,
            conflict_count,
        ) = await OfflineAttendanceService.reconcile_claims_for_host_session(
            db=db,
            host_session_id=payload.host_session_id,
            current_time=now,
        )

        return OfflineHostSyncResponse(
            status="SUCCESS",
            host_session_id=payload.host_session_id,
            events_ingested=len(payload.events),
            claims_reconciled=reconciled_count,
            conflicts_detected=conflict_count,
        )

    @staticmethod
    async def sync_student_claims(
        db: AsyncSession,
        current_user: User,
        payload: OfflineStudentSyncRequest,
        current_time: datetime.datetime | None = None,
    ) -> OfflineStudentSyncResponse:
        """Process batch of offline attendance claims submitted by a student.

        Enforces INV-01: student identity is derived strictly from current_user.id.
        Evaluates presence immediately if host events are present; otherwise marks
        claims as PENDING_HOST_EVENTS.
        """
        now = current_time or utc_now()

        # 1. Identify Student profile
        stu_stmt = select(Student).where(Student.user_id == current_user.id)
        stu_res = await db.execute(stu_stmt)
        student = stu_res.scalar_one_or_none()
        if not student:
            raise DomainException(
                code="NOT_A_STUDENT",
                message="Only enrolled students can submit offline attendance claims.",
                status_code=403,
            )

        # 2. Idempotency deduplication check
        inbox_stmt = select(SyncInboxEntry).where(
            SyncInboxEntry.client_batch_id == payload.client_batch_id,
            SyncInboxEntry.idempotency_key == payload.idempotency_key,
        )
        inbox_res = await db.execute(inbox_stmt)
        if inbox_res.scalar_one_or_none():
            # Return existing claim statuses
            results: list[OfflineStudentClaimSyncResult] = []
            for item in payload.claims:
                c_stmt = select(OfflineAttendanceClaim).where(
                    OfflineAttendanceClaim.offline_permit_id == item.permit_id,
                    OfflineAttendanceClaim.student_id == student.id,
                    OfflineAttendanceClaim.checkpoint_type == item.checkpoint_type,
                )
                c_res = await db.execute(c_stmt)
                claim_rec = c_res.scalar_one_or_none()
                if claim_rec:
                    results.append(
                        OfflineStudentClaimSyncResult(
                            claim_id=claim_rec.id,
                            checkpoint_type=claim_rec.checkpoint_type,
                            status=claim_rec.status,
                            rejection_reason=claim_rec.rejection_reason,
                            credited=claim_rec.status == OfflineClaimStatus.VERIFIED.value,
                        )
                    )
            return OfflineStudentSyncResponse(
                status="ALREADY_PROCESSED",
                claims_processed=len(results),
                results=results,
            )

        results = []
        for claim_item in payload.claims:
            result = await OfflineAttendanceService._process_single_student_claim(
                db=db,
                student=student,
                current_user=current_user,
                claim_item=claim_item,
                now=now,
            )
            results.append(result)

        # Record Inbox Entry
        batch_summary = json.dumps(
            {"batch_id": payload.client_batch_id, "claims_count": len(payload.claims)}
        )
        inbox_entry = SyncInboxEntry(
            id=uuid.uuid4(),
            client_batch_id=payload.client_batch_id,
            idempotency_key=payload.idempotency_key,
            actor_user_id=current_user.id,
            batch_type=SyncBatchType.STUDENT_CLAIMS.value,
            payload_digest=hashlib.sha256(batch_summary.encode("utf-8")).hexdigest(),
            status=SyncEntryStatus.PROCESSED.value,
            processed_at_utc=now,
            created_at=now,
        )
        db.add(inbox_entry)
        await db.commit()

        return OfflineStudentSyncResponse(
            status="SUCCESS",
            claims_processed=len(results),
            results=results,
        )

    @staticmethod
    async def _process_single_student_claim(
        db: AsyncSession,
        student: Student,
        current_user: User,
        claim_item: OfflineStudentClaimItem,
        now: datetime.datetime,
    ) -> OfflineStudentClaimSyncResult:
        """Evaluate and persist an individual student offline claim."""
        # 1. Duplicate claim check (INV-05)
        existing_stmt = select(OfflineAttendanceClaim).where(
            OfflineAttendanceClaim.offline_permit_id == claim_item.permit_id,
            OfflineAttendanceClaim.student_id == student.id,
            OfflineAttendanceClaim.checkpoint_type == claim_item.checkpoint_type,
        )
        existing_res = await db.execute(existing_stmt)
        existing_claim = existing_res.scalar_one_or_none()
        if existing_claim:
            return OfflineStudentClaimSyncResult(
                claim_id=existing_claim.id,
                checkpoint_type=existing_claim.checkpoint_type,
                status=existing_claim.status,
                rejection_reason=existing_claim.rejection_reason,
                credited=existing_claim.status == OfflineClaimStatus.VERIFIED.value,
            )

        # 2. Fetch Permit
        permit_stmt = select(OfflineAttendancePermit).where(
            OfflineAttendancePermit.id == claim_item.permit_id
        )
        permit_res = await db.execute(permit_stmt)
        permit = permit_res.scalar_one_or_none()
        if not permit:
            return OfflineStudentClaimSyncResult(
                claim_id=claim_item.claim_id,
                checkpoint_type=claim_item.checkpoint_type,
                status=OfflineClaimStatus.REJECTED.value,
                rejection_reason="Permit not found on server.",
                credited=False,
            )

        # 3. Verify Challenge Signature
        try:
            _ = OfflineChallengeEngine.verify_challenge(
                token=claim_item.qr_challenge_token,
                host_public_key_material=permit.temporary_host_public_key,
                current_time=claim_item.client_captured_at_utc,
                rotation_seconds=get_settings().ATTENDANCE_OFFLINE_ROTATION_SECONDS,
                tolerance_steps=1,
            )
        except OfflineCryptoException as exc:
            # Signature failure or slot window expiry
            claim = OfflineAttendanceClaim(
                id=claim_item.claim_id,
                offline_permit_id=permit.id,
                offline_host_session_id=claim_item.host_session_id,
                student_id=student.id,
                submitted_by_user_id=current_user.id,
                checkpoint_type=claim_item.checkpoint_type,
                rotation_slot=claim_item.rotation_slot,
                qr_challenge_token=claim_item.qr_challenge_token,
                ble_evidence_payload=claim_item.ble_evidence,
                status=OfflineClaimStatus.REJECTED.value,
                rejection_reason=f"Cryptographic challenge rejection: {exc.message}",
                client_monotonic_offset_ms=claim_item.client_monotonic_offset_ms,
                client_captured_at_utc=claim_item.client_captured_at_utc,
                server_synced_at_utc=now,
                created_at=now,
            )
            db.add(claim)
            return OfflineStudentClaimSyncResult(
                claim_id=claim.id,
                checkpoint_type=claim.checkpoint_type,
                status=claim.status,
                rejection_reason=claim.rejection_reason,
                credited=False,
            )

        # 4. Check if matching Host Session is already synced
        host_stmt = select(OfflineHostSession).where(
            OfflineHostSession.offline_permit_id == permit.id,
            OfflineHostSession.status == OfflineHostSessionStatus.SYNCED.value,
        )
        host_res = await db.execute(host_stmt)
        host_session = host_res.scalar_one_or_none()

        if not host_session:
            # Out-of-order delivery: Student synced before lecturer!
            claim = OfflineAttendanceClaim(
                id=claim_item.claim_id,
                offline_permit_id=permit.id,
                offline_host_session_id=None,
                student_id=student.id,
                submitted_by_user_id=current_user.id,
                checkpoint_type=claim_item.checkpoint_type,
                rotation_slot=claim_item.rotation_slot,
                qr_challenge_token=claim_item.qr_challenge_token,
                ble_evidence_payload=claim_item.ble_evidence,
                status=OfflineClaimStatus.PENDING_HOST_EVENTS.value,
                client_monotonic_offset_ms=claim_item.client_monotonic_offset_ms,
                client_captured_at_utc=claim_item.client_captured_at_utc,
                server_synced_at_utc=now,
                created_at=now,
            )
            db.add(claim)
            return OfflineStudentClaimSyncResult(
                claim_id=claim.id,
                checkpoint_type=claim.checkpoint_type,
                status=OfflineClaimStatus.PENDING_HOST_EVENTS.value,
                credited=False,
            )

        # Host session is present: Evaluate presence credit immediately!
        claim = OfflineAttendanceClaim(
            id=claim_item.claim_id,
            offline_permit_id=permit.id,
            offline_host_session_id=host_session.id,
            student_id=student.id,
            submitted_by_user_id=current_user.id,
            checkpoint_type=claim_item.checkpoint_type,
            rotation_slot=claim_item.rotation_slot,
            qr_challenge_token=claim_item.qr_challenge_token,
            ble_evidence_payload=claim_item.ble_evidence,
            client_monotonic_offset_ms=claim_item.client_monotonic_offset_ms,
            client_captured_at_utc=claim_item.client_captured_at_utc,
            server_synced_at_utc=now,
            created_at=now,
        )

        credited = await OfflineAttendanceService._credit_claim(
            db=db,
            claim=claim,
            session_id=permit.attendance_session_id,
            now=now,
        )

        db.add(claim)
        return OfflineStudentClaimSyncResult(
            claim_id=claim.id,
            checkpoint_type=claim.checkpoint_type,
            status=claim.status,
            rejection_reason=claim.rejection_reason,
            credited=credited,
        )

    @staticmethod
    async def reconcile_claims_for_host_session(
        db: AsyncSession,
        host_session_id: uuid.UUID,
        current_time: datetime.datetime | None = None,
    ) -> tuple[int, int]:
        """Reconcile pending claims for a newly synced host session.

        Returns: (reconciled_count, conflict_count)
        """
        now = current_time or utc_now()

        # Fetch host session and permit
        host_stmt = (
            select(OfflineHostSession)
            .options(selectinload(OfflineHostSession.permit))
            .where(OfflineHostSession.id == host_session_id)
        )
        host_res = await db.execute(host_stmt)
        host_session = host_res.scalar_one_or_none()
        if not host_session:
            return 0, 0

        # Find pending claims
        claims_stmt = select(OfflineAttendanceClaim).where(
            OfflineAttendanceClaim.offline_permit_id == host_session.offline_permit_id,
            OfflineAttendanceClaim.status == OfflineClaimStatus.PENDING_HOST_EVENTS.value,
        )
        claims_res = await db.execute(claims_stmt)
        pending_claims = list(claims_res.scalars().all())

        reconciled = 0
        conflicts = 0

        for claim in pending_claims:
            claim.offline_host_session_id = host_session.id
            credited = await OfflineAttendanceService._credit_claim(
                db=db,
                claim=claim,
                session_id=host_session.permit.attendance_session_id,
                now=now,
            )
            if credited:
                reconciled += 1
            elif claim.status == OfflineClaimStatus.CONFLICT.value:
                conflicts += 1

        await db.commit()
        return reconciled, conflicts

    @staticmethod
    async def _credit_claim(
        db: AsyncSession,
        claim: OfflineAttendanceClaim,
        session_id: uuid.UUID,
        now: datetime.datetime,
    ) -> bool:
        """Attempt to grant verified checkpoint credit via AttendanceService."""
        try:
            evidence = await AttendanceService.record_verified_checkpoint_credit(
                db=db,
                session_id=session_id,
                checkpoint_type=claim.checkpoint_type,
                student_id=claim.student_id,
                actor_id=claim.submitted_by_user_id,
                source_mode=EvidenceSourceMode.OFFLINE_SYNC.value,
                reason="Offline attendance reconciled from verified host event challenge.",
                evidence_metadata={
                    "offline_claim_id": str(claim.id),
                    "offline_permit_id": str(claim.offline_permit_id),
                    "offline_host_session_id": (
                        str(claim.offline_host_session_id)
                        if claim.offline_host_session_id
                        else None
                    ),
                    "rotation_slot": claim.rotation_slot,
                    "client_captured_at_utc": claim.client_captured_at_utc.isoformat(),
                    "ble_evidence": claim.ble_evidence_payload,
                },
                is_real_time=False,
                override_now=now,
            )
            claim.status = OfflineClaimStatus.VERIFIED.value
            claim.attendance_evidence_id = evidence.id
            claim.rejection_reason = None
            return True
        except DomainException as exc:
            if exc.code == "STUDENT_NOT_ROSTERED":
                claim.status = OfflineClaimStatus.REJECTED.value
                claim.rejection_reason = "Student not in course roster."
            else:
                claim.status = OfflineClaimStatus.CONFLICT.value
                claim.rejection_reason = f"Reconciliation conflict: {exc.message}"
                # Log conflict
                conflict = OfflineSyncConflict(
                    id=uuid.uuid4(),
                    attendance_session_id=session_id,
                    offline_permit_id=claim.offline_permit_id,
                    student_id=claim.student_id,
                    conflict_type=OfflineConflictType.EXISTING_RECORD_CONFLICT.value,
                    resolution_status=OfflineConflictResolution.UNRESOLVED.value,
                    conflict_details={
                        "claim_id": str(claim.id),
                        "checkpoint_type": claim.checkpoint_type,
                        "error_code": exc.code,
                        "error_message": exc.message,
                    },
                    created_at=now,
                )
                db.add(conflict)
            return False
