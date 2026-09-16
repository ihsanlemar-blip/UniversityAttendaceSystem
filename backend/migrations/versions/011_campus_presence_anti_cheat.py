"""Campus network presence, short-lived network challenge, and anti-cheat hardening.

Revision ID: 011_campus_presence_anti_cheat
Revises: 010_device_registration_trust
Create Date: 2026-09-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers (<= 32 chars for alembic_version)
revision: str = "011_campus_presence_anti_cheat"
down_revision: str | None = "010_device_registration_trust"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating campus network zones, challenges, risk signals, and policy."""
    # 1. campus_network_zones table
    op.create_table(
        "campus_network_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("network_cidr", sa.String(length=64), nullable=False),
        sa.Column("ip_version", sa.Integer(), server_default="4", nullable=False),
        sa.Column(
            "zone_type", sa.String(length=30), server_default="CAMPUS_TRUSTED", nullable=False
        ),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column(
            "allow_student_presence",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_lecturer_operations",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_campus_network_zones_university_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["building_id"],
            ["buildings.id"],
            name="fk_campus_network_zones_building_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "university_id",
            "code",
            name="uq_campus_network_zones_uni_code",
        ),
    )
    op.create_index(
        "ix_campus_network_zones_id",
        "campus_network_zones",
        ["id"],
    )
    op.create_index(
        "ix_campus_network_zones_uni_status",
        "campus_network_zones",
        ["university_id", "status"],
    )
    op.create_index(
        "ix_campus_network_zones_building_id",
        "campus_network_zones",
        ["building_id"],
    )

    # 2. campus_network_challenges table
    op.create_table(
        "campus_network_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trusted_device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("network_zone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("nonce_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ISSUED", nullable=False),
        sa.Column("proof_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_campus_network_challenges_university_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_campus_network_challenges_user_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["trusted_device_id"],
            ["trusted_devices.id"],
            name="fk_campus_network_challenges_device_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"],
            ["attendance_sessions.id"],
            name="fk_campus_network_challenges_session_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_checkpoint_id"],
            ["attendance_checkpoints.id"],
            name="fk_campus_network_challenges_checkpoint_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["network_zone_id"],
            ["campus_network_zones.id"],
            name="fk_campus_network_challenges_zone_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_campus_network_challenges_id",
        "campus_network_challenges",
        ["id"],
    )
    op.create_index(
        "ix_campus_network_challenges_user_status",
        "campus_network_challenges",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_campus_network_challenges_expiry",
        "campus_network_challenges",
        ["expires_at", "status"],
    )
    op.create_index(
        "ix_campus_network_challenges_session_cp",
        "campus_network_challenges",
        ["attendance_session_id", "attendance_checkpoint_id"],
    )
    op.create_index(
        "ix_campus_network_challenges_nonce_hash",
        "campus_network_challenges",
        ["nonce_hash"],
    )

    # 3. attendance_risk_signals table
    op.create_table(
        "attendance_risk_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="INFO", nullable=False),
        sa.Column("risk_points", sa.Integer(), nullable=True),
        sa.Column("subject_type", sa.String(length=30), server_default="STUDENT", nullable=False),
        sa.Column("subject_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trusted_device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attendance_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("class_occurrence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("course_offering_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rule_version", sa.String(length=20), server_default="1.0", nullable=False),
        sa.Column("risk_key", sa.String(length=255), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), server_default="OPEN", nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_note", sa.String(length=1000), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_attendance_risk_signals_university_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["users.id"],
            name="fk_attendance_risk_signals_subject_user_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["trusted_device_id"],
            ["trusted_devices.id"],
            name="fk_attendance_risk_signals_device_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_session_id"],
            ["attendance_sessions.id"],
            name="fk_attendance_risk_signals_session_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["class_occurrence_id"],
            ["class_occurrences.id"],
            name="fk_attendance_risk_signals_occurrence_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["course_offering_id"],
            ["course_offerings.id"],
            name="fk_attendance_risk_signals_offering_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_attendance_risk_signals_reviewer_id",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "university_id",
            "risk_key",
            name="uq_attendance_risk_signals_key",
        ),
    )
    op.create_index(
        "ix_attendance_risk_signals_id",
        "attendance_risk_signals",
        ["id"],
    )
    op.create_index(
        "ix_attendance_risk_signals_uni_status",
        "attendance_risk_signals",
        ["university_id", "status", "detected_at"],
    )
    op.create_index(
        "ix_attendance_risk_signals_type_sev",
        "attendance_risk_signals",
        ["university_id", "signal_type", "severity"],
    )
    op.create_index(
        "ix_attendance_risk_signals_subject_user",
        "attendance_risk_signals",
        ["subject_user_id"],
    )
    op.create_index(
        "ix_attendance_risk_signals_session",
        "attendance_risk_signals",
        ["attendance_session_id"],
    )
    op.create_index(
        "ix_attendance_risk_signals_occurrence",
        "attendance_risk_signals",
        ["class_occurrence_id"],
    )

    # 4. Alter attendance_policies table
    op.add_column(
        "attendance_policies",
        sa.Column(
            "network_presence_mode",
            sa.String(length=20),
            server_default="DISABLED",
            nullable=False,
        ),
    )
    op.add_column(
        "attendance_policies",
        sa.Column(
            "lecturer_network_presence_mode",
            sa.String(length=20),
            server_default="DISABLED",
            nullable=False,
        ),
    )
    op.add_column(
        "attendance_policies",
        sa.Column(
            "allow_university_wide_zones",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Revert migration removing campus network zones, challenges, and risk signals."""
    # 1. Revert attendance_policies columns
    op.drop_column("attendance_policies", "allow_university_wide_zones")
    op.drop_column("attendance_policies", "lecturer_network_presence_mode")
    op.drop_column("attendance_policies", "network_presence_mode")

    # 2. Drop tables in reverse order of foreign key dependencies
    op.drop_table("attendance_risk_signals")
    op.drop_table("campus_network_challenges")
    op.drop_table("campus_network_zones")
