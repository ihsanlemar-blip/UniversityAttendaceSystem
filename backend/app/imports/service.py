"""Data import orchestration service for staging, validation, preview, and safe commit."""

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.common.types import utc_now
from backend.app.core.config import get_settings
from backend.app.core.constants import (
    ImportCommitMode,
    ImportJobStatus,
    ImportRowStatus,
    ImportType,
)
from backend.app.core.exceptions import ConflictException, NotFoundException, ValidationException
from backend.app.imports.parser import parse_import_file
from backend.app.imports.processors import get_processor
from backend.app.imports.schemas import ImportTemplateResponse
from backend.app.models.import_job import ImportJob, ImportRow

logger = logging.getLogger(__name__)


class ImportService:
    """Institutional service managing CSV/XLSX imports across all academic domains."""

    @staticmethod
    async def preview_import(
        db: AsyncSession,
        university_id: uuid.UUID,
        requested_by_user_id: uuid.UUID,
        filename: str,
        content: bytes,
        import_type: ImportType,
        commit_mode: ImportCommitMode = ImportCommitMode.STRICT,
        idempotency_key: str | None = None,
        sheet_name: str | None = None,
    ) -> tuple[ImportJob, list[ImportRow], list[str]]:
        """Parse, validate, and stage import dataset.

        CRITICAL INVARIANT: This method NEVER mutates production domain tables.
        Only import_jobs and import_rows staging tables are populated.
        """
        settings = get_settings()

        # 1. Check idempotency
        if idempotency_key:
            idem_stmt = select(ImportJob).where(
                ImportJob.university_id == university_id,
                ImportJob.idempotency_key == idempotency_key,
            )
            idem_res = await db.execute(idem_stmt)
            existing_job = idem_res.scalar_one_or_none()
            if existing_job:
                # Return existing staged job and rows
                row_stmt = (
                    select(ImportRow)
                    .where(ImportRow.import_job_id == existing_job.id)
                    .order_by(ImportRow.row_number.asc())
                )
                rows_res = await db.execute(row_stmt)
                existing_rows = list(rows_res.scalars().all())
                headers = (existing_job.metadata_json or {}).get("headers", [])
                return existing_job, existing_rows, headers

        # 2. Parse file content
        parsed = parse_import_file(
            filename=filename,
            content=content,
            max_bytes=settings.IMPORT_MAX_FILE_BYTES,
            max_rows=settings.IMPORT_MAX_ROWS,
            sheet_name=sheet_name,
        )

        # 3. Verify required headers
        processor = get_processor(import_type)
        required_headers = processor.get_required_headers()
        missing_headers = [h for h in required_headers if h not in parsed.headers]
        if missing_headers:
            raise ValidationException(
                f"Uploaded file is missing required column headers: {missing_headers}",
                details={
                    "missing_headers": missing_headers,
                    "required_headers": required_headers,
                    "detected_headers": parsed.headers,
                },
            )

        # 4. Create ImportJob header in VALIDATING state
        job = ImportJob(
            university_id=university_id,
            import_type=import_type.value,
            status=ImportJobStatus.VALIDATING.value,
            commit_mode=commit_mode.value,
            original_filename=filename,
            file_size=parsed.file_size,
            file_hash=parsed.file_hash,
            requested_by_user_id=requested_by_user_id,
            row_count=len(parsed.rows),
            idempotency_key=idempotency_key,
            metadata_json={
                "headers": parsed.headers,
                "raw_headers": parsed.raw_headers,
                "sheet_names": parsed.sheet_names,
                "selected_sheet": parsed.selected_sheet,
            },
        )
        db.add(job)
        await db.flush()

        # 5. Row-by-row domain validation
        valid_count = 0
        warning_count = 0
        error_count = 0
        staged_rows: list[ImportRow] = []
        seen_keys: dict[str, Any] = {}

        for parsed_row in parsed.rows:
            norm_data, action, status, errors, warnings = await processor.validate_row(
                db=db,
                university_id=university_id,
                row_number=parsed_row.row_number,
                raw_data=parsed_row.raw_data,
                seen_keys=seen_keys,
            )

            if status == ImportRowStatus.VALID.value:
                valid_count += 1
            elif status == ImportRowStatus.WARNING.value:
                warning_count += 1
            else:
                error_count += 1

            row_record = ImportRow(
                import_job_id=job.id,
                row_number=parsed_row.row_number,
                raw_data=parsed_row.raw_data,
                normalized_data=norm_data,
                action=action,
                status=status,
                errors=errors if errors else None,
                warnings=warnings if warnings else None,
            )
            db.add(row_record)
            staged_rows.append(row_record)

        # 6. Update Job tallies and final preview status
        job.valid_count = valid_count
        job.warning_count = warning_count
        job.error_count = error_count
        job.status = ImportJobStatus.READY.value

        await db.commit()
        await db.refresh(job)

        logger.info(
            "Import preview generated: job_id=%s, type=%s, rows=%d (valid=%d, warn=%d, err=%d)",
            job.id,
            job.import_type,
            job.row_count,
            valid_count,
            warning_count,
            error_count,
        )
        return job, staged_rows, parsed.headers

    @staticmethod
    async def commit_import_job(
        db: AsyncSession,
        university_id: uuid.UUID,
        job_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        commit_mode_override: ImportCommitMode | None = None,
    ) -> ImportJob:
        """Atomically commit validated staged rows to production domain tables.

        Follows canonical rules:
        - Row-level locking on ImportJob header.
        - Strict validation mode blocks commit if error_count > 0.
        - Partial mode commits valid rows and marks error rows as SKIPPED.
        - Records immutable audit details in summary_json.
        """
        # 1. Lock job record
        stmt = select(ImportJob).where(ImportJob.id == job_id).with_for_update()
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()

        if not job or job.university_id != university_id:
            raise NotFoundException("ImportJob", job_id)

        # 2. Status invariants
        if job.status == ImportJobStatus.COMMITTING.value:
            raise ConflictException("Import job is currently being committed by another worker.")
        if job.status == ImportJobStatus.COMPLETED.value:
            raise ConflictException("Import job has already been completed.")
        if job.status == ImportJobStatus.CANCELLED.value:
            raise ConflictException("Import job was cancelled and cannot be committed.")

        # 3. Resolve commit mode
        effective_mode = commit_mode_override.value if commit_mode_override else job.commit_mode
        if effective_mode == ImportCommitMode.STRICT.value and job.error_count > 0:
            raise ValidationException(
                f"Cannot commit import job with {job.error_count} errors in STRICT mode. "
                "Resolve errors in the source dataset or select PARTIAL commit mode.",
                details={
                    "job_id": str(job.id),
                    "error_count": job.error_count,
                    "commit_mode": effective_mode,
                },
            )

        job.status = ImportJobStatus.COMMITTING.value
        job.commit_mode = effective_mode
        await db.flush()

        # 4. Fetch staged rows
        rows_stmt = (
            select(ImportRow)
            .where(ImportRow.import_job_id == job.id)
            .order_by(ImportRow.row_number.asc())
            .with_for_update()
        )
        rows_res = await db.execute(rows_stmt)
        rows = list(rows_res.scalars().all())

        processor = get_processor(job.import_type)
        committed_count = 0
        skipped_count = 0
        created_count = 0
        updated_count = 0
        created_entities: list[dict[str, Any]] = []
        updated_entities: list[dict[str, Any]] = []

        # 5. Execute transactional commit row-by-row
        for row in rows:
            if row.status in (ImportRowStatus.VALID.value, ImportRowStatus.WARNING.value):
                entity_id, entity_type = await processor.commit_row(
                    db=db,
                    university_id=university_id,
                    staged_row=row,
                    actor_user_id=actor_user_id,
                )
                row.resolved_entity_id = entity_id
                row.resolved_entity_type = entity_type
                row.status = ImportRowStatus.COMMITTED.value
                committed_count += 1

                if row.action == "CREATE":
                    created_count += 1
                    created_entities.append(
                        {"row": row.row_number, "id": str(entity_id), "type": entity_type}
                    )
                else:
                    updated_count += 1
                    updated_entities.append(
                        {"row": row.row_number, "id": str(entity_id), "type": entity_type}
                    )
            else:
                row.status = ImportRowStatus.SKIPPED.value
                skipped_count += 1

        # 6. Finalize job status and audit summary
        job.commit_count = committed_count
        job.status = ImportJobStatus.COMPLETED.value
        job.summary_json = {
            "committed_count": committed_count,
            "skipped_count": skipped_count,
            "created_count": created_count,
            "updated_count": updated_count,
            "committed_at_utc": utc_now().isoformat(),
            "committed_by_user_id": str(actor_user_id),
            "created_samples": created_entities[:10],
            "updated_samples": updated_entities[:10],
        }

        await db.commit()
        await db.refresh(job)

        logger.info(
            "Import job committed: job_id=%s, type=%s, committed=%d, skipped=%d",
            job.id,
            job.import_type,
            committed_count,
            skipped_count,
        )
        return job

    @staticmethod
    async def get_import_job(
        db: AsyncSession,
        university_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> ImportJob:
        """Retrieve import job header with tenant isolation."""
        stmt = select(ImportJob).where(
            ImportJob.id == job_id,
            ImportJob.university_id == university_id,
        )
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            raise NotFoundException("ImportJob", job_id)
        return job

    @staticmethod
    async def list_import_jobs(
        db: AsyncSession,
        university_id: uuid.UUID,
        import_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ImportJob], int]:
        """List historical and active import jobs for a university."""
        base_stmt = select(ImportJob).where(ImportJob.university_id == university_id)
        if import_type:
            base_stmt = base_stmt.where(ImportJob.import_type == import_type.upper())
        if status:
            base_stmt = base_stmt.where(ImportJob.status == status.upper())

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        query_stmt = base_stmt.order_by(ImportJob.created_at.desc()).limit(limit).offset(offset)
        items = list((await db.execute(query_stmt)).scalars().all())
        return items, total

    @staticmethod
    async def list_job_rows(
        db: AsyncSession,
        university_id: uuid.UUID,
        job_id: uuid.UUID,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ImportRow], int]:
        """List staged rows for an import job with optional status filtering."""
        # Verify job ownership
        await ImportService.get_import_job(db, university_id, job_id)

        base_stmt = select(ImportRow).where(ImportRow.import_job_id == job_id)
        if status:
            base_stmt = base_stmt.where(ImportRow.status == status.upper())

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        query_stmt = base_stmt.order_by(ImportRow.row_number.asc()).limit(limit).offset(offset)
        rows = list((await db.execute(query_stmt)).scalars().all())
        return rows, total

    @staticmethod
    async def cancel_import_job(
        db: AsyncSession,
        university_id: uuid.UUID,
        job_id: uuid.UUID,
        actor_user_id: uuid.UUID,
    ) -> ImportJob:
        """Cancel a staged import job preventing its execution."""
        stmt = (
            select(ImportJob)
            .where(
                ImportJob.id == job_id,
                ImportJob.university_id == university_id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            raise NotFoundException("ImportJob", job_id)

        if job.status == ImportJobStatus.COMPLETED.value:
            raise ConflictException("Cannot cancel a completed import job.")
        if job.status == ImportJobStatus.CANCELLED.value:
            return job

        job.status = ImportJobStatus.CANCELLED.value
        job.failure_reason = f"Cancelled by user {actor_user_id}."

        # Mark all pending rows as skipped
        rows_stmt = select(ImportRow).where(
            ImportRow.import_job_id == job.id,
            ImportRow.status != ImportRowStatus.COMMITTED.value,
        )
        rows_res = await db.execute(rows_stmt)
        for r in rows_res.scalars().all():
            r.status = ImportRowStatus.SKIPPED.value

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    def get_template_spec(import_type: ImportType) -> ImportTemplateResponse:
        """Return schema columns and sample CSV template for an import type."""
        processor = get_processor(import_type)
        return ImportTemplateResponse(
            import_type=import_type,
            columns=processor.get_template(),
            csv_sample=processor.get_sample_csv(),
        )
