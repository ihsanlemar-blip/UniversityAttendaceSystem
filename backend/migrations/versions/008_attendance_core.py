"""Attendance core engine, policies, sessions, checkpoints, records, and revisions migration.

Revision ID: 008_attendance_core
Revises: 007_timetable_and_occurrences
Create Date: 2026-09-14 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers (<= 32 chars for alembic_version)
revision: str = "008_attendance_core"
down_revision: str | None = "007_timetable_and_occurrences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating attendance core tables."""
    # 1. attendance_policies table
    op.create_table(
        "attendance_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("academic_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("scope_type", sa.String(length=20), server_default="UNIVERSITY", nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "min_attendance_percentage",
            sa.Numeric(5, 2),
            server_default="75.00",
            nullable=False,
        ),
        sa.Column("late_threshold_minutes", sa.Integer(), server_default="10", nullable=False),
        sa.Column(
            "lecturer_correction_window_hours",
            sa.Integer(),
            server_default="24",
            nullable=False,
        ),
        sa.Column(
            "required_checkpoint_count",
            sa.Integer(),
            server_default="3",
            nullable=False,
        ),
        sa.Column(
            "checkpoint_duration_seconds",
            sa.Integer(),
            server_default="300",
            nullable=False,
        ),
        sa.Column("token_rotation_seconds", sa.Integer(), server_default="30", nullable=False),
        sa.Column(
            "checkpoint_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='{"START": 1.0, "MIDDLE": 1.0, "END": 1.0}',
            nullable=False,
        ),
        sa.Column(
            "status_mapping",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=(
                '{"111": "PRESENT", "110": "PRESENT", "101": "PRESENT", "011": "LATE", '
                '"100": "LATE", "010": "LATE", "001": "ABSENT", "000": "ABSENT"}'
            ),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_att_policies_university_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_unit_id"],
            ["academic_units.id"],
            name="fk_att_policies_unit_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_att_policies_course_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "min_attendance_percentage >= 0 AND min_attendance_percentage <= 100",
            name="ck_attendance_policies_min_pct",
        ),
        sa.CheckConstraint(
            "checkpoint_duration_seconds >= 60 AND checkpoint_duration_seconds <= 3600",
            name="ck_attendance_policies_duration",
        ),
        sa.CheckConstraint(
            "late_threshold_minutes >= 0 AND late_threshold_minutes <= 120",
            name="ck_attendance_policies_late_thresh",
        ),
    )
    op.create_index(
        "ix_attendance_policies_id",
        "attendance_policies",
        ["id"],
    )
    op.create_index(
        "ix_attendance_policies_university_id",
        "attendance_policies",
        ["university_id"],
    )
    op.create_index(
        "ix_attendance_policies_academic_unit_id",
        "attendance_policies",
        ["academic_unit_id"],
    )
    op.create_index(
        "ix_attendance_policies_course_id",
        "attendance_policies",
        ["course_id"],
    )
    op.create_index(
        "ix_attendance_policies_scope_id",
        "attendance_policies",
        ["scope_id"],
    )
    op.create_index(
        "ix_attendance_policies_scope_lookup",
        "attendance_policies",
        ["university_id", "scope_type", "scope_id"],
    )

    # 2. attendance_sessions table
    op.create_table(
        "attendance_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="SCHEDULED", nullable=False),
        sa.Column("host_type", sa.String(length=30), server_default="LOCAL_SERVER", nullable=False),
        sa.Column("opened_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resumed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_att_sessions_university_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["class_occurrence_id"],
            ["class_occurrences.id"],
            name="fk_att_sessions_occurrence_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_policy_id"],
            ["attendance_policies.id"],
            name="fk_att_sessions_policy_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opened_by_user_id"],
            ["users.id"],
            name="fk_att_sessions_opened_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["closed_by_user_id"],
            ["users.id"],
            name="fk_att_sessions_closed_by",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_attendance_sessions_id",
        "attendance_sessions",
        ["id"],
    )
    op.create_index(
        "ix_attendance_sessions_class_occurrence_id",
        "attendance_sessions",
        ["class_occurrence_id"],
        unique=True,
    )
    op.create_index(
        "ix_attendance_sessions_university_id",
        "attendance_sessions",
        ["university_id"],
    )
    op.create_index(
        "ix_attendance_sessions_attendance_policy_id",
        "attendance_sessions",
        ["attendance_policy_id"],
    )
    op.create_index(
        "ix_attendance_sessions_status",
        "attendance_sessions",
        ["status"],
    )
    op.create_index(
        "ix_attendance_sessions_status_occurrence",
        "attendance_sessions",
        ["status", "class_occurrence_id"],
    )
    op.create_index(
        "ix_attendance_sessions_university_status",
        "attendance_sessions",
        ["university_id", "status"],
    )

    # 3. attendance_checkpoints table
    op.create_table(
        "attendance_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("attendance_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_type", sa.String(length=20), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="SCHEDULED", nullable=False),
        sa.Column(
            "window_duration_seconds",
            sa.Integer(),
            server_default="300",
            nullable=False,
        ),
        sa.Column("opened_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"],
            ["attendance_sessions.id"],
            name="fk_att_checkpoints_session_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opened_by_user_id"],
            ["users.id"],
            name="fk_att_checkpoints_opened_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["closed_by_user_id"],
            ["users.id"],
            name="fk_att_checkpoints_closed_by",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "attendance_session_id",
            "checkpoint_type",
            name="uq_attendance_checkpoints_session_type",
        ),
        sa.UniqueConstraint(
            "attendance_session_id",
            "sequence_no",
            name="uq_attendance_checkpoints_session_seq",
        ),
        sa.CheckConstraint(
            "checkpoint_type IN ('START', 'MIDDLE', 'END')",
            name="ck_attendance_checkpoints_type",
        ),
        sa.CheckConstraint(
            "sequence_no IN (1, 2, 3)",
            name="ck_attendance_checkpoints_sequence",
        ),
    )
    op.create_index(
        "ix_attendance_checkpoints_id",
        "attendance_checkpoints",
        ["id"],
    )
    op.create_index(
        "ix_attendance_checkpoints_attendance_session_id",
        "attendance_checkpoints",
        ["attendance_session_id"],
    )
    op.create_index(
        "ix_attendance_checkpoints_session_status",
        "attendance_checkpoints",
        ["attendance_session_id", "status"],
    )

    # 4. attendance_evidence table
    op.create_table(
        "attendance_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("attendance_checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_mode", sa.String(length=30), server_default="MANUAL", nullable=False),
        sa.Column(
            "server_received_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("manual_reason", sa.String(length=500), nullable=True),
        sa.Column("evidence_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attendance_checkpoint_id"],
            ["attendance_checkpoints.id"],
            name="fk_att_evidence_checkpoint_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_att_evidence_student_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"],
            ["users.id"],
            name="fk_att_evidence_user_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "attendance_checkpoint_id",
            "student_id",
            name="uq_attendance_evidence_checkpoint_student",
        ),
    )
    op.create_index(
        "ix_attendance_evidence_id",
        "attendance_evidence",
        ["id"],
    )
    op.create_index(
        "ix_attendance_evidence_attendance_checkpoint_id",
        "attendance_evidence",
        ["attendance_checkpoint_id"],
    )
    op.create_index(
        "ix_attendance_evidence_student_id",
        "attendance_evidence",
        ["student_id"],
    )
    op.create_index(
        "ix_attendance_evidence_checkpoint_student",
        "attendance_evidence",
        ["attendance_checkpoint_id", "student_id"],
    )
    op.create_index(
        "ix_attendance_evidence_student_received",
        "attendance_evidence",
        ["student_id", "server_received_at_utc"],
    )
    op.create_index(
        "ix_attendance_evidence_request_id",
        "attendance_evidence",
        ["request_id"],
    )

    # 5. attendance_records table
    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("attendance_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("start_credited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("middle_credited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("end_credited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("checkpoints_verified", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "attendance_credit",
            sa.Numeric(5, 2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column("is_manual", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("manual_reason", sa.String(length=500), nullable=True),
        sa.Column("calculation_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("finalized_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version_no", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"],
            ["attendance_sessions.id"],
            name="fk_att_records_session_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_att_records_student_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "attendance_session_id",
            "student_id",
            name="uq_attendance_records_session_student",
        ),
    )
    op.create_index(
        "ix_attendance_records_id",
        "attendance_records",
        ["id"],
    )
    op.create_index(
        "ix_attendance_records_attendance_session_id",
        "attendance_records",
        ["attendance_session_id"],
    )
    op.create_index(
        "ix_attendance_records_student_id",
        "attendance_records",
        ["student_id"],
    )
    op.create_index(
        "ix_attendance_records_status",
        "attendance_records",
        ["status"],
    )
    op.create_index(
        "ix_attendance_records_session_status",
        "attendance_records",
        ["attendance_session_id", "status"],
    )
    op.create_index(
        "ix_attendance_records_student_status",
        "attendance_records",
        ["student_id", "status"],
    )

    # 6. attendance_revisions table
    op.create_table(
        "attendance_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("attendance_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("previous_credit", sa.Numeric(5, 2), nullable=True),
        sa.Column("new_credit", sa.Numeric(5, 2), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "occurred_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"],
            ["attendance_sessions.id"],
            name="fk_att_revisions_session_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_record_id"],
            ["attendance_records.id"],
            name="fk_att_revisions_record_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_att_revisions_actor_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_attendance_revisions_id",
        "attendance_revisions",
        ["id"],
    )
    op.create_index(
        "ix_attendance_revisions_attendance_session_id",
        "attendance_revisions",
        ["attendance_session_id"],
    )
    op.create_index(
        "ix_attendance_revisions_attendance_record_id",
        "attendance_revisions",
        ["attendance_record_id"],
    )
    op.create_index(
        "ix_attendance_revisions_actor_user_id",
        "attendance_revisions",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_attendance_revisions_session_event",
        "attendance_revisions",
        ["attendance_session_id", "event_type"],
    )
    op.create_index(
        "ix_attendance_revisions_record_date",
        "attendance_revisions",
        ["attendance_record_id", "occurred_at_utc"],
    )
    op.create_index(
        "ix_attendance_revisions_actor_date",
        "attendance_revisions",
        ["actor_user_id", "occurred_at_utc"],
    )


def downgrade() -> None:
    """Revert migration dropping attendance core tables in reverse dependency order."""
    op.drop_table("attendance_revisions")
    op.drop_table("attendance_records")
    op.drop_table("attendance_evidence")
    op.drop_table("attendance_checkpoints")
    op.drop_table("attendance_sessions")
    op.drop_table("attendance_policies")
