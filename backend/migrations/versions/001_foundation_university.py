"""Foundation migration creating universities institutional table.

Revision ID: 001_foundation_university
Revises:
Create Date: 2026-09-13 13:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "001_foundation_university"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating universities table."""
    op.create_table(
        "universities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=50),
            server_default="Asia/Kabul",
            nullable=False,
        ),
        sa.Column(
            "default_language",
            sa.String(length=10),
            server_default="en",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="ACTIVE",
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_universities")),
        sa.UniqueConstraint("code", name=op.f("uq_universities_code")),
    )
    op.create_index(op.f("ix_universities_id"), "universities", ["id"], unique=False)
    op.create_index(op.f("ix_universities_code"), "universities", ["code"], unique=True)


def downgrade() -> None:
    """Revert migration dropping universities table."""
    op.drop_index(op.f("ix_universities_code"), table_name="universities")
    op.drop_index(op.f("ix_universities_id"), table_name="universities")
    op.drop_table("universities")
