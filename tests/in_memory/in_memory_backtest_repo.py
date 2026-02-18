"""In-memory implementation of IBacktestRepoInterface for unit tests."""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID, uuid4

from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.backtest_create_request import BacktestCreateRequest
from stock_trader.models.exceptions import JobNotFoundError
from stock_trader.models.shared_enums import BacktestStatusEnum


class MemoryBacktestRepository:
    """In-memory implementation of IBacktestRepoInterface for unit tests."""

    def __init__(self) -> None:
        self.jobs: dict[UUID, BacktestJobTableSchema] = {}

    async def create_backtest_job(
        self,
        backtest_request: BacktestCreateRequest,
    ) -> BacktestJobTableSchema:
        """Create a new backtest job in memory."""
        job = BacktestJobTableSchema(
            uuid=uuid4(),
            status=BacktestStatusEnum.CREATED,
            strategy_name=backtest_request.strategy_name,
            symbols=backtest_request.symbols,
            parameters=backtest_request.parameters,
            start_date=backtest_request.start_date,
            end_date=backtest_request.end_date,
            create_time=datetime.now(timezone.utc),
        )
        self.jobs[job.uuid] = job
        return job

    async def get_backtest_job(self, job_id: UUID) -> BacktestJobTableSchema:
        """Retrieve a backtest job by its ID."""
        if job_id not in self.jobs:
            raise JobNotFoundError(f"Job {job_id} not found")
        return self.jobs[job_id]

    async def update_job_status(
        self,
        job_id: UUID,
        status: BacktestStatusEnum,
        error: str | None = None,
    ) -> BacktestJobTableSchema:
        """Update the status of a backtest job."""
        job = await self.get_backtest_job(job_id)
        job.status = status
        job.error = error
        return job

    async def list_backtest_jobs(
        self,
        status_filter: BacktestStatusEnum | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[BacktestJobTableSchema]:
        """List backtest jobs with optional status filtering and pagination."""
        jobs = list(self.jobs.values())

        if status_filter is not None:
            jobs = [j for j in jobs if j.status == status_filter]

        # Newest first (matches real repo ordering)
        jobs.sort(key=lambda j: j.create_time, reverse=True)
        return jobs[offset : offset + limit]
