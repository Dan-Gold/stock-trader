"""Interface for backtest repository implementations."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.backtest_create_request import BacktestCreateRequest
from stock_trader.models.shared_enums import BacktestStatusEnum


class IBacktestRepoInterface(Protocol):
    """Interface for backtest repository implementations."""

    async def create_backtest_job(self, backtest_request: BacktestCreateRequest) -> BacktestJobTableSchema:
        """Create a new backtest job in the database.

        Args:
            backtest_request: The backtest request to create.

        Returns:
            The created backtest job record.
        """
        ...

    async def get_backtest_job(self, job_id: UUID) -> BacktestJobTableSchema:
        """Get a backtest job by its UUID.

        Args:
            job_id: The UUID of the backtest job.

        Returns:
            The backtest job record.
        """
        ...

    async def update_job_status(
        self,
        job_id: UUID,
        status: BacktestStatusEnum,
        error: str | None = None,
    ) -> BacktestJobTableSchema:
        """Update a backtest job's status.

        Args:
            job_id: The UUID of the backtest job.
            status: The new status.
            error: Optional error message (for FAILED status).

        Returns:
            The updated backtest job record.
        """
        ...

    async def list_backtest_jobs(
        self,
        status_filter: BacktestStatusEnum | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[BacktestJobTableSchema]:
        """List backtest jobs from database with pagination."""
        ...
