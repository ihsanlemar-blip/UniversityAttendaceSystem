"""Models package exporting declarative Base and entities."""

from backend.app.models.academic_unit import AcademicUnit
from backend.app.models.academic_year import AcademicYear
from backend.app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from backend.app.models.login_attempt import LoginAttempt
from backend.app.models.permission import Permission
from backend.app.models.refresh_session import RefreshSession
from backend.app.models.role import Role
from backend.app.models.role_assignment import RoleAssignment
from backend.app.models.role_permission import RolePermission
from backend.app.models.semester import Semester
from backend.app.models.university import University
from backend.app.models.user import User

__all__ = [
    "AcademicUnit",
    "AcademicYear",
    "Base",
    "LoginAttempt",
    "Permission",
    "RefreshSession",
    "Role",
    "RoleAssignment",
    "RolePermission",
    "Semester",
    "TimestampMixin",
    "UUIDv7PrimaryKeyMixin",
    "University",
    "User",
]
