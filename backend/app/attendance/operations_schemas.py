"""Pydantic schemas for attendance operations, corrections, excuses, and leave workflows."""

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import (
    AttendanceStatus,
    CorrectionRequestStatus,
    CorrectionRequestType,
    ExcuseCategory,
    ExcuseRequestStatus,
    LeaveRequestStatus,
)


class CorrectionRequestCreate(BaseModel):
    """Payload submitted by student to request attendance correction."""

    attendance_record_id: uuid.UUID
    request_type: CorrectionRequestType = CorrectionRequestType.OTHER
    requested_status: AttendanceStatus = AttendanceStatus.PRESENT
    reason: str = Field(..., min_length=3, max_length=500)
    supporting_note: str | None = Field(None, max_length=1000)


class CorrectionRequestReview(BaseModel):
    """Review action payload submitted by lecturer or administrator."""

    status: CorrectionRequestStatus = Field(
        ..., description="Resulting status: APPROVED or REJECTED"
    )
    approved_status: AttendanceStatus | None = Field(
        None, description="Target status if APPROVED (defaults to requested_status if omitted)"
    )
    review_note: str = Field(..., min_length=3, max_length=500)


class CorrectionRequestResponse(BaseModel):
    """Full operational representation of an attendance correction request."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    attendance_record_id: uuid.UUID
    attendance_session_id: uuid.UUID
    student_id: uuid.UUID
    request_type: str
    requested_status: str
    reason: str
    supporting_note: str | None = None
    status: str
    reviewed_by_user_id: uuid.UUID | None = None
    reviewed_at_utc: datetime.datetime | None = None
    review_note: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ExcuseRequestCreate(BaseModel):
    """Payload submitted by student to request absence excuse."""

    attendance_session_id: uuid.UUID | None = None
    class_occurrence_id: uuid.UUID | None = None
    attendance_record_id: uuid.UUID | None = None
    category: ExcuseCategory = ExcuseCategory.OTHER
    description: str = Field(..., min_length=5, max_length=1000)
    document_reference: str | None = Field(None, max_length=255)


class ExcuseRequestReview(BaseModel):
    """Review action payload for absence excuse request."""

    status: ExcuseRequestStatus = Field(..., description="Resulting status: APPROVED or REJECTED")
    review_note: str = Field(..., min_length=3, max_length=500)


class ExcuseRequestResponse(BaseModel):
    """Full operational representation of an attendance excuse request."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    student_id: uuid.UUID
    attendance_record_id: uuid.UUID | None = None
    attendance_session_id: uuid.UUID | None = None
    class_occurrence_id: uuid.UUID | None = None
    category: str
    description: str
    document_reference: str | None = None
    status: str
    reviewed_by_user_id: uuid.UUID | None = None
    reviewed_at_utc: datetime.datetime | None = None
    review_note: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class LeaveRequestCreate(BaseModel):
    """Payload submitted by student to request pre-class leave for a class occurrence."""

    class_occurrence_id: uuid.UUID
    reason: str = Field(..., min_length=5, max_length=1000)


class LeaveRequestReview(BaseModel):
    """Review action payload for pre-class leave request."""

    status: LeaveRequestStatus = Field(..., description="Resulting status: APPROVED or REJECTED")
    review_note: str = Field(..., min_length=3, max_length=500)


class LeaveRequestResponse(BaseModel):
    """Full operational representation of an attendance leave request."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    student_id: uuid.UUID
    class_occurrence_id: uuid.UUID
    reason: str
    status: str
    reviewed_by_user_id: uuid.UUID | None = None
    reviewed_at_utc: datetime.datetime | None = None
    review_note: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AdminOverrideRequest(BaseModel):
    """Privileged override payload executed by administrator."""

    attendance_record_id: uuid.UUID
    target_status: AttendanceStatus
    reason: str = Field(..., min_length=5, max_length=500)
    target_credit: float | None = Field(None, ge=0.0, le=1.0)


class RevisionReversalRequest(BaseModel):
    """Payload to reverse a prior attendance revision."""

    revision_id: uuid.UUID
    reason: str = Field(..., min_length=5, max_length=500)


class RevisionItemResponse(BaseModel):
    """Single revision item in the audit history timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attendance_session_id: uuid.UUID
    attendance_record_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID
    event_type: str
    previous_status: str | None = None
    new_status: str | None = None
    previous_credit: float | None = None
    new_credit: float | None = None
    reason: str | None = None
    metadata_json: dict[str, Any] | None = None
    occurred_at_utc: datetime.datetime
    created_at: datetime.datetime


class RecordTimelineResponse(BaseModel):
    """Comprehensive timeline of attendance record and its revisions."""

    record_id: uuid.UUID
    session_id: uuid.UUID
    student_id: uuid.UUID
    current_status: str
    current_credit: float
    version_no: int
    is_manual: bool
    manual_reason: str | None = None
    revisions: list[RevisionItemResponse]


class BulkItemResult(BaseModel):
    """Result of an individual item within a bulk review operation."""

    id: uuid.UUID
    success: bool
    status: str | None = None
    error: str | None = None


class BulkReviewRequest(BaseModel):
    """Payload for safe batch review of attendance operations."""

    request_type: str = Field(..., description="Target queue: 'correction', 'excuse', or 'leave'")
    request_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)
    status: str = Field(..., description="Target outcome: 'APPROVED' or 'REJECTED'")
    review_note: str = Field(..., min_length=3, max_length=500)
    approved_status: AttendanceStatus | None = Field(
        None, description="Optional target status for approved corrections"
    )


class BulkReviewResponse(BaseModel):
    """Summary of batch review outcome with individual item results."""

    total: int
    succeeded: int
    failed: int
    results: list[BulkItemResult]


class OperationsCountsResponse(BaseModel):
    """Pending counts for attendance operations dashboard tabs."""

    pending_corrections: int
    pending_excuses: int
    pending_leaves: int
    manual_reviews: int


class RecordEligibilityResponse(BaseModel):
    """Student eligibility check for requesting correction or excuse on a record."""

    record_id: uuid.UUID
    eligible_for_correction: bool
    correction_ineligibility_reason: str | None = None
    correction_window_deadline_utc: datetime.datetime | None = None
    has_open_correction: bool
    has_open_excuse: bool
    current_status: str
    current_credit: float


class ManualReviewItemResponse(BaseModel):
    """Item in the manual / anomaly review queue."""

    record_id: uuid.UUID
    session_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str | None = None
    student_number: str | None = None
    course_code: str | None = None
    course_title: str | None = None
    status: str
    attendance_credit: float
    verification_method: str | None = None
    is_flagged: bool = False
    flag_reasons: list[str] = []
    is_manual: bool = False
    created_at: datetime.datetime


class ManualReviewConfirmRequest(BaseModel):
    """Payload to confirm or adjust a manual / anomaly attendance record."""

    target_status: AttendanceStatus
    target_credit: float | None = Field(None, ge=0.0, le=1.0)
    reason: str = Field(..., min_length=3, max_length=500)
