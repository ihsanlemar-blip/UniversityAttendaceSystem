"""Domain import processors package."""

from backend.app.core.constants import ImportType
from backend.app.core.exceptions import ValidationException
from backend.app.imports.processors.base import BaseImportProcessor
from backend.app.imports.processors.course_offerings import CourseOfferingImportProcessor
from backend.app.imports.processors.courses import CourseImportProcessor
from backend.app.imports.processors.enrollments import EnrollmentImportProcessor
from backend.app.imports.processors.lecturers import LecturerImportProcessor
from backend.app.imports.processors.students import StudentImportProcessor
from backend.app.imports.processors.timetables import TimetableImportProcessor

PROCESSOR_REGISTRY: dict[ImportType, type[BaseImportProcessor]] = {
    ImportType.STUDENTS: StudentImportProcessor,
    ImportType.LECTURERS: LecturerImportProcessor,
    ImportType.COURSES: CourseImportProcessor,
    ImportType.COURSE_OFFERINGS: CourseOfferingImportProcessor,
    ImportType.ENROLLMENTS: EnrollmentImportProcessor,
    ImportType.TIMETABLES: TimetableImportProcessor,
}


def get_processor(import_type: ImportType | str) -> BaseImportProcessor:
    """Retrieve an instantiated processor for the given import type."""
    if isinstance(import_type, str):
        try:
            import_type = ImportType(import_type.upper())
        except ValueError as err:
            raise ValidationException(
                f"Unknown import type: '{import_type}'.",
                details={"supported_types": [t.value for t in ImportType]},
            ) from err

    proc_cls = PROCESSOR_REGISTRY.get(import_type)
    if not proc_cls:
        raise ValidationException(
            f"No processor registered for import type: '{import_type.value}'.",
            details={"supported_types": [t.value for t in ImportType]},
        )
    return proc_cls()


__all__ = [
    "BaseImportProcessor",
    "CourseImportProcessor",
    "CourseOfferingImportProcessor",
    "EnrollmentImportProcessor",
    "LecturerImportProcessor",
    "StudentImportProcessor",
    "TimetableImportProcessor",
    "get_processor",
]
