"""In-memory implementation of ITaskDispatcher for unit tests."""


class MemoryTaskDispatcher:
    """In-memory implementation of ITaskDispatcher for unit tests.

    Records every dispatch call so tests can assert on dispatch behavior.
    """

    def __init__(self) -> None:
        """Initialize the in-memory task dispatcher."""
        self.dispatches: list[dict[str, object]] = []

    def dispatch_backtest(self, job_id: str, symbols: list[str]) -> None:
        """Record a backtest dispatch call."""
        self.dispatches.append({"job_id": job_id, "symbols": symbols})
