"""Unit and security tests for safe CSV and XLSX import file parsers."""

import io

import openpyxl  # type: ignore[import-untyped]
import pytest

from backend.app.core.exceptions import ValidationException
from backend.app.imports.parser import (
    normalize_cell_value,
    normalize_header,
    parse_import_file,
)


def test_header_normalization() -> None:
    """Verify headers are reliably transformed to snake_case."""
    assert normalize_header("Student ID") == "student_id"
    assert normalize_header("First-Name") == "first_name"
    assert normalize_header("  Course Code  ") == "course_code"
    assert normalize_header("SEMESTER.CODE") == "semester_code"
    assert normalize_header("Weekday (1-7)") == "weekday_1_7"


def test_cell_value_normalization_unicode() -> None:
    """Verify NFKC normalization preserves Pashto, Dari, and trims whitespace."""
    # Pashto letters
    assert normalize_cell_value("  احمد  ") == "احمد"
    assert normalize_cell_value("ځوان") == "ځوان"
    assert normalize_cell_value("  پوهنتون  ") == "پوهنتون"

    # Dari letters
    assert normalize_cell_value("  دانشگاه  ") == "دانشگاه"
    assert normalize_cell_value("  ") is None
    assert normalize_cell_value(None) is None
    assert normalize_cell_value(123.0) == 123


def test_csv_utf8_bom_parsing() -> None:
    """Verify CSV with UTF-8 BOM is properly decoded without mangling the first header."""
    csv_text = "\ufeffstudent_number,first_name,last_name\nCS-001,احمد,محمدی\n"
    content = csv_text.encode("utf-8")

    parsed = parse_import_file(
        filename="students.csv",
        content=content,
        max_bytes=10000,
        max_rows=100,
    )

    assert parsed.headers == ["student_number", "first_name", "last_name"]
    assert len(parsed.rows) == 1
    assert parsed.rows[0].raw_data["student_number"] == "CS-001"
    assert parsed.rows[0].raw_data["first_name"] == "احمد"
    assert parsed.rows[0].raw_data["last_name"] == "محمدی"


def test_xlsx_parsing_and_formula_safety() -> None:
    """Verify XLSX files are safely parsed without formula execution."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "DataSheet"
    ws.append(["code", "name", "credit_hours"])
    ws.append(["CS-101", "Programming", 3])
    ws.append(["CS-102", "=SUM(A1:A5)", 4])  # Formula injection attempt

    bio = io.BytesIO()
    wb.save(bio)
    xlsx_bytes = bio.getvalue()

    parsed = parse_import_file(
        filename="courses.xlsx",
        content=xlsx_bytes,
        max_bytes=100000,
        max_rows=100,
    )

    assert parsed.headers == ["code", "name", "credit_hours"]
    assert len(parsed.rows) == 2
    assert parsed.rows[0].raw_data["code"] == "CS-101"
    assert parsed.rows[0].raw_data["credit_hours"] == 3
    # data_only=True ensures formula string or cached value is read, zero execution
    assert parsed.sheet_names == ["DataSheet"]


def test_file_size_limit_rejection() -> None:
    """Verify files exceeding max_bytes are rejected."""
    content = b"a" * 50
    with pytest.raises(ValidationException) as exc_info:
        parse_import_file(
            filename="large.csv",
            content=content,
            max_bytes=20,
            max_rows=100,
        )
    assert "exceeds maximum allowed limit" in str(exc_info.value.message)


def test_row_limit_rejection() -> None:
    """Verify files exceeding max_rows are rejected."""
    lines = ["student_number,first_name,last_name"]
    for i in range(15):
        lines.append(f"CS-{i},Name{i},Last{i}")
    content = "\n".join(lines).encode("utf-8")

    with pytest.raises(ValidationException) as exc_info:
        parse_import_file(
            filename="too_many_rows.csv",
            content=content,
            max_bytes=10000,
            max_rows=10,
        )
    assert "more than the maximum permitted 10 data rows" in str(exc_info.value.message)


def test_unsupported_file_extension() -> None:
    """Verify unsupported file extensions are rejected."""
    with pytest.raises(ValidationException) as exc_info:
        parse_import_file(
            filename="data.pdf",
            content=b"%PDF-1.4...",
            max_bytes=10000,
            max_rows=100,
        )
    assert "Unsupported file format" in str(exc_info.value.message)


def test_empty_file_rejection() -> None:
    """Verify empty files (0 bytes) are rejected."""
    with pytest.raises(ValidationException) as exc_info:
        parse_import_file(
            filename="empty.csv",
            content=b"",
            max_bytes=10000,
            max_rows=100,
        )
    assert "empty (0 bytes)" in str(exc_info.value.message)
