"""Async SQLAlchemy 2.0 engine, sessionmaker, and transaction conventions."""

from collections.abc import AsyncGenerator

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = get_logger(__name__)

# Global engine and sessionmaker singletons
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return or initialize the async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.async_database_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return or initialize the async sessionmaker."""
    global _sessionmaker
    if _sessionmaker is None:
        engine = get_engine()
        _sessionmaker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI request-scoped database session dependency.

    Enforces explicit transaction lifecycle:
    - One session per request
    - Automatically rolls back on unhandled error
    - Closes session cleanly in finally block
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_database_connections() -> None:
    """Dispose of the engine connection pool gracefully on shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        logger.info("Disposing PostgreSQL connection pool...")
        await _engine.dispose()
        _engine = None
        _sessionmaker = None


async def check_db_connectivity() -> bool:
    """Execute a lightweight SELECT 1 to verify database reachability."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning(f"Database readiness check failed: {exc}")
        return False
