"""RBAC package exporting service, dependencies, and router."""

from backend.app.rbac.dependencies import require_permission
from backend.app.rbac.router import router
from backend.app.rbac.seeding import seed_system_rbac
from backend.app.rbac.service import RbacService

__all__ = [
    "RbacService",
    "require_permission",
    "router",
    "seed_system_rbac",
]
