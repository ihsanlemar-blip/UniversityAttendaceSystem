"""Curriculum, people profiles, sections, offerings, and enrollments migration.

Revision ID: 006_curriculum_and_rosters
Revises: 005_academic_units_and_calendar
Create Date: 2026-09-13 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers (<= 32 chars for alembic_version)
revision: str = "006_curriculum_and_rosters"
down_revision: str | None = "005_academic_units_and_calendar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration creating curriculum, people, offering, and enrollment tables."""
    # 1. courses table
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("academic_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("credit_hours", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=1000), nullable=True),
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
            name="fk_courses_university_id_universities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["academic_unit_id"],
            ["academic_units.id"],
            name="fk_courses_academic_unit_id_academic_units",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("university_id", "code", name="uq_courses_university_code"),
    )
    op.create_index("ix_courses_id", "courses", ["id"], unique=False)
    op.create_index("ix_courses_university_id", "courses", ["university_id"], unique=False)
    op.create_index("ix_courses_academic_unit_id", "courses", ["academic_unit_id"], unique=False)
    op.create_index(
        "ix_courses_university_code", "courses", ["university_id", "code"], unique=False
    )

    # 2. sections table
    op.create_table(
        "sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("academic_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
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
            name="fk_sections_university_id_universities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["academic_unit_id"],
            ["academic_units.id"],
            name="fk_sections_academic_unit_id_academic_units",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["semesters.id"],
            name="fk_sections_semester_id_semesters",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "university_id",
            "semester_id",
            "code",
            name="uq_sections_university_semester_code",
        ),
    )
    op.create_index("ix_sections_id", "sections", ["id"], unique=False)
    op.create_index("ix_sections_university_id", "sections", ["university_id"], unique=False)
    op.create_index("ix_sections_academic_unit_id", "sections", ["academic_unit_id"], unique=False)
    op.create_index("ix_sections_semester_id", "sections", ["semester_id"], unique=False)
    op.create_index(
        "ix_sections_university_code", "sections", ["university_id", "code"], unique=False
    )

    # 3. students table
    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_number", sa.String(length=50), nullable=False),
        sa.Column("academic_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admission_date", sa.Date(), nullable=True),
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
            ["user_id"],
            ["users.id"],
            name="fk_students_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_students_university_id_universities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["academic_unit_id"],
            ["academic_units.id"],
            name="fk_students_academic_unit_id_academic_units",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_students_section_id_sections",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "university_id",
            "student_number",
            name="uq_students_university_student_number",
        ),
    )
    op.create_index("ix_students_id", "students", ["id"], unique=False)
    op.create_index("ix_students_user_id", "students", ["user_id"], unique=True)
    op.create_index("ix_students_university_id", "students", ["university_id"], unique=False)
    op.create_index("ix_students_academic_unit_id", "students", ["academic_unit_id"], unique=False)
    op.create_index("ix_students_section_id", "students", ["section_id"], unique=False)
    op.create_index(
        "ix_students_university_student_number",
        "students",
        ["university_id", "student_number"],
        unique=False,
    )

    # 4. lecturers table
    op.create_table(
        "lecturers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_code", sa.String(length=50), nullable=False),
        sa.Column("academic_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=100), nullable=True),
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
            ["user_id"],
            ["users.id"],
            name="fk_lecturers_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_lecturers_university_id_universities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["academic_unit_id"],
            ["academic_units.id"],
            name="fk_lecturers_academic_unit_id_academic_units",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "university_id",
            "employee_code",
            name="uq_lecturers_university_employee_code",
        ),
    )
    op.create_index("ix_lecturers_id", "lecturers", ["id"], unique=False)
    op.create_index("ix_lecturers_user_id", "lecturers", ["user_id"], unique=True)
    op.create_index("ix_lecturers_university_id", "lecturers", ["university_id"], unique=False)
    op.create_index(
        "ix_lecturers_academic_unit_id", "lecturers", ["academic_unit_id"], unique=False
    )
    op.create_index(
        "ix_lecturers_university_employee_code",
        "lecturers",
        ["university_id", "employee_code"],
        unique=False,
    )

    # 5. course_offerings table
    op.create_table(
        "course_offerings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("academic_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            name="fk_course_offerings_university_id_universities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_course_offerings_course_id_courses",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["semesters.id"],
            name="fk_course_offerings_semester_id_semesters",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_course_offerings_section_id_sections",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_unit_id"],
            ["academic_units.id"],
            name="fk_course_offerings_academic_unit_id_academic_units",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_course_offerings_id", "course_offerings", ["id"], unique=False)
    op.create_index(
        "ix_course_offerings_university_id", "course_offerings", ["university_id"], unique=False
    )
    op.create_index(
        "ix_course_offerings_course_id", "course_offerings", ["course_id"], unique=False
    )
    op.create_index(
        "ix_course_offerings_semester_id", "course_offerings", ["semester_id"], unique=False
    )
    op.create_index(
        "ix_course_offerings_section_id", "course_offerings", ["section_id"], unique=False
    )
    op.create_index(
        "ix_course_offerings_academic_unit_id",
        "course_offerings",
        ["academic_unit_id"],
        unique=False,
    )
    op.create_index(
        "ix_course_offerings_course_semester",
        "course_offerings",
        ["course_id", "semester_id"],
        unique=False,
    )
    op.create_index(
        "uq_course_offerings_with_section",
        "course_offerings",
        ["university_id", "course_id", "semester_id", "section_id"],
        unique=True,
        postgresql_where=sa.text("section_id IS NOT NULL"),
    )
    op.create_index(
        "uq_course_offerings_without_section",
        "course_offerings",
        ["university_id", "course_id", "semester_id"],
        unique=True,
        postgresql_where=sa.text("section_id IS NULL"),
    )

    # 6. lecturer_assignments table
    op.create_table(
        "lecturer_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_offering_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lecturer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "assignment_type",
            sa.String(length=30),
            server_default="PRIMARY",
            nullable=False,
        ),
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
            ["course_offering_id"],
            ["course_offerings.id"],
            name="fk_lecturer_assignments_course_offering_id_course_offerings",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lecturer_id"],
            ["lecturers.id"],
            name="fk_lecturer_assignments_lecturer_id_lecturers",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "course_offering_id",
            "lecturer_id",
            name="uq_lecturer_assignments_offering_lecturer",
        ),
    )
    op.create_index("ix_lecturer_assignments_id", "lecturer_assignments", ["id"], unique=False)
    op.create_index(
        "ix_lecturer_assignments_course_offering_id",
        "lecturer_assignments",
        ["course_offering_id"],
        unique=False,
    )
    op.create_index(
        "ix_lecturer_assignments_lecturer_id",
        "lecturer_assignments",
        ["lecturer_id"],
        unique=False,
    )
    op.create_index(
        "uq_primary_lecturer_per_offering",
        "lecturer_assignments",
        ["course_offering_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
    )

    # 7. enrollments table
    op.create_table(
        "enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_offering_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dropped_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_enrollments_university_id_universities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_offering_id"],
            ["course_offerings.id"],
            name="fk_enrollments_course_offering_id_course_offerings",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_enrollments_student_id_students",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "course_offering_id",
            "student_id",
            name="uq_enrollments_offering_student",
        ),
    )
    op.create_index("ix_enrollments_id", "enrollments", ["id"], unique=False)
    op.create_index("ix_enrollments_university_id", "enrollments", ["university_id"], unique=False)
    op.create_index(
        "ix_enrollments_course_offering_id", "enrollments", ["course_offering_id"], unique=False
    )
    op.create_index("ix_enrollments_student_id", "enrollments", ["student_id"], unique=False)
    op.create_index("ix_enrollments_status", "enrollments", ["status"], unique=False)


