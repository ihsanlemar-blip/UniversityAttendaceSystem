"""Unit tests for SQLAlchemy models, Base metadata, and database session dependency."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core.constants import DEFAULT_LOCALE, DEFAULT_TIMEZONE, RecordStatus
from backend.app.core.database import get_db_session
from backend.app.models.base import Base
from backend.app.models.university import University


def test_university_model_metadata() -> None:
    """Verify University model schema definition and constraints in Base.metadata."""
    assert "universities" in Base.metadata.tables
    table = Base.metadata.tables["universities"]

    column_names = {c.name for c in table.columns}
    expected_columns = {
        "id",
        "name",
        "code",
        "timezone",
        "default_language",
        "status",
        "created_at",
        "updated_at",
    }
    assert expected_columns.issubset(column_names)

    # Check primary key
    assert table.primary_key.columns.keys() == ["id"]

    # Check unique on code
    assert table.c.code.unique is True
    assert getattr(table.c.timezone.default, "arg", None) == DEFAULT_TIMEZONE
    assert getattr(table.c.default_language.default, "arg", None) == DEFAULT_LOCALE
    assert getattr(table.c.status.default, "arg", None) == RecordStatus.ACTIVE.value


def test_university_instance_instantiation() -> None:
    """Verify explicit instantiation of University entity attributes."""
    uni = University(
        name="Herat University",
        code="HU",
        timezone="Asia/Kabul",
        default_language="ps",
        status="ACTIVE",
    )
    assert uni.name == "Herat University"
    assert uni.code == "HU"
    assert uni.timezone == "Asia/Kabul"
    assert uni.default_language == "ps"
    assert uni.status == "ACTIVE"
    assert "Herat University" in repr(uni)


class MockSessionContext:
    """Async context manager wrapper around an AsyncMock session."""

    def __init__(self, session: AsyncMock) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncMock:
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


@pytest.mark.asyncio
async def test_get_db_session_lifecycle_success() -> None:
    """Verify get_db_session yields session and closes it on normal completion."""
    mock_session = AsyncMock()

    def mock_factory() -> MockSessionContext:
        return MockSessionContext(mock_session)

    with patch("backend.app.core.database.get_sessionmaker", return_value=mock_factory):
        gen = get_db_session()
        session = await anext(gen)
        assert session == mock_session
        with pytest.raises(StopAsyncIteration):
            await anext(gen)
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_session_lifecycle_rollback_on_error() -> None:
    """Verify get_db_session rolls back the transaction when an exception is raised."""
    mock_session = AsyncMock()

    def mock_factory() -> MockSessionContext:
        return MockSessionContext(mock_session)

    with patch("backend.app.core.database.get_sessionmaker", return_value=mock_factory):
        gen = get_db_session()
        session = await anext(gen)
        assert session == mock_session
        with pytest.raises(RuntimeError, match="Simulated endpoint failure"):
            try:
                raise RuntimeError("Simulated endpoint failure")
            except Exception as e:
                await gen.athrow(e)
        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()
