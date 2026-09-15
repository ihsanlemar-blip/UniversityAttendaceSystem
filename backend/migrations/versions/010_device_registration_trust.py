"""Student device registration, primary device trust, replacement workflow, and audit ledger.

Revision ID: 010_device_registration_trust
Revises: 009_offline_attendance
Create Date: 2026-09-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers (<= 32 chars for alembic_version)
revision: str = "010_device_registration_trust"
down_revision: str | None = "009_offline_attendance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating trusted devices, challenges, replacements, and events."""
    # 1. trusted_devices table
    op.create_table(
        "trusted_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "device_role",
            sa.String(length=20),
            server_default="PRIMARY",
            nullable=False,
        ),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("public_key_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("installation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("platform", sa.String(length=30), nullable=True),
        sa.Column("device_label", sa.String(length=100), nullable=True),
        sa.Column("app_version", sa.String(length=30), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="PENDING_REGISTRATION",
            nullable=False,
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_device_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_device_id"],
            ["trusted_devices.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_trusted_devices_id",
        "trusted_devices",
        ["id"],
    )
    op.create_index(
        "ix_trusted_devices_fingerprint",
        "trusted_devices",
        ["public_key_fingerprint"],
        unique=True,
    )
    op.create_index(
        "ix_trusted_devices_uni_user",
        "trusted_devices",
        ["university_id", "user_id"],
    )
    op.create_index(
        "ix_trusted_devices_uni_student",
        "trusted_devices",
        ["university_id", "student_id"],
    )
    op.create_index(
        "ix_trusted_devices_status",
        "trusted_devices",
        ["status"],
    )
    op.create_index(
        "uq_trusted_devices_active_student",
        "trusted_devices",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    # 2. device_registration_challenges table
    op.create_table(
        "device_registration_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_public_key", sa.Text(), nullable=False),
        sa.Column("candidate_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("candidate_installation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("platform", sa.String(length=30), nullable=True),
        sa.Column("device_label", sa.String(length=100), nullable=True),
        sa.Column("app_version", sa.String(length=30), nullable=True),
        sa.Column(
            "purpose",
            sa.String(length=30),
            server_default="DEVICE_REGISTRATION",
            nullable=False,
        ),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("canonical_challenge", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_device_registration_challenges_id",
        "device_registration_challenges",
        ["id"],
    )
    op.create_index(
        "ix_device_reg_challenges_fingerprint",
        "device_registration_challenges",
        ["candidate_fingerprint"],
    )
    op.create_index(
        "ix_device_reg_challenges_user_active",
        "device_registration_challenges",
        ["user_id", "purpose", "used_at", "expires_at"],
    )

    # 3. device_replacement_requests table
    op.create_table(
        "device_replacement_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_public_key", sa.Text(), nullable=False),
        sa.Column("candidate_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("candidate_installation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("candidate_platform", sa.String(length=30), nullable=True),
        sa.Column("candidate_device_label", sa.String(length=100), nullable=True),
        sa.Column("candidate_app_version", sa.String(length=30), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("approved_device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["old_device_id"],
            ["trusted_devices.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_device_id"],
            ["trusted_devices.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_device_replacement_requests_id",
        "device_replacement_requests",
        ["id"],
    )
    op.create_index(
        "ix_device_replacements_uni_status",
        "device_replacement_requests",
        ["university_id", "status"],
    )
    op.create_index(
        "ix_device_replacements_student_status",
        "device_replacement_requests",
        ["student_id", "status"],
    )
    op.create_index(
        "ix_device_replacements_requested_at",
        "device_replacement_requests",
        ["requested_at"],
    )

    # 4. device_trust_events table
    op.create_table(
        "device_trust_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("replacement_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_student_id"],
            ["students.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["trusted_devices.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["replacement_request_id"],
            ["device_replacement_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_device_trust_events_id",
        "device_trust_events",
        ["id"],
    )
    op.create_index(
        "ix_device_trust_events_uni_user",
        "device_trust_events",
        ["university_id", "target_user_id", "created_at"],
    )
    op.create_index(
        "ix_device_trust_events_device_id",
        "device_trust_events",
        ["device_id"],
    )

    # 5. Alter offline_attendance_claims to add device binding columns
    op.add_column(
        "offline_attendance_claims",
        sa.Column("trusted_device_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "offline_attendance_claims",
        sa.Column("device_proof_signature", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_offline_claims_trusted_device",
        "offline_attendance_claims",
        "trusted_devices",
        ["trusted_device_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_offline_claims_device_id",
        "offline_attendance_claims",
        ["trusted_device_id"],
    )


def downgrade() -> None:
    """Revert migration removing trusted devices, challenges, replacements, and events."""
    op.drop_index("ix_offline_claims_device_id", table_name="offline_attendance_claims")
    op.drop_constraint(
        "fk_offline_claims_trusted_device",
        "offline_attendance_claims",
        type_="foreignkey",
    )
    op.drop_column("offline_attendance_claims", "device_proof_signature")
    op.drop_column("offline_attendance_claims", "trusted_device_id")

    op.drop_table("device_trust_events")
    op.drop_table("device_replacement_requests")
    op.drop_table("device_registration_challenges")
    op.drop_table("trusted_devices")
