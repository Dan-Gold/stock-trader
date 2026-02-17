"""Service layer for backtest operations."""

from typing import Sequence
from uuid import UUID

from celery import chain, chord

from stock_trader.core.backtest import finalize_backtest_job, run_backtest
from stock_trader.core.market_data.fetch_market_data import fetch_market_data
from stock_trader.db.interfaces.backtest_repo_interface import IBacktestRepoInterface
from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.backtest_create_request import BacktestCreateRequest
from stock_trader.models.shared_enums import BacktestStatusEnum


class BacktestService:
    """Service layer for backtest operations."""

    def __init__(self, backtest_repository: IBacktestRepoInterface) -> None:
        """Initialize the BacktestService."""
        self.backtest_repository = backtest_repository

    async def create_backtest_job(self, backtest_request: BacktestCreateRequest) -> BacktestJobTableSchema:
        """Create a new backtest job.

        Args:
            backtest_request: The backtest request to create.

        Returns:
            The created backtest job record.
        """
        job = await self.backtest_repository.create_backtest_job(backtest_request=backtest_request)
        return job

    async def get_backtest_job(self, job_id: UUID) -> BacktestJobTableSchema:
        """Get a backtest job by its UUID.

        Args:
            job_id: The UUID of the backtest job.

        Returns:
            The backtest job record.

        Raises:
            NotImplementedError: This method is not yet implemented.
        """
        return await self.backtest_repository.get_backtest_job(job_id=job_id)

    async def dispatch_backtest_job(self, job_id: UUID) -> None:
        """Dispatch a backtest job to celery for processing.

        Creates one Celery task per symbol in the backtest job. A chord callback runs after
        all of the symbol tasks are complete to update the parent job status.

        Args:
            job_id: The UUID of the backtest job to dispatch.
        """
        job = await self.backtest_repository.get_backtest_job(job_id=job_id)

        # Update job status to running
        await self.backtest_repository.update_job_status(
            job_id=job_id,
            status=BacktestStatusEnum.RUNNING,
        )

        # Chain: fetch market data → chord of backtest tasks per symbol
        task_group = [run_backtest.s(str(job_id), symbol) for symbol in job.symbols]
        callback = finalize_backtest_job.s(str(job_id))

        chain(
            fetch_market_data.s(str(job_id)),
            chord(task_group, callback),
        ).apply_async()

    async def list_backtest_jobs(
        self,
        status_filter: BacktestStatusEnum | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[BacktestJobTableSchema]:
        """List backtest jobs with optional filtering and pagination."""
        return await self.backtest_repository.list_backtest_jobs(
            status_filter=status_filter,
            offset=offset,
            limit=limit,
        )
