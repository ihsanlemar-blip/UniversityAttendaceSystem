"""Health check probe module."""

from backend.app.health.router import router as health_router

__all__ = ["health_router"]
