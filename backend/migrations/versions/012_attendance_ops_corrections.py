"""Attendance operations, corrections, excuses, leave and immutable workflow foundation.

Revision ID: 012_attendance_ops_corrections
Revises: 011_campus_presence_anti_cheat
Create Date: 2026-09-17 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers (<= 32 chars for alembic_version)
revision: str = "012_attendance_ops_corrections"
down_revision: str | None = "011_campus_presence_anti_cheat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating attendance correction, excuse, and leave tables."""
    # 1. attendance_correction_requests table
    op.create_table(
        "attendance_correction_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("requested_status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("supporting_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attendance_record_id"],
            ["attendance_records.id"],
            name="fk_att_corr_req_record_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"],
            ["attendance_sessions.id"],
            name="fk_att_corr_req_session_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_att_corr_req_reviewer_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_att_corr_req_student_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_att_corr_req_university_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_attendance_correction_requests_id",
        "attendance_correction_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_corrections_student_status",
        "attendance_correction_requests",
        ["student_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_corrections_session_status",
        "attendance_correction_requests",
        ["attendance_session_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_corrections_university_status",
        "attendance_correction_requests",
        ["university_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_corrections_record_id",
        "attendance_correction_requests",
        ["attendance_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_corrections_reviewer_id",
        "attendance_correction_requests",
        ["reviewed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "uq_open_correction_request_per_record",
        "attendance_correction_requests",
        ["attendance_record_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'UNDER_REVIEW')"),
    )

    # 2. attendance_excuse_requests table
    op.create_table(
        "attendance_excuse_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attendance_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("class_occurrence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("document_reference", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attendance_record_id"],
            ["attendance_records.id"],
            name="fk_att_exc_req_record_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"],
            ["attendance_sessions.id"],
            name="fk_att_exc_req_session_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["class_occurrence_id"],
            ["class_occurrences.id"],
            name="fk_att_exc_req_occurrence_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_att_exc_req_reviewer_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_att_exc_req_student_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_att_exc_req_university_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_attendance_excuse_requests_id",
        "attendance_excuse_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_excuses_student_status",
        "attendance_excuse_requests",
        ["student_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_excuses_session_status",
        "attendance_excuse_requests",
        ["attendance_session_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_excuses_university_status",
        "attendance_excuse_requests",
        ["university_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_excuses_record_id",
        "attendance_excuse_requests",
        ["attendance_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_excuses_occurrence_id",
        "attendance_excuse_requests",
        ["class_occurrence_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_excuses_reviewer_id",
        "attendance_excuse_requests",
        ["reviewed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "uq_open_excuse_request_per_session_student",
        "attendance_excuse_requests",
        ["attendance_session_id", "student_id"],
        unique=True,
        postgresql_where=sa.text(
            "attendance_session_id IS NOT NULL AND status IN ('PENDING', 'UNDER_REVIEW')"
        ),
    )
    op.create_index(
        "uq_open_excuse_request_per_occurrence_student",
        "attendance_excuse_requests",
        ["class_occurrence_id", "student_id"],
        unique=True,
        postgresql_where=sa.text(
            "class_occurrence_id IS NOT NULL AND status IN ('PENDING', 'UNDER_REVIEW')"
        ),
    )

    # 3. attendance_leave_requests table
    op.create_table(
        "attendance_leave_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["class_occurrence_id"],
            ["class_occurrences.id"],
            name="fk_att_leave_req_occurrence_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_att_leave_req_reviewer_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_att_leave_req_student_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_att_leave_req_university_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_attendance_leave_requests_id",
        "attendance_leave_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_leave_student_status",
        "attendance_leave_requests",
        ["student_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_leave_occurrence_status",
        "attendance_leave_requests",
        ["class_occurrence_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_leave_university_status",
        "attendance_leave_requests",
        ["university_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_leave_reviewer_id",
        "attendance_leave_requests",
        ["reviewed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "uq_open_leave_request_per_occurrence_student",
        "attendance_leave_requests",
        ["class_occurrence_id", "student_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'UNDER_REVIEW')"),
    )


def downgrade() -> None:
    """Revert migration dropping attendance correction, excuse, and leave tables."""
    op.drop_table("attendance_leave_requests")
    op.drop_table("attendance_excuse_requests")
    op.drop_table("attendance_correction_requests")
