"""Digital Student Attendance System - Backend Modular Monolith Entrypoint.

Milestone 4: Core Platform Foundation.
Establishes production configuration, async database pool lifecycle,
Redis client, correlation IDs, structured logging, and standard error handling.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_v1_router
from backend.app.core.config import get_settings
from backend.app.core.database import close_database_connections
from backend.app.core.logging import get_logger, setup_logging
from backend.app.core.middleware import RequestIdMiddleware, register_exception_handlers
from backend.app.core.redis import close_redis, init_redis
from backend.app.health.router import health_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management for connection pools and resources."""
    settings = get_settings()

    # 1. Initialize structured logging
    setup_logging(
        level=settings.LOG_LEVEL,
        json_format=(settings.LOG_FORMAT == "json"),
        env=settings.APP_ENV.value,
    )
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV.value}]")

    # 2. Initialize Redis connection pool
    try:
        await init_redis()
        logger.info("Redis connection initialized successfully.")
    except Exception as exc:
        logger.warning(f"Could not connect to Redis on startup: {exc}")

    yield

    # 3. Graceful resource cleanup
    logger.info("Shutting down application resources...")
    await close_redis()
    await close_database_connections()
    logger.info("Shutdown complete.")


def create_application() -> FastAPI:
    """Application factory building and configuring the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title="Digital Student Attendance System API",
        description=(
            "Campus-local, offline-resilient university student attendance platform. "
            "Server-authoritative presence verification and academic governance."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # 1. Correlation Request ID Middleware
    app.add_middleware(RequestIdMiddleware)

    # 2. CORS Middleware (Environment Configurable)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 3. Standard Exception Envelopes
    register_exception_handlers(app)

    # 4. Mount Health Check Probes
    app.include_router(health_router)

    # 5. Mount Versioned API Routes
    app.include_router(api_v1_router)

    return app


app = create_application()
