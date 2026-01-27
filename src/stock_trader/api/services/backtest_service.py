"""Service layer for backtest operations."""

from uuid import UUID

from stock_trader.db.interfaces.backtest_repo_interface import IBacktestRepoInterface
from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.backtest_create_request import BacktestCreateRequest
from stock_trader.models.shared_enums import BacktestStatusEnum


class BacktestService:
    """Service layer for backtest operations."""

    def __init__(self, backtest_repository: IBacktestRepoInterface):
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
        # TODO: Then add the job to the Redis queue for processing
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

    async def list_backtest_jobs(
        self,
        status_filter: BacktestStatusEnum | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[BacktestJobTableSchema]:
        """List backtest jobs with optional filtering and pagination."""
        return await self.backtest_repository.list_backtest_jobs(
            status_filter=status_filter,
            offset=offset,
            limit=limit,
        )
