"""Pydantic schemas for data import staging, validation, preview, and commit."""

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import ImportCommitMode, ImportType


class ImportRowResponse(BaseModel):
    """Schema for an individual staged import row."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_job_id: uuid.UUID
    row_number: int
    raw_data: dict[str, Any]
    normalized_data: dict[str, Any] | None = None
    action: str
    status: str
    errors: list[dict[str, Any]] | None = None
    warnings: list[dict[str, Any]] | None = None
    resolved_entity_id: uuid.UUID | None = None
    resolved_entity_type: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ImportJobResponse(BaseModel):
    """Schema for import job summary header."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    university_id: uuid.UUID
    import_type: str
    status: str
    commit_mode: str
    original_filename: str
    file_size: int
    file_hash: str
    requested_by_user_id: uuid.UUID
    row_count: int
    valid_count: int
    warning_count: int
    error_count: int
    commit_count: int
    failure_reason: str | None = None
    idempotency_key: str | None = None
    summary_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ImportPreviewResponse(BaseModel):
    """Schema for import upload and preview result."""

    job: ImportJobResponse
    columns_detected: list[str]
    staged_rows_preview: list[ImportRowResponse]


class ImportCommitRequest(BaseModel):
    """Schema for requesting execution of a staged import job."""

    commit_mode: ImportCommitMode | None = Field(
        default=None,
        description="Optional commit mode override (STRICT or PARTIAL).",
    )


class ImportCommitResponse(BaseModel):
    """Schema for import commit execution summary."""

    job_id: uuid.UUID
    import_type: str
    status: str
    commit_mode: str
    row_count: int
    commit_count: int
    error_count: int
    summary: dict[str, Any]


class ImportTemplateColumn(BaseModel):
    """Schema describing an import column attribute."""

    name: str
    required: bool
    description: str
    example: str


class ImportTemplateResponse(BaseModel):
    """Schema for CSV/Excel template specifications."""

    import_type: ImportType
    columns: list[ImportTemplateColumn]
    csv_sample: str
