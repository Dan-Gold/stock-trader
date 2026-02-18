"""Celery task for fetching market data before backtests."""

import logging
from uuid import UUID

from celery import Task, shared_task

from stock_trader.core.market_data.market_data_service import MarketDataService
from stock_trader.core.market_data.providers.market_data_provider_interface import ProviderError
from stock_trader.core.market_data.providers.massive.provider import MassiveProvider
from stock_trader.core.market_data.providers.massive.rate_limiter import MassiveRateLimiter
from stock_trader.db.db_engine import get_sync_session_maker
from stock_trader.db.repositories.market_data_repo import MarketDataRepositorySync
from stock_trader.db.repositories.worker_repo import BacktestRepositorySync
from stock_trader.entrypoints.config import get_config
from stock_trader.models.shared_enums import BacktestStatusEnum, IntervalEnum

logger = logging.getLogger(__name__)


def _on_fetch_failure(self: Task, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: object) -> None:
    """Mark the backtest job as FAILED when fetch exhausts all retries."""
    job_id = args[0] if args else kwargs.get("job_id")
    if not job_id:
        return

    logger.error("Job %s: fetch_market_data failed permanently: %s", job_id, exc)

    repo = BacktestRepositorySync(get_sync_session_maker())
    repo.update_job_status(
        UUID(job_id),
        BacktestStatusEnum.FAILED,
        error=f"Market data fetch failed: {exc}",
    )


@shared_task(
    name="fetch_market_data",
    max_retries=3,
    default_retry_delay=65,
    autoretry_for=(ProviderError,),
    on_failure=_on_fetch_failure,
)
def fetch_market_data(job_id: str) -> str:
    """Fetch and store market data for all symbols in a backtest job.

    Runs before the backtest chord. For each symbol, checks Postgres first
    and only calls the Massive API on a cache miss. The rate limiter
    ensures we stay within the free-tier window limit.

    Args:
        job_id: The backtest job UUID (as string).

    Returns:
        The job_id (passes through to the next task in the chain).
    """
    repo = BacktestRepositorySync(get_sync_session_maker())
    job = repo.get_backtest_job(UUID(job_id))

    logger.info("Job %s: Fetching %s data for %d symbols: %s", job_id, IntervalEnum.ONE_MINUTE, len(job.symbols), job.symbols)

    service = _build_market_data_service()

    for symbol in job.symbols:
        logger.info("Job %s: Ensuring data for %s (%s to %s)", job_id, symbol, job.start_date, job.end_date)
        service.ensure_data(
            symbol=symbol,
            interval=IntervalEnum.ONE_MINUTE,
            start_date=job.start_date,
            end_date=job.end_date,
        )

    logger.info("Job %s: All market data fetched and stored", job_id)
    return job_id


def _build_market_data_service() -> MarketDataService:
    """Build the MarketDataService with all dependencies.

    Called once per task execution. The rate limiter is in-memory,
    which works because worker_concurrency=1.
    """
    config = get_config()

    provider = MassiveProvider(api_key=config.massive_api_key)
    rate_limiter = MassiveRateLimiter()
    market_data_repo = MarketDataRepositorySync(get_sync_session_maker())

    return MarketDataService(
        market_data_repository=market_data_repo,
        provider=provider,
        rate_limiter=rate_limiter,
    )
