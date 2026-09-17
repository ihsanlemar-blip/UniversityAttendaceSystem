"""Safe spreadsheet export service with CSV formula injection defense and XLSX generation."""

import csv
import io
from typing import Any

import openpyxl  # type: ignore[import-untyped]
from openpyxl.styles import Alignment, Font, PatternFill  # type: ignore[import-untyped]
from openpyxl.utils import get_column_letter  # type: ignore[import-untyped]

DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_cell_value(val: Any) -> Any:
    """Neutralize spreadsheet formula injection on cell values.

    If a string value begins with dangerous spreadsheet execution prefixes
    ('=', '+', '-', '@', '\t', '\r'), prepend a single quote to force spreadsheet
    applications to evaluate it strictly as literal text.
    """
    if val is None:
        return ""
    if isinstance(val, (int, float, bool)):
        return val

    s = str(val)
    if s.startswith(DANGEROUS_FORMULA_PREFIXES):
        # Escape by prepending a single quote
        return f"'{s}"
    return s


class ExportService:
    """Provides secure, audited CSV and XLSX exports for attendance reports."""

    @staticmethod
    def export_course_roster_csv(
        report: dict[str, Any],
    ) -> bytes:
        """Generate UTF-8 BOM encoded CSV for course roster attendance report."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header metadata rows
        writer.writerow(["Course Attendance Roster Report"])
        writer.writerow(["Course Code", sanitize_cell_value(report.get("course_code"))])
        writer.writerow(["Course Name", sanitize_cell_value(report.get("course_name"))])
        writer.writerow(["Semester", sanitize_cell_value(report.get("semester_code"))])
        writer.writerow(["Section", sanitize_cell_value(report.get("section_code") or "All")])
        writer.writerow(["Total Sessions", report.get("total_sessions_conducted", 0)])
        avg_pct = f"{report.get('average_attendance_percentage', 0.0):.1f}%"
        writer.writerow(["Average Attendance %", avg_pct])
        writer.writerow(["Threshold %", f"{report.get('threshold_percentage', 75.0):.1f}%"])
        writer.writerow(["Generated At (UTC)", str(report.get("generated_at_utc", ""))])
        writer.writerow([])  # blank row

        # Data table header
        columns = [
            "Student Number",
            "Student Name",
            "Eligible Sessions",
            "Attended Credit",
            "Attendance %",
            "Present",
            "Late",
            "Absent",
            "Excused",
            "Leave",
            "Has Revision",
            "Threshold Status",
        ]
        writer.writerow(columns)

        for item in report.get("roster", []):
            writer.writerow(
                [
                    sanitize_cell_value(item.get("student_number")),
                    sanitize_cell_value(item.get("student_name")),
                    item.get("eligible_sessions", 0),
                    f"{item.get('attendance_credit', 0.0):.2f}",
                    f"{item.get('attendance_percentage', 0.0):.1f}%",
                    item.get("present_count", 0),
                    item.get("late_count", 0),
                    item.get("absent_count", 0),
                    item.get("excused_count", 0),
                    item.get("leave_count", 0),
                    "YES" if item.get("has_revision") else "NO",
                    item.get("threshold_status", ""),
                ]
            )

        # Encode with UTF-8 BOM for Excel compatibility with Dari/Pashto
        return "\ufeff".encode("utf-8") + output.getvalue().encode("utf-8")

    @staticmethod
    def export_course_roster_xlsx(
        report: dict[str, Any],
    ) -> bytes:
        """Generate structured, macro-free XLSX workbook for course roster report."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Course Roster Report"

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        title_font = Font(name="Calibri", size=14, bold=True)

        ws.append(["Course Attendance Roster Report"])
        ws["A1"].font = title_font

        ws.append(["Course Code", sanitize_cell_value(report.get("course_code"))])
        ws.append(["Course Name", sanitize_cell_value(report.get("course_name"))])
        ws.append(["Semester", sanitize_cell_value(report.get("semester_code"))])
        ws.append(["Total Sessions", report.get("total_sessions_conducted", 0)])
        avg_pct = f"{report.get('average_attendance_percentage', 0.0):.1f}%"
        ws.append(["Average Attendance", avg_pct])
        ws.append(["Threshold %", f"{report.get('threshold_percentage', 75.0):.1f}%"])
        ws.append([])

        headers = [
            "Student Number",
            "Student Name",
            "Eligible Sessions",
            "Attended Credit",
            "Attendance %",
            "Present",
            "Late",
            "Absent",
            "Excused",
            "Leave",
            "Has Revision",
            "Threshold Status",
        ]
        ws.append(headers)
        header_row_idx = ws.max_row
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=header_row_idx, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for item in report.get("roster", []):
            ws.append(
                [
                    sanitize_cell_value(item.get("student_number")),
                    sanitize_cell_value(item.get("student_name")),
                    item.get("eligible_sessions", 0),
                    item.get("attendance_credit", 0.0),
                    f"{item.get('attendance_percentage', 0.0):.1f}%",
                    item.get("present_count", 0),
                    item.get("late_count", 0),
                    item.get("absent_count", 0),
                    item.get("excused_count", 0),
                    item.get("leave_count", 0),
                    "YES" if item.get("has_revision") else "NO",
                    item.get("threshold_status", ""),
                ]
            )

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def export_session_report_csv(
        report: dict[str, Any],
    ) -> bytes:
        """Generate UTF-8 BOM CSV for single session operational report."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow(["Attendance Session Operational Report"])
        writer.writerow(["Session ID", report.get("session_id")])
        writer.writerow(["Course", f"{report.get('course_code')} - {report.get('course_name')}"])
        writer.writerow(["Semester", report.get("semester_code")])
        writer.writerow(["Section", report.get("section_code") or "None"])
        lec_str = f"{report.get('lecturer_code')} - {report.get('lecturer_name')}"
        writer.writerow(["Lecturer", lec_str])
        b_code = report.get("building_code") or ""
        r_num = report.get("room_number") or ""
        writer.writerow(["Room", f"{b_code} {r_num}".strip()])
        writer.writerow(["Session Status", report.get("status")])
        writer.writerow(["Opened At (UTC)", str(report.get("opened_at_utc", ""))])
        writer.writerow(["Closed At (UTC)", str(report.get("closed_at_utc", ""))])
        writer.writerow([])

        writer.writerow(["Metric", "Count"])
        writer.writerow(["Roster Total", report.get("roster_count", 0)])
        writer.writerow(["Start Checkpoint Credited", report.get("start_credited_count", 0)])
        writer.writerow(["Middle Checkpoint Credited", report.get("middle_credited_count", 0)])
        writer.writerow(["End Checkpoint Credited", report.get("end_credited_count", 0)])
        writer.writerow(["Present Count", report.get("present_count", 0)])
        writer.writerow(["Late Count", report.get("late_count", 0)])
        writer.writerow(["Absent Count", report.get("absent_count", 0)])
        writer.writerow(["Excused Count", report.get("excused_count", 0)])
        writer.writerow(["Leave Count", report.get("leave_count", 0)])
        writer.writerow(["Manual Overrides", report.get("manual_count", 0)])
        writer.writerow(["Offline Created", report.get("offline_count", 0)])
        writer.writerow(["Revisions", report.get("revision_count", 0)])

        return "\ufeff".encode("utf-8") + output.getvalue().encode("utf-8")

    @staticmethod
    def export_session_report_xlsx(
        report: dict[str, Any],
    ) -> bytes:
        """Generate XLSX workbook for session report."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Session Report"

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")

        ws.append(["Attendance Session Operational Report"])
        ws["A1"].font = Font(name="Calibri", size=14, bold=True)
        ws.append(["Course", f"{report.get('course_code')} - {report.get('course_name')}"])
        ws.append(["Lecturer", f"{report.get('lecturer_code')} - {report.get('lecturer_name')}"])
        ws.append(["Status", report.get("status")])
        ws.append([])

        ws.append(["Operational Metric", "Result"])
        ws.cell(row=5, column=1).font = header_font
        ws.cell(row=5, column=1).fill = header_fill
        ws.cell(row=5, column=2).font = header_font
        ws.cell(row=5, column=2).fill = header_fill

        metrics = [
            ("Roster Total", report.get("roster_count", 0)),
            ("Start Checkpoint Credited", report.get("start_credited_count", 0)),
            ("Middle Checkpoint Credited", report.get("middle_credited_count", 0)),
            ("End Checkpoint Credited", report.get("end_credited_count", 0)),
            ("Present", report.get("present_count", 0)),
            ("Late", report.get("late_count", 0)),
            ("Absent", report.get("absent_count", 0)),
            ("Excused", report.get("excused_count", 0)),
            ("Leave", report.get("leave_count", 0)),
            ("Manual Overrides", report.get("manual_count", 0)),
            ("Offline Created", report.get("offline_count", 0)),
            ("Revisions", report.get("revision_count", 0)),
        ]
        for name, val in metrics:
            ws.append([name, val])

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def export_department_report_csv(
        report: dict[str, Any],
    ) -> bytes:
        """Generate UTF-8 BOM CSV for departmental aggregate report."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow(["Department Attendance Aggregate Report"])
        writer.writerow(["Department Code", report.get("academic_unit_code")])
        writer.writerow(["Department Name", sanitize_cell_value(report.get("academic_unit_name"))])
        writer.writerow(["Total Offerings", report.get("total_offerings", 0)])
        writer.writerow(["Total Enrolled Students", report.get("total_students_enrolled", 0)])
        dept_avg = f"{report.get('department_average_percentage', 0.0):.1f}%"
        writer.writerow(["Department Average %", dept_avg])
        writer.writerow(["Below Threshold Count", report.get("below_threshold_count", 0)])
        writer.writerow(["Near Threshold Count", report.get("near_threshold_count", 0)])
        writer.writerow(["Above Threshold Count", report.get("above_threshold_count", 0)])
        writer.writerow([])

        writer.writerow(
            [
                "Course Code",
                "Course Name",
                "Semester",
                "Section",
                "Enrolled Count",
                "Conducted Sessions",
                "Average Attendance %",
                "Below Threshold Count",
                "Near Threshold Count",
            ]
        )
        for off in report.get("offerings", []):
            writer.writerow(
                [
                    sanitize_cell_value(off.get("course_code")),
                    sanitize_cell_value(off.get("course_name")),
                    sanitize_cell_value(off.get("semester_code")),
                    sanitize_cell_value(off.get("section_code") or "None"),
                    off.get("enrolled_count", 0),
                    off.get("conducted_sessions_count", 0),
                    f"{off.get('average_attendance_percentage', 0.0):.1f}%",
                    off.get("below_threshold_count", 0),
                    off.get("near_threshold_count", 0),
                ]
            )

        return "\ufeff".encode("utf-8") + output.getvalue().encode("utf-8")

    @staticmethod
    def export_department_report_xlsx(
        report: dict[str, Any],
    ) -> bytes:
        """Generate XLSX workbook for departmental aggregate report."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Department Aggregate"

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")

        ws.append(["Department Attendance Aggregate Report"])
        ws["A1"].font = Font(name="Calibri", size=14, bold=True)
        dept_lbl = f"{report.get('academic_unit_code')} - {report.get('academic_unit_name')}"
        ws.append(["Department", dept_lbl])
        ws.append(["Average %", f"{report.get('department_average_percentage', 0.0):.1f}%"])
        ws.append([])

        headers = [
            "Course Code",
            "Course Name",
            "Semester",
            "Section",
            "Enrolled Count",
            "Conducted Sessions",
            "Average Attendance %",
            "Below Threshold Count",
            "Near Threshold Count",
        ]
        ws.append(headers)
        h_row = ws.max_row
        for i in range(1, len(headers) + 1):
            c = ws.cell(row=h_row, column=i)
            c.font = header_font
            c.fill = header_fill

        for off in report.get("offerings", []):
            ws.append(
                [
                    sanitize_cell_value(off.get("course_code")),
                    sanitize_cell_value(off.get("course_name")),
                    sanitize_cell_value(off.get("semester_code")),
                    sanitize_cell_value(off.get("section_code") or "None"),
                    off.get("enrolled_count", 0),
                    off.get("conducted_sessions_count", 0),
                    f"{off.get('average_attendance_percentage', 0.0):.1f}%",
                    off.get("below_threshold_count", 0),
                    off.get("near_threshold_count", 0),
                ]
            )

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()
