"""Interface for worker repository."""

from typing import Protocol
from uuid import UUID

from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.shared_enums import BacktestStatusEnum


class IBacktestRepositorySync(Protocol):
    """Sync repository for Celery worker database access."""

    def save_job_result(self, job_id: UUID, symbol: str, summary: dict, raw: dict) -> None:
        """Create and save the result data of a completed backtest job.

        Args:
            job_id: The UUID of the backtest job.
            symbol: The stock ticker symbol.
            summary: The summary data to store.
            raw: The raw data to store.
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
