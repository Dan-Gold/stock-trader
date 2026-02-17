"""Tasks for running backtest jobs."""

import logging
import traceback
from uuid import UUID

from celery import shared_task

from stock_trader.core.interfaces.strategy_interface import IStrategy
from stock_trader.core.strategies.registry import get_strategy
from stock_trader.db.db_engine import database_session_sync
from stock_trader.db.repositories.market_data_repo import MarketDataRepositorySync
from stock_trader.db.repositories.worker_repo import BacktestRepositorySync
from stock_trader.models.shared_enums import BacktestStatusEnum

logger = logging.getLogger(__name__)


@shared_task(
    name="run_backtest",
    max_retries=1,
    default_retry_delay=10,
)
def run_backtest(job_id: str, symbol: str) -> dict:
    """Run a backtest for a single symbol within a job.

    This task is dispatched as part of a Celery chord — one task per symbol.
    After all symbol tasks complete, the finalize_backtest_job callback runs.

    Exceptions are caught and returned as error dicts so the chord always
    completes cleanly. The finalize callback inspects results to determine
    overall job status.

    Args:
        job_id: The parent backtest job UUID (as string).
        symbol: The stock ticker symbol to backtest.

    Returns:
        A dict containing either the backtest success or an error.
    """
    backtest_repo = BacktestRepositorySync(database_session_sync)
    market_data_repo = MarketDataRepositorySync(database_session_sync)
    job_uuid = UUID(job_id)

    try:
        # ------------------------------------------------------------------
        # Step 1: Pull job details from the database.
        # ------------------------------------------------------------------
        job = backtest_repo.get_backtest_job(job_uuid)
        strategy_name = job.strategy_name
        strategy_params = job.parameters or {}

        logger.info(f"Job {job_id}: Running '{strategy_name}' on {symbol} with params {strategy_params}")

        # ------------------------------------------------------------------
        # Step 2: Load historical price data from the database.
        #         Data was fetched by the upstream fetch_market_data task.
        # ------------------------------------------------------------------
        ohlcv = market_data_repo.get_ohlcv_data(
            symbol=symbol,
            start_time=job.start_date,
            end_time=job.end_date,
        )

        if not ohlcv:
            raise ValueError(f"No market data found for {symbol} between {job.start_date} and {job.end_date}")

        df = ohlcv.to_dataframe()
        logger.info(f"Job {job_id}: Loaded {len(df)} rows of data for {symbol}")

        # ------------------------------------------------------------------
        # Step 3: Run the trading strategy.
        # ------------------------------------------------------------------
        strategy_cls = get_strategy(job.strategy_name)
        strategy: IStrategy = strategy_cls(**strategy_params)
        results = strategy.run(df)

        logger.info(f"Job {job_id}: Backtest complete for {symbol} — total return: {results.metrics.total_return_pct:.2f}%")

        # ------------------------------------------------------------------
        # Step 4: Persist results to the database.
        # ------------------------------------------------------------------
        backtest_repo.save_job_result(
            job_id=job_uuid,
            symbol=symbol,
            summary=results.to_summary(),
            raw=results.to_raw(),
        )

    except Exception as exc:
        logger.error(f"Job {job_id}: Backtest failed for {symbol}: {exc}")
        logger.error(traceback.format_exc())
        return {"symbol": symbol, "error": str(exc)}

    return {"symbol": symbol, "status": "completed"}


@shared_task()
def finalize_backtest_job(results: list[dict], job_id: str) -> None:
    """Chord callback — mark the parent job as completed or failed.

    This runs automatically after all run_backtest tasks in the chord finish.
    Celery passes the list of return values from all tasks as the first argument.

    Args:
        results: List of return dicts from each run_backtest task.
        job_id: The parent backtest job UUID (as string).
    """
    repo = BacktestRepositorySync(database_session_sync)
    job_uuid = UUID(job_id)

    failed = [r for r in results if r.get("error")]

    if failed:
        failed_symbols = [r["symbol"] for r in failed]
        error_msg = f"{len(failed)} of {len(results)} symbols failed: {', '.join(failed_symbols)}"
        logger.error(f"Job {job_id}: {error_msg}")

        repo.update_job_status(
            job_uuid,
            BacktestStatusEnum.FAILED,
            error=error_msg,
        )
    else:
        logger.info(f"Job {job_id}: All {len(results)} symbols completed successfully")
        repo.update_job_status(job_uuid, BacktestStatusEnum.COMPLETED)
