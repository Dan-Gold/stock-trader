"""Interface for backtest repository implementations."""

from asyncio import Protocol


class IBacktestRepoInterface(Protocol):
    """Interface for backtest repository implementations."""

    async def create_backtest_job(self, backtest_request) -> object:
        """Create a new backtest job in the database.

        Args:
            backtest_request: The backtest request to create.

        Returns:
            The created backtest job record.
        """
        ...

    async def get_backtest_job(self, job_id: str) -> object:
        """Get a backtest job by its UUID.

        Args:
            job_id: The UUID of the backtest job.

        Returns:
            The backtest job record.
        """
        ...

    async def list_backtest_jobs(self) -> list[object]:
        """List all backtest jobs.

        Returns:
            A list of backtest job records.
        """
        ...
