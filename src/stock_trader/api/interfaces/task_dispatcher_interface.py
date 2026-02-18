"""Protocol for dispatching backtest tasks to a worker backend."""

from typing import Protocol


class ITaskDispatcher(Protocol):
    """Protocol for dispatching tasks."""

    def dispatch_backtest(self, job_id: str, symbols: list[str]) -> None:
        """Dispatch a full backtest pipeline for a job.

        Args:
            job_id: The backtest job UUID as a string.
            symbols: List of stock ticker symbols to backtest.
        """
        ...
