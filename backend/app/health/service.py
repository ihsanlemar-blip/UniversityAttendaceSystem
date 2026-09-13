"""Health service evaluating backing infrastructure readiness."""

from backend.app.core.database import check_db_connectivity
from backend.app.core.redis import check_redis_connectivity


class HealthService:
    """Evaluates readiness of backing services without leaking sensitive details."""

    @staticmethod
    async def evaluate_readiness() -> tuple[bool, dict[str, str]]:
        """Check database and Redis availability.

        Returns:
            (is_ready, dependency_status_dict)
        """
        db_ok = await check_db_connectivity()
        redis_ok = await check_redis_connectivity()

        dependencies = {
            "database": "healthy" if db_ok else "unreachable",
            "redis": "healthy" if redis_ok else "unreachable",
        }

        all_ready = db_ok and redis_ok
        return all_ready, dependencies
