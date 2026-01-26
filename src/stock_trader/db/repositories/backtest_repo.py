"""Repository for backtesting-related database operations."""

from sqlalchemy.ext.asyncio import async_sessionmaker

from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.backtest_create_request import BacktestCreateRequest


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
