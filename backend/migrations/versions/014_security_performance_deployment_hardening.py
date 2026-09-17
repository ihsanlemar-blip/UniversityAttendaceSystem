"""Performance and query optimization composite indexes.

Revision ID: 014_perf_hardening
Revises: 013_imports_administration
Create Date: 2026-09-17 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# Revision identifiers (<= 32 chars for alembic_version)
revision: str = "014_perf_hardening"
down_revision: str | None = "013_imports_administration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create composite performance indexes for high-throughput queries."""
    # 1. Lecturer schedule & dashboard query optimization
    op.create_index(
        "ix_class_occurrences_lecturer_date_status",
        "class_occurrences",
        ["lecturer_id", "local_date", "status"],
        unique=False,
    )

    # 2. Daily university schedule & background session activation
    op.create_index(
        "ix_class_occurrences_uni_status_start",
        "class_occurrences",
        ["university_id", "status", "scheduled_start_utc"],
        unique=False,
    )

    # 3. Student timeline and historical attendance outcome aggregation
    op.create_index(
        "ix_attendance_records_student_created",
        "attendance_records",
        ["student_id", "created_at"],
        unique=False,
    )

    # 4. Checkpoint evidence lookup by source mode (QR, BLE, WiFi, Manual)
    op.create_index(
        "ix_attendance_evidence_checkpoint_source",
        "attendance_evidence",
        ["attendance_checkpoint_id", "source_mode"],
        unique=False,
    )

    # 5. Student active enrollment lookups
    op.create_index(
        "ix_enrollments_student_status",
        "enrollments",
        ["student_id", "status"],
        unique=False,
    )

    # 6. Semester offering catalog queries
    op.create_index(
        "ix_course_offerings_semester_status",
        "course_offerings",
        ["semester_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop composite performance indexes."""
    op.drop_index("ix_course_offerings_semester_status", table_name="course_offerings")
    op.drop_index("ix_enrollments_student_status", table_name="enrollments")
    op.drop_index("ix_attendance_evidence_checkpoint_source", table_name="attendance_evidence")
    op.drop_index("ix_attendance_records_student_created", table_name="attendance_records")
    op.drop_index("ix_class_occurrences_uni_status_start", table_name="class_occurrences")
    op.drop_index("ix_class_occurrences_lecturer_date_status", table_name="class_occurrences")
