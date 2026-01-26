"""Dependencies for backtest service and repository."""

from stock_trader.api.services.backtest_service import BacktestService
from stock_trader.db.db_engine import database_session
from stock_trader.db.repositories.backtest_repo import BacktestRepository


def get_backtest_repository() -> BacktestRepository:
    """Get the backtest repository dependency.

    Returns:
        The backtest repository.
    """
    return BacktestRepository(session_maker=database_session)


async def get_backtest_service() -> BacktestService:
    """Get the backtest service dependency.

    Returns:
        The backtest service.
    """
    backtest_repo = get_backtest_repository()
    return BacktestService(backtest_repository=backtest_repo)
