"""Base class for domain import processors."""

import abc
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.imports.schemas import ImportTemplateColumn
from backend.app.models.import_job import ImportRow


class BaseImportProcessor(abc.ABC):
    """Abstract base processor for validating and committing imported data rows."""

    @abc.abstractmethod
    def get_required_headers(self) -> list[str]:
        """Return list of required normalized header keys."""

    @abc.abstractmethod
    def get_template(self) -> list[ImportTemplateColumn]:
        """Return list of template columns describing expected fields."""

    @abc.abstractmethod
    def get_sample_csv(self) -> str:
        """Return sample CSV snippet."""

    @abc.abstractmethod
    async def validate_row(
        self,
        db: AsyncSession,
        university_id: uuid.UUID,
        row_number: int,
        raw_data: dict[str, Any],
        seen_keys: dict[str, Any],
    ) -> tuple[dict[str, Any], str, str, list[dict[str, Any]], list[dict[str, Any]]]:
        """Validate a single parsed row against university domain rules.

        Returns:
            tuple of:
            - normalized_data (dict[str, Any])
            - action (str: CREATE, UPDATE, NONE, SKIP)
            - status (str: VALID, WARNING, ERROR)
            - errors (list[dict[str, Any]])
            - warnings (list[dict[str, Any]])
        """

    @abc.abstractmethod
    async def commit_row(
        self,
        db: AsyncSession,
        university_id: uuid.UUID,
        staged_row: ImportRow,
        actor_user_id: uuid.UUID,
    ) -> tuple[uuid.UUID, str]:
        """Commit a single staged row into production domain tables.

        Returns:
            tuple of:
            - resolved_entity_id (uuid.UUID)
            - resolved_entity_type (str, e.g. 'Student', 'Lecturer', etc.)
        """
