"""Digital Student Attendance System - Backend API Entrypoint.

Milestone 3: Minimal application bootstrap skeleton exposing system health probes.
Business functionality, database models, and attendance routes are deferred
to subsequent milestones.
"""

from typing import Any, Dict
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Digital Student Attendance System API",
    description="Campus-local, offline-resilient university student attendance platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)

# Configure Cross-Origin Resource Sharing (CORS) for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health/live", status_code=status.HTTP_200_OK, tags=["Health"])
async def liveness_probe() -> Dict[str, Any]:
    """Liveness probe indicating the backend application process is running."""
    return {
        "status": "alive",
        "service": "backend",
        "version": "0.1.0",
    }


@app.get("/health/ready", status_code=status.HTTP_200_OK, tags=["Health"])
async def readiness_probe() -> Dict[str, Any]:
    """Readiness probe verifying the service is ready to accept incoming traffic."""
    return {
        "status": "ready",
        "service": "backend",
        "version": "0.1.0",
        "components": {
            "api": "ok",
        },
    }
