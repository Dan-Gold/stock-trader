"""Service layer for backtest operations."""

from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.db.repositories.backtest_repo import BacktestRepository
from stock_trader.models.backtest_create_request import BacktestCreateRequest


class BacktestService:
    """Service layer for backtest operations."""

    def __init__(self, backtest_repository: BacktestRepository):
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
