"""Celery implementation of the task dispatcher."""

from celery import chain, chord

from stock_trader.core.backtest import finalize_backtest_job, run_backtest
from stock_trader.core.market_data.fetch_market_data import fetch_market_data


class CeleryTaskDispatcher:
    """Dispatches backtest pipelines via Celery chain + chord.

    Pipeline: fetch_market_data -> chord(run_backtest per symbol) -> finalize_backtest_job
    """

    def dispatch_backtest(self, job_id: str, symbols: list[str]) -> None:
        """Dispatch the full backtest pipeline to Celery workers."""
        task_group = [run_backtest.si(job_id, symbol) for symbol in symbols]
        callback = finalize_backtest_job.s(job_id)

        chain(
            fetch_market_data.s(job_id),
            chord(task_group, callback),
        ).apply_async()
