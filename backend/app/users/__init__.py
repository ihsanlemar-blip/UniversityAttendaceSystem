"""Users package exporting service and router."""

from backend.app.users.router import router
from backend.app.users.service import UserService

__all__ = ["UserService", "router"]
