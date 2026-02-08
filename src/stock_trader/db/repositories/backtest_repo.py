"""Repository for backtesting-related database operations."""

from collections.abc import Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.backtest_create_request import BacktestCreateRequest
from stock_trader.models.exceptions import JobNotFoundError
from stock_trader.models.shared_enums import BacktestStatusEnum

# TODO: Implement domain model to convert DB models to?


class BacktestRepository:
    """Repository for backtesting-related database operations."""

    def __init__(self, session_maker: async_sessionmaker) -> None:
        self.database_session = session_maker

    async def create_backtest_job(self, backtest_request: BacktestCreateRequest) -> BacktestJobTableSchema:
        """Create a new backtest job in the database.

        Args:
            backtest_request: The backtest request to create.

        Returns:
            The created backtest job record.
        """
        async with self.database_session() as session:
            backtest_db = BacktestJobTableSchema.from_request(backtest_request=backtest_request)
            session.add(backtest_db)
            await session.commit()
            await session.refresh(backtest_db)
            return backtest_db

    async def get_backtest_job(self, job_id: UUID) -> BacktestJobTableSchema:
        """Get a backtest job by its UUID.

        Args:
            job_id: The UUID of the backtest job.

        Returns:
            The backtest job record.
        """
        async with self.database_session() as session:
            job_query = await session.execute(select(BacktestJobTableSchema).where(BacktestJobTableSchema.uuid == job_id))

            result = job_query.scalar_one_or_none()

        if not result:
            raise JobNotFoundError(f"Backtest job with ID {job_id} not found")

        return cast(BacktestJobTableSchema, result)

    async def list_backtest_jobs(
        self,
        status_filter: BacktestStatusEnum | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[BacktestJobTableSchema]:
        """List backtest jobs from database with pagination."""
        async with self.database_session() as session:
            query = select(BacktestJobTableSchema)

            if status_filter:
                query = query.where(BacktestJobTableSchema.status == status_filter)

            query = query.offset(offset).limit(limit)
            result = await session.execute(query)

        return result.scalars().all()
