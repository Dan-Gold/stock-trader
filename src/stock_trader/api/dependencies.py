"""Dependencies for backtest service and repository."""

from fastapi import Depends, Request

from stock_trader.api.interfaces.task_dispatcher_interface import ITaskDispatcher
from stock_trader.api.services.backtest_service import BacktestService
from stock_trader.api.services.celery_task_dispatcher import CeleryTaskDispatcher
from stock_trader.api.services.market_data_fetcher import MarketDataFetcher
from stock_trader.db.db_engine import get_async_session_maker
from stock_trader.db.interfaces.backtest_repo_interface import IBacktestRepoInterface
from stock_trader.db.repositories.backtest_repo import BacktestRepository
from stock_trader.entrypoints.config import get_config
from stock_trader.infrastructure.redis_client import IRedisClient


def get_backtest_repository() -> IBacktestRepoInterface:
    """Get the backtest repository dependency.

    Returns:
        The backtest repository.
    """
    return BacktestRepository(session_maker=get_async_session_maker())


def get_task_dispatcher() -> ITaskDispatcher:
    """Get the task dispatcher dependency.

    Returns:
        The Celery task dispatcher.
    """
    return CeleryTaskDispatcher()


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
    task_dispatcher: ITaskDispatcher = Depends(get_task_dispatcher),  # noqa: B008
) -> BacktestService:
    """Get the backtest service dependency.

    Returns:
        The backtest service.
    """
    return BacktestService(backtest_repository=backtest_repo, task_dispatcher=task_dispatcher)


def get_market_data_fetcher() -> MarketDataFetcher:
    """Get the market-data fetcher dependency.

    Returns:
        The market-data fetcher.
    """
    return MarketDataFetcher(result_timeout=get_config().market_data_fetch_timeout)
