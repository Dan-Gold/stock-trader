"""Celery tasks for ensuring market data: job-scoped (backtests) and symbol-scoped."""

import logging
from datetime import date
from uuid import UUID

from celery import Task, shared_task
from redis.exceptions import RedisError

from stock_trader.core.market_data.market_data_service import MarketDataService, NoDataError
from stock_trader.core.market_data.providers.market_data_provider_interface import ProviderError
from stock_trader.core.market_data.providers.massive.provider import MassiveProvider
from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.db.db_engine import get_sync_session_maker
from stock_trader.db.repositories.market_data_repo import MarketDataRepositorySync
from stock_trader.db.repositories.worker_repo import BacktestRepositorySync
from stock_trader.entrypoints.config import get_config
from stock_trader.infrastructure.redis_rate_limiter import build_massive_rate_limiter
from stock_trader.models.shared_enums import BacktestStatusEnum, IntervalEnum

logger = logging.getLogger(__name__)


def _on_fetch_failure(task: Task, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: object) -> None:
    """Mark the backtest job as FAILED when fetch exhausts all retries."""
    job_id = args[0] if args else kwargs.get("job_id")
    if not job_id:
        return

    logger.error("Job %s: ensure_market_data_for_job failed permanently: %s", job_id, exc)

    repo = BacktestRepositorySync(get_sync_session_maker())
    repo.update_job_status(
        UUID(job_id),
        BacktestStatusEnum.FAILED,
        error=f"Market data fetch failed: {exc}",
    )


@shared_task(
    name="ensure_market_data_for_job",
    max_retries=3,
    default_retry_delay=65,
    # RedisError: the rate limiter fails closed (raises) on a Redis error; retry
    # so a transient blip does not permanently fail the job.
    autoretry_for=(ProviderError, RedisError),
    on_failure=_on_fetch_failure,
)
def ensure_market_data_for_job(job_id: str) -> str:
    """Ensure and store market data for all symbols in a backtest job.

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


@shared_task(
    name="ensure_market_data_for_symbol",
    max_retries=3,
    default_retry_delay=65,
    # Mirror ensure_market_data_for_job: the Redis limiter fails closed (raises)
    # on a transient Redis blip, so retry rather than hard-fail.
    autoretry_for=(ProviderError, RedisError),
)
def ensure_market_data_for_symbol(symbol: str, interval: str, start_date: str, end_date: str) -> dict:
    """Ensure OHLCV data for one symbol/range; return the series as JSON.

    Symbol-scoped sibling of :func:`ensure_market_data_for_job`, run on the same fetch
    worker so it shares the Redis-backed rate limiter. No data for the range
    (e.g. a ticker with no history that far back) is NOT an error: it returns an
    empty series.

    Args:
        symbol: The ticker symbol.
        interval: The bar interval value (e.g. ``"1min"``).
        start_date: Inclusive ISO date (``YYYY-MM-DD``).
        end_date: Inclusive ISO date (``YYYY-MM-DD``).

    Returns:
        The OHLCV series serialized via ``model_dump(mode="json")``.
    """
    # Parse OUTSIDE the try: a malformed interval/date is a real input error and
    # must not be swallowed as "no data". On the API path FastAPI validates
    # these, but the task is independently callable.
    interval_enum = IntervalEnum(interval)
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    service = _build_market_data_service()
    try:
        series = service.ensure_data(symbol=symbol, interval=interval_enum, start_date=start, end_date=end)
    except NoDataError:
        # Valid "no data" result for this endpoint. Catch the TYPED exception,
        # not bare ValueError: other ValueError subclasses must surface as an
        # error, not be swallowed as an empty 200. (The provider path can't
        # produce one here — it wraps fetch+parse as ProviderError — but the
        # DB-reconstruction path can: a corrupt row raises ValueError/
        # pydantic.ValidationError out of get_ohlcv_data -> from_records.)
        series = OHLCVSeries(symbol=symbol, interval=interval_enum, bars=[])
    return series.model_dump(mode="json")


def _build_market_data_service() -> MarketDataService:
    """Build the MarketDataService with all dependencies.

    Called once per task execution. The rate limiter is Redis-backed so the
    Massive free-tier budget is shared across all worker processes and greenlets.
    """
    config = get_config()

    provider = MassiveProvider(api_key=config.massive_api_key)
    rate_limiter = build_massive_rate_limiter()
    market_data_repo = MarketDataRepositorySync(get_sync_session_maker())

    return MarketDataService(
        market_data_repository=market_data_repo,
        provider=provider,
        rate_limiter=rate_limiter,
    )
