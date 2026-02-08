"""Dependencies for backtest service and repository."""

from fastapi import Depends, Request

from stock_trader.api.services.backtest_service import BacktestService
from stock_trader.db.db_engine import database_session
from stock_trader.db.interfaces.backtest_repo_interface import IBacktestRepoInterface
from stock_trader.db.repositories.backtest_repo import BacktestRepository
from stock_trader.infrastructure.redis_client import IRedisClient


def get_backtest_repository() -> IBacktestRepoInterface:
    """Get the backtest repository dependency.

    Returns:
        The backtest repository.
    """
    return BacktestRepository(session_maker=database_session)


def get_redis_client(request: Request) -> IRedisClient:
    """Get the Redis client from application state.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The Redis client instance.
    """
    return request.app.state.redis


def get_backtest_service(
    backtest_repo: IBacktestRepoInterface = Depends(get_backtest_repository),  # noqa: B008
    redis_client: IRedisClient = Depends(get_redis_client),  # noqa: B008
) -> BacktestService:
    """Get the backtest service dependency.

    Returns:
        The backtest service.
    """
    return BacktestService(backtest_repository=backtest_repo, redis_client=redis_client)
