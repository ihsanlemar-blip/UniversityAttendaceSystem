"""Data import staging and safe commit tables.

Revision ID: 013_imports_administration
Revises: 012_attendance_ops_corrections
Create Date: 2026-09-17 05:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers (<= 32 chars for alembic_version)
revision: str = "013_imports_administration"
down_revision: str | None = "012_attendance_ops_corrections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating import_jobs and import_rows tables."""
    # 1. import_jobs table
    op.create_table(
        "import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("commit_mode", sa.String(length=50), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_import_jobs_university_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name="fk_import_jobs_requested_by_user_id",
            ondelete="RESTRICT",
        ),
    )

    op.create_index("ix_import_jobs_id", "import_jobs", ["id"], unique=False)
    op.create_index("ix_import_jobs_university_id", "import_jobs", ["university_id"], unique=False)
    op.create_index("ix_import_jobs_import_type", "import_jobs", ["import_type"], unique=False)
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"], unique=False)
    op.create_index(
        "ix_import_jobs_requested_by_user_id",
        "import_jobs",
        ["requested_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_jobs_uni_type_status",
        "import_jobs",
        ["university_id", "import_type", "status"],
        unique=False,
    )
    op.create_index(
        "ix_import_jobs_uni_created",
        "import_jobs",
        ["university_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_import_jobs_idempotency", "import_jobs", ["idempotency_key"], unique=False)

    # 2. import_rows table
    op.create_table(
        "import_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("import_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalized_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False, server_default="CREATE"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="VALID"),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolved_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_entity_type", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_job_id"],
            ["import_jobs.id"],
            name="fk_import_rows_import_job_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("import_job_id", "row_number", name="uq_import_rows_job_row_number"),
    )

    op.create_index("ix_import_rows_id", "import_rows", ["id"], unique=False)
    op.create_index("ix_import_rows_import_job_id", "import_rows", ["import_job_id"], unique=False)
    op.create_index("ix_import_rows_status", "import_rows", ["status"], unique=False)
    op.create_index(
        "ix_import_rows_job_status",
        "import_rows",
        ["import_job_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Revert migration dropping import_rows and import_jobs tables."""
    op.drop_table("import_rows")
    op.drop_table("import_jobs")
