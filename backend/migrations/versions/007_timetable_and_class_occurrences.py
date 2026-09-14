"""Facilities, timetable rules, and concrete class occurrences migration.

Revision ID: 007_timetable_and_occurrences
Revises: 006_curriculum_and_rosters
Create Date: 2026-09-13 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers (<= 32 chars for alembic_version)
revision: str = "007_timetable_and_occurrences"
down_revision: str | None = "006_curriculum_and_rosters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating buildings, rooms, timetables, and class_occurrences tables."""
    # 1. buildings table
    op.create_table(
        "buildings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
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
            name="fk_buildings_university_id_universities",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("university_id", "code", name="uq_buildings_university_code"),
    )
    op.create_index("ix_buildings_id", "buildings", ["id"], unique=False)
    op.create_index("ix_buildings_university_id", "buildings", ["university_id"], unique=False)
    op.create_index("ix_buildings_code", "buildings", ["code"], unique=False)

    # 2. rooms table
    op.create_table(
        "rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_number", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("room_type", sa.String(length=50), server_default="CLASSROOM", nullable=False),
        sa.Column("floor", sa.String(length=20), nullable=True),
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
            name="fk_rooms_university_id_universities",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["building_id"],
            ["buildings.id"],
            name="fk_rooms_building_id_buildings",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("building_id", "room_number", name="uq_rooms_building_room_number"),
        sa.CheckConstraint("capacity IS NULL OR capacity > 0", name="ck_rooms_capacity_positive"),
    )
    op.create_index("ix_rooms_id", "rooms", ["id"], unique=False)
    op.create_index("ix_rooms_university_id", "rooms", ["university_id"], unique=False)
    op.create_index("ix_rooms_building_id", "rooms", ["building_id"], unique=False)
    op.create_index("ix_rooms_room_number", "rooms", ["room_number"], unique=False)
    op.create_index(
        "ix_rooms_university_building", "rooms", ["university_id", "building_id"], unique=False
    )

    # 3. timetables table
    op.create_table(
        "timetables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_offering_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lecturer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
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
            name="fk_timetables_university_id_universities",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_offering_id"],
            ["course_offerings.id"],
            name="fk_timetables_course_offering_id_course_offerings",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name="fk_timetables_room_id_rooms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lecturer_id"],
            ["lecturers.id"],
            name="fk_timetables_lecturer_id_lecturers",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("start_time < end_time", name="ck_timetables_time_range"),
        sa.CheckConstraint("weekday >= 1 AND weekday <= 7", name="ck_timetables_weekday"),
        sa.CheckConstraint(
            "effective_from IS NULL OR effective_to IS NULL OR effective_from <= effective_to",
            name="ck_timetables_effective_range",
        ),
    )
    op.create_index("ix_timetables_id", "timetables", ["id"], unique=False)
    op.create_index("ix_timetables_university_id", "timetables", ["university_id"], unique=False)
    op.create_index(
        "ix_timetables_course_offering_id", "timetables", ["course_offering_id"], unique=False
    )
    op.create_index("ix_timetables_room_id", "timetables", ["room_id"], unique=False)
    op.create_index("ix_timetables_lecturer_id", "timetables", ["lecturer_id"], unique=False)
    op.create_index(
        "ix_timetables_offering_weekday",
        "timetables",
        ["course_offering_id", "weekday"],
        unique=False,
    )
    op.create_index(
        "ix_timetables_room_weekday", "timetables", ["room_id", "weekday"], unique=False
    )
    op.create_index(
        "ix_timetables_lecturer_weekday", "timetables", ["lecturer_id", "weekday"], unique=False
    )
    op.create_index(
        "ix_timetables_university_status", "timetables", ["university_id", "status"], unique=False
    )

    # 4. class_occurrences table
    op.create_table(
        "class_occurrences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_offering_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timetable_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lecturer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("substitute_lecturer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("scheduled_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="SCHEDULED", nullable=False),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("rescheduled_from_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rescheduled_to_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            name="fk_class_occurrences_university_id_universities",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_offering_id"],
            ["course_offerings.id"],
            name="fk_class_occurrences_course_offering_id_course_offerings",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["timetable_id"],
            ["timetables.id"],
            name="fk_class_occurrences_timetable_id_timetables",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name="fk_class_occurrences_room_id_rooms",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lecturer_id"],
            ["lecturers.id"],
            name="fk_class_occurrences_lecturer_id_lecturers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["substitute_lecturer_id"],
            ["lecturers.id"],
            name="fk_class_occurrences_substitute_lecturer_id_lecturers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rescheduled_from_id"],
            ["class_occurrences.id"],
            name="fk_class_occurrences_rescheduled_from_id_class_occurrences",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["rescheduled_to_id"],
            ["class_occurrences.id"],
            name="fk_class_occurrences_rescheduled_to_id_class_occurrences",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "scheduled_start_utc < scheduled_end_utc",
            name="ck_class_occurrences_time_range",
        ),
    )
    op.create_index("ix_class_occurrences_id", "class_occurrences", ["id"], unique=False)
    op.create_index(
        "ix_class_occurrences_university_id",
        "class_occurrences",
        ["university_id"],
        unique=False,
    )
    op.create_index(
        "ix_class_occurrences_course_offering_id",
        "class_occurrences",
        ["course_offering_id"],
        unique=False,
    )
    op.create_index(
        "ix_class_occurrences_timetable_id",
        "class_occurrences",
        ["timetable_id"],
        unique=False,
    )
    op.create_index(
        "ix_class_occurrences_room_id",
        "class_occurrences",
        ["room_id"],
        unique=False,
    )
    op.create_index(
        "ix_class_occurrences_lecturer_id",
        "class_occurrences",
        ["lecturer_id"],
        unique=False,
    )
    op.create_index(
        "ix_class_occurrences_substitute_lecturer_id",
        "class_occurrences",
        ["substitute_lecturer_id"],
        unique=False,
    )
    op.create_index(
        "uq_class_occurrences_timetable_start",
        "class_occurrences",
        ["timetable_id", "scheduled_start_utc"],
        unique=True,
        postgresql_where=sa.text("timetable_id IS NOT NULL"),
    )
    op.create_index(
        "ix_class_occurrences_offering_start",
        "class_occurrences",
        ["course_offering_id", "scheduled_start_utc"],
        unique=False,
    )
    op.create_index(
        "ix_class_occurrences_room_start",
        "class_occurrences",
        ["room_id", "scheduled_start_utc"],
        unique=False,
    )
    op.create_index(
        "ix_class_occurrences_lecturer_start",
        "class_occurrences",
        ["lecturer_id", "scheduled_start_utc"],
        unique=False,
    )
    op.create_index(
        "ix_class_occurrences_start_status",
        "class_occurrences",
        ["scheduled_start_utc", "status"],
        unique=False,
    )
    op.create_index(
        "ix_class_occurrences_local_date",
        "class_occurrences",
        ["university_id", "local_date"],
        unique=False,
    )


def downgrade() -> None:
    """Revert migration dropping class_occurrences, timetables, rooms, and buildings."""
    op.drop_table("class_occurrences")
    op.drop_table("timetables")
    op.drop_table("rooms")
    op.drop_table("buildings")
