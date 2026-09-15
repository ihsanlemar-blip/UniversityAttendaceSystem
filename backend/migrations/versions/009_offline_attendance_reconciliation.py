"""Offline attendance permits, sessions, event chains, claims, inbox, conflicts.

Revision ID: 009_offline_attendance
Revises: 008_attendance_core
Create Date: 2026-09-15 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers (<= 32 chars for alembic_version)
revision: str = "009_offline_attendance"
down_revision: str | None = "008_attendance_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating offline attendance and reconciliation tables."""
    # 1. offline_attendance_permits table
    op.create_table(
        "offline_attendance_permits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lecturer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("temporary_host_public_key", sa.String(length=500), nullable=False),
        sa.Column("authority_epoch", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "roster_snapshot_digest",
            sa.String(length=64),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "policy_snapshot_digest",
            sa.String(length=64),
            server_default="",
            nullable=False,
        ),
        sa.Column("valid_from_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ISSUED", nullable=False),
        sa.Column("signed_permit_token", sa.Text(), nullable=False),
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
            name="fk_offline_permits_university_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"],
            ["attendance_sessions.id"],
            name="fk_offline_permits_session_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["class_occurrence_id"],
            ["class_occurrences.id"],
            name="fk_offline_permits_occurrence_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lecturer_user_id"],
            ["users.id"],
            name="fk_offline_permits_lecturer_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_offline_attendance_permits_id",
        "offline_attendance_permits",
        ["id"],
    )
    op.create_index(
        "ix_offline_permits_session_id",
        "offline_attendance_permits",
        ["attendance_session_id"],
    )
    op.create_index(
        "ix_offline_permits_occurrence_id",
        "offline_attendance_permits",
        ["class_occurrence_id"],
    )
    op.create_index(
        "ix_offline_permits_lecturer_id",
        "offline_attendance_permits",
        ["lecturer_user_id"],
    )
    op.create_index(
        "ix_offline_permits_status",
        "offline_attendance_permits",
        ["status"],
    )

    # 2. offline_host_sessions table
    op.create_table(
        "offline_host_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("offline_permit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_device_id", sa.String(length=128), nullable=False),
        sa.Column("clock_anchor_server_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clock_anchor_uptime_ms", sa.BigInteger(), nullable=False),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_event_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("synced_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["offline_permit_id"],
            ["offline_attendance_permits.id"],
            name="fk_offline_host_sessions_permit_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_offline_host_sessions_id",
        "offline_host_sessions",
        ["id"],
    )
    op.create_index(
        "ix_offline_host_sessions_permit_id",
        "offline_host_sessions",
        ["offline_permit_id"],
    )
    op.create_index(
        "ix_offline_host_sessions_status",
        "offline_host_sessions",
        ["status"],
    )

    # 3. offline_host_events table
    op.create_table(
        "offline_host_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("offline_host_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("prev_event_hash", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["offline_host_session_id"],
            ["offline_host_sessions.id"],
            name="fk_offline_host_events_session_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "offline_host_session_id",
            "sequence_number",
            name="uq_offline_host_events_session_seq",
        ),
    )
    op.create_index(
        "ix_offline_host_events_id",
        "offline_host_events",
        ["id"],
    )
    op.create_index(
        "ix_offline_host_events_session_id",
        "offline_host_events",
        ["offline_host_session_id"],
    )

    # 4. offline_attendance_claims table
    op.create_table(
        "offline_attendance_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("offline_permit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offline_host_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_type", sa.String(length=20), nullable=False),
        sa.Column("rotation_slot", sa.Integer(), nullable=False),
        sa.Column("qr_challenge_token", sa.Text(), nullable=False),
        sa.Column("ble_evidence_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="PENDING_HOST_EVENTS",
            nullable=False,
        ),
        sa.Column("rejection_reason", sa.String(length=255), nullable=True),
        sa.Column("attendance_evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_monotonic_offset_ms", sa.BigInteger(), nullable=True),
        sa.Column("client_captured_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "server_synced_at_utc",
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
            ["offline_permit_id"],
            ["offline_attendance_permits.id"],
            name="fk_offline_claims_permit_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["offline_host_session_id"],
            ["offline_host_sessions.id"],
            name="fk_offline_claims_host_session_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_offline_claims_student_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"],
            ["users.id"],
            name="fk_offline_claims_user_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_evidence_id"],
            ["attendance_evidence.id"],
            name="fk_offline_claims_evidence_id",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "offline_permit_id",
            "student_id",
            "checkpoint_type",
            name="uq_offline_claims_permit_student_cpt",
        ),
    )
    op.create_index(
        "ix_offline_attendance_claims_id",
        "offline_attendance_claims",
        ["id"],
    )
    op.create_index(
        "ix_offline_claims_permit_id",
        "offline_attendance_claims",
        ["offline_permit_id"],
    )
    op.create_index(
        "ix_offline_claims_student_id",
        "offline_attendance_claims",
        ["student_id"],
    )
    op.create_index(
        "ix_offline_claims_status",
        "offline_attendance_claims",
        ["status"],
    )

    # 5. sync_inbox_entries table
    op.create_table(
        "sync_inbox_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_batch_id", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_type", sa.String(length=50), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PROCESSED", nullable=False),
        sa.Column(
            "processed_at_utc",
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
            ["actor_user_id"],
            ["users.id"],
            name="fk_sync_inbox_actor_user_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "client_batch_id",
            "idempotency_key",
            name="uq_sync_inbox_batch_idempotency",
        ),
    )
    op.create_index(
        "ix_sync_inbox_entries_id",
        "sync_inbox_entries",
        ["id"],
    )
    op.create_index(
        "ix_sync_inbox_actor_id",
        "sync_inbox_entries",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_sync_inbox_status",
        "sync_inbox_entries",
        ["status"],
    )

    # 6. offline_sync_conflicts table
    op.create_table(
        "offline_sync_conflicts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("attendance_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offline_permit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conflict_type", sa.String(length=50), nullable=False),
        sa.Column(
            "resolution_status",
            sa.String(length=30),
            server_default="UNRESOLVED",
            nullable=False,
        ),
        sa.Column("conflict_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.String(length=500), nullable=True),
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
            name="fk_offline_conflicts_session_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["offline_permit_id"],
            ["offline_attendance_permits.id"],
            name="fk_offline_conflicts_permit_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_offline_conflicts_student_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"],
            ["users.id"],
            name="fk_offline_conflicts_resolver_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_offline_sync_conflicts_id",
        "offline_sync_conflicts",
        ["id"],
    )
    op.create_index(
        "ix_offline_conflicts_session_id",
        "offline_sync_conflicts",
        ["attendance_session_id"],
    )
    op.create_index(
        "ix_offline_conflicts_permit_id",
        "offline_sync_conflicts",
        ["offline_permit_id"],
    )
    op.create_index(
        "ix_offline_conflicts_status",
        "offline_sync_conflicts",
        ["resolution_status"],
    )


def downgrade() -> None:
    """Revert migration dropping offline attendance tables in reverse dependency order."""
    op.drop_table("offline_sync_conflicts")
    op.drop_table("sync_inbox_entries")
    op.drop_table("offline_attendance_claims")
    op.drop_table("offline_host_events")
    op.drop_table("offline_host_sessions")
    op.drop_table("offline_attendance_permits")
