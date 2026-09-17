"""API endpoints for data imports, validation, preview, and transactional commit."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.pagination import PaginatedResponse, PaginationParams
from backend.app.common.schemas import StandardResponse
from backend.app.core.constants import ImportCommitMode, ImportType
from backend.app.core.database import get_db_session
from backend.app.imports.schemas import (
    ImportCommitRequest,
    ImportCommitResponse,
    ImportJobResponse,
    ImportPreviewResponse,
    ImportRowResponse,
    ImportTemplateResponse,
)
from backend.app.imports.service import ImportService
from backend.app.models.user import User
from backend.app.rbac.dependencies import require_permission

router = APIRouter(prefix="/imports", tags=["Data Imports & Administration"])


@router.post(
    "/preview",
    response_model=StandardResponse[ImportPreviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload and preview import dataset",
    description="Parses and stages an import file without mutating production tables.",
)
async def preview_import(
    file: Annotated[UploadFile, File(description="CSV (.csv) or Excel (.xlsx) spreadsheet file")],
    import_type: Annotated[ImportType, Form(description="Type of data being imported")],
    commit_mode: Annotated[
        ImportCommitMode,
        Form(description="Validation mode: STRICT (all rows must be valid) or PARTIAL"),
    ] = ImportCommitMode.STRICT,
    idempotency_key: Annotated[
        str | None,
        Form(description="Client-side idempotency key to prevent double staging"),
    ] = None,
    sheet_name: Annotated[
        str | None,
        Form(description="Worksheet name to parse (for multi-sheet Excel files)"),
    ] = None,
    current_user: Annotated[User, Depends(require_permission("imports.create"))] = None,  # type: ignore[assignment]
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> StandardResponse[ImportPreviewResponse]:
    content = await file.read()
    job, staged_rows, headers = await ImportService.preview_import(
        db=db,
        university_id=current_user.university_id,
        requested_by_user_id=current_user.id,
        filename=file.filename or "import.csv",
        content=content,
        import_type=import_type,
        commit_mode=commit_mode,
        idempotency_key=idempotency_key,
        sheet_name=sheet_name,
    )

    preview_rows = [ImportRowResponse.model_validate(r) for r in staged_rows[:50]]
    job_response = ImportJobResponse.model_validate(job)

    return StandardResponse(
        data=ImportPreviewResponse(
            job=job_response,
            columns_detected=headers,
            staged_rows_preview=preview_rows,
        )
    )


@router.get(
    "",
    response_model=StandardResponse[PaginatedResponse[ImportJobResponse]],
    summary="List import jobs",
    description="Retrieve paginated history of import jobs for the authenticated university.",
)
async def list_import_jobs(
    pagination: Annotated[PaginationParams, Depends()],
    import_type: Annotated[str | None, Query(description="Filter by import type")] = None,
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by job status")
    ] = None,
    current_user: Annotated[User, Depends(require_permission("imports.read"))] = None,  # type: ignore[assignment]
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> StandardResponse[PaginatedResponse[ImportJobResponse]]:
    jobs, total = await ImportService.list_import_jobs(
        db=db,
        university_id=current_user.university_id,
        import_type=import_type,
        status=status_filter,
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    items = [ImportJobResponse.model_validate(j) for j in jobs]
    return StandardResponse(
        data=PaginatedResponse[ImportJobResponse].create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    )


@router.get(
    "/templates/{import_type}",
    response_model=StandardResponse[ImportTemplateResponse],
    summary="Get import template specification",
    description="Returns expected columns and a sample CSV file for the requested import domain.",
)
async def get_import_template(
    import_type: ImportType,
    current_user: Annotated[User, Depends(require_permission("imports.read"))] = None,  # type: ignore[assignment]
) -> StandardResponse[ImportTemplateResponse]:
    template = ImportService.get_template_spec(import_type)
    return StandardResponse(data=template)


@router.get(
    "/{job_id}",
    response_model=StandardResponse[ImportJobResponse],
    summary="Get import job details",
    description="Retrieve job header details and tallies.",
)
async def get_import_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("imports.read"))] = None,  # type: ignore[assignment]
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> StandardResponse[ImportJobResponse]:
    job = await ImportService.get_import_job(db, current_user.university_id, job_id)
    return StandardResponse(data=ImportJobResponse.model_validate(job))


@router.get(
    "/{job_id}/rows",
    response_model=StandardResponse[PaginatedResponse[ImportRowResponse]],
    summary="List staged rows for an import job",
    description="Retrieve paginated staged rows with error and warning details.",
)
async def list_import_rows(
    job_id: uuid.UUID,
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter rows by status")
    ] = None,
    current_user: Annotated[User, Depends(require_permission("imports.read"))] = None,  # type: ignore[assignment]
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> StandardResponse[PaginatedResponse[ImportRowResponse]]:
    rows, total = await ImportService.list_job_rows(
        db=db,
        university_id=current_user.university_id,
        job_id=job_id,
        status=status_filter,
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    items = [ImportRowResponse.model_validate(r) for r in rows]
    return StandardResponse(
        data=PaginatedResponse[ImportRowResponse].create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    )


@router.post(
    "/{job_id}/commit",
    response_model=StandardResponse[ImportCommitResponse],
    summary="Commit staged import job",
    description="Executes transactional write of staged rows into production domain tables.",
)
async def commit_import_job(
    job_id: uuid.UUID,
    payload: Annotated[ImportCommitRequest | None, Body()] = None,
    current_user: Annotated[User, Depends(require_permission("imports.commit"))] = None,  # type: ignore[assignment]
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> StandardResponse[ImportCommitResponse]:
    req = payload or ImportCommitRequest()
    job = await ImportService.commit_import_job(
        db=db,
        university_id=current_user.university_id,
        job_id=job_id,
        actor_user_id=current_user.id,
        commit_mode_override=req.commit_mode,
    )
    return StandardResponse(
        data=ImportCommitResponse(
            job_id=job.id,
            import_type=job.import_type,
            status=job.status,
            commit_mode=job.commit_mode,
            row_count=job.row_count,
            commit_count=job.commit_count,
            error_count=job.error_count,
            summary=job.summary_json or {},
        )
    )


@router.post(
    "/{job_id}/cancel",
    response_model=StandardResponse[ImportJobResponse],
    summary="Cancel staged import job",
    description="Cancels a staged import job preventing it from being committed.",
)
async def cancel_import_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("imports.cancel"))] = None,  # type: ignore[assignment]
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> StandardResponse[ImportJobResponse]:
    job = await ImportService.cancel_import_job(
        db=db,
        university_id=current_user.university_id,
        job_id=job_id,
        actor_user_id=current_user.id,
    )
    return StandardResponse(data=ImportJobResponse.model_validate(job))
