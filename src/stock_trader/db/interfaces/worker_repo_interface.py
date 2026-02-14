"""Interface for worker repository."""

from typing import Protocol
from uuid import UUID

from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.shared_enums import BacktestStatusEnum


class IBacktestRepositorySync(Protocol):
    """Sync repository for Celery worker database access."""

    def post_job_result(self, job_id: UUID, metric_data: dict, result_data: dict) -> None:
        """Create the result data of a completed backtest job.

        Args:
            job_id: The UUID of the backtest job.
            metric_data: The metric data to store.
            result_data: The result data to store.
        """
        ...

    def get_backtest_job(self, job_id: UUID) -> BacktestJobTableSchema:
        """Get a backtest job by its UUID."""
        ...

    def update_job_status(
        self,
        job_id: UUID,
        status: BacktestStatusEnum,
        error: str | None = None,
    ) -> None:
        """Update a backtest job's status."""
        ...
