"""Celery implementation of the task dispatcher."""

from celery import chain, chord

from stock_trader.core.backtest import finalize_backtest_job, run_backtest
from stock_trader.core.market_data.market_data_tasks import ensure_market_data_for_job


class CeleryTaskDispatcher:
    """Dispatches backtest pipelines via Celery chain + chord.

    Pipeline: ensure_market_data_for_job -> chord(run_backtest per symbol) -> finalize_backtest_job
    """

    def dispatch_backtest(self, job_id: str, symbols: list[str]) -> None:
        """Dispatch the full backtest pipeline to Celery workers."""
        task_group = [run_backtest.si(job_id, symbol) for symbol in symbols]
        callback = finalize_backtest_job.s(job_id)

        chain(
            ensure_market_data_for_job.s(job_id),
            chord(task_group, callback),
        ).apply_async()
