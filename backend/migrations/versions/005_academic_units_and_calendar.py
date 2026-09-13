"""Academic units and calendar migration.

Revision ID: 005_academic_units_and_calendar
Revises: 004_auth_sessions_attempts
Create Date: 2026-09-13 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "005_academic_units_and_calendar"
down_revision: str | None = "004_auth_sessions_attempts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating academic_units, academic_years, and semesters tables."""
    # 1. academic_units table
    op.create_table(
        "academic_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("unit_type", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
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
            name="fk_academic_units_university_id_universities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["academic_units.id"],
            name="fk_academic_units_parent_id_academic_units",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "university_id",
            "code",
            name="uq_academic_units_university_code",
        ),
    )
    op.create_index("ix_academic_units_id", "academic_units", ["id"], unique=False)
    op.create_index(
        "ix_academic_units_university_id", "academic_units", ["university_id"], unique=False
    )
    op.create_index("ix_academic_units_parent_id", "academic_units", ["parent_id"], unique=False)
    op.create_index(
        "ix_academic_units_university_parent",
        "academic_units",
        ["university_id", "parent_id"],
        unique=False,
    )
    op.create_index(
        "ix_academic_units_university_type",
        "academic_units",
        ["university_id", "unit_type"],
        unique=False,
    )

    # 2. academic_years table
    op.create_table(
        "academic_years",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
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
            name="fk_academic_years_university_id_universities",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "university_id",
            "code",
            name="uq_academic_years_university_code",
        ),
        sa.CheckConstraint(
            "start_date < end_date",
            name="ck_academic_years_date_range",
        ),
    )
    op.create_index("ix_academic_years_id", "academic_years", ["id"], unique=False)
    op.create_index(
        "ix_academic_years_university_id", "academic_years", ["university_id"], unique=False
    )
    op.create_index(
        "ix_academic_years_is_current",
        "academic_years",
        ["university_id", "is_current"],
        unique=False,
    )

    # 3. semesters table
    op.create_table(
        "semesters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("academic_year_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("sequence_order", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
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
            name="fk_semesters_university_id_universities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["academic_year_id"],
            ["academic_years.id"],
            name="fk_semesters_academic_year_id_academic_years",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "academic_year_id",
            "code",
            name="uq_semesters_academic_year_code",
        ),
        sa.CheckConstraint(
            "start_date < end_date",
            name="ck_semesters_date_range",
        ),
    )
    op.create_index("ix_semesters_id", "semesters", ["id"], unique=False)
    op.create_index("ix_semesters_university_id", "semesters", ["university_id"], unique=False)
    op.create_index(
        "ix_semesters_academic_year_id", "semesters", ["academic_year_id"], unique=False
    )
    op.create_index(
        "ix_semesters_is_current",
        "semesters",
        ["university_id", "is_current"],
        unique=False,
    )


def downgrade() -> None:
    """Revert migration dropping semesters, academic_years, and academic_units tables."""
    # 1. Drop semesters
    op.drop_index("ix_semesters_is_current", table_name="semesters")
    op.drop_index("ix_semesters_academic_year_id", table_name="semesters")
    op.drop_index("ix_semesters_university_id", table_name="semesters")
    op.drop_index("ix_semesters_id", table_name="semesters")
    op.drop_table("semesters")

    # 2. Drop academic_years
    op.drop_index("ix_academic_years_is_current", table_name="academic_years")
    op.drop_index("ix_academic_years_university_id", table_name="academic_years")
    op.drop_index("ix_academic_years_id", table_name="academic_years")
    op.drop_table("academic_years")

    # 3. Drop academic_units
    op.drop_index("ix_academic_units_university_type", table_name="academic_units")
    op.drop_index("ix_academic_units_university_parent", table_name="academic_units")
    op.drop_index("ix_academic_units_parent_id", table_name="academic_units")
    op.drop_index("ix_academic_units_university_id", table_name="academic_units")
    op.drop_index("ix_academic_units_id", table_name="academic_units")
    op.drop_table("academic_units")