def downgrade() -> None:
    """Revert migration dropping tables in reverse order."""
    op.drop_index("ix_enrollments_status", table_name="enrollments")
    op.drop_index("ix_enrollments_student_id", table_name="enrollments")
    op.drop_index("ix_enrollments_course_offering_id", table_name="enrollments")
    op.drop_index("ix_enrollments_university_id", table_name="enrollments")
    op.drop_index("ix_enrollments_id", table_name="enrollments")
    op.drop_table("enrollments")

    op.drop_index("uq_primary_lecturer_per_offering", table_name="lecturer_assignments")
    op.drop_index("ix_lecturer_assignments_lecturer_id", table_name="lecturer_assignments")
    op.drop_index("ix_lecturer_assignments_course_offering_id", table_name="lecturer_assignments")
    op.drop_index("ix_lecturer_assignments_id", table_name="lecturer_assignments")
    op.drop_table("lecturer_assignments")

    op.drop_index("uq_course_offerings_without_section", table_name="course_offerings")
    op.drop_index("uq_course_offerings_with_section", table_name="course_offerings")
    op.drop_index("ix_course_offerings_course_semester", table_name="course_offerings")
    op.drop_index("ix_course_offerings_academic_unit_id", table_name="course_offerings")
    op.drop_index("ix_course_offerings_section_id", table_name="course_offerings")
    op.drop_index("ix_course_offerings_semester_id", table_name="course_offerings")
    op.drop_index("ix_course_offerings_course_id", table_name="course_offerings")
    op.drop_index("ix_course_offerings_university_id", table_name="course_offerings")
    op.drop_index("ix_course_offerings_id", table_name="course_offerings")
    op.drop_table("course_offerings")

    op.drop_index("ix_lecturers_university_employee_code", table_name="lecturers")
    op.drop_index("ix_lecturers_academic_unit_id", table_name="lecturers")
    op.drop_index("ix_lecturers_university_id", table_name="lecturers")
    op.drop_index("ix_lecturers_user_id", table_name="lecturers")
    op.drop_index("ix_lecturers_id", table_name="lecturers")
    op.drop_table("lecturers")

    op.drop_index("ix_students_university_student_number", table_name="students")
    op.drop_index("ix_students_section_id", table_name="students")
    op.drop_index("ix_students_academic_unit_id", table_name="students")
    op.drop_index("ix_students_university_id", table_name="students")
    op.drop_index("ix_students_user_id", table_name="students")
    op.drop_index("ix_students_id", table_name="students")
    op.drop_table("students")

    op.drop_index("ix_sections_university_code", table_name="sections")
    op.drop_index("ix_sections_semester_id", table_name="sections")
    op.drop_index("ix_sections_academic_unit_id", table_name="sections")
    op.drop_index("ix_sections_university_id", table_name="sections")
    op.drop_index("ix_sections_id", table_name="sections")
    op.drop_table("sections")

    op.drop_index("ix_courses_university_code", table_name="courses")
    op.drop_index("ix_courses_academic_unit_id", table_name="courses")
    op.drop_index("ix_courses_university_id", table_name="courses")
    op.drop_index("ix_courses_id", table_name="courses")
    op.drop_table("courses")
