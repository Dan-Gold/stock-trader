"""Helpers for unit tests."""

from datetime import date

from stock_trader.api.services.backtest_service import BacktestService
from stock_trader.models.backtest_create_request import BacktestCreateRequest
from tests.in_memory.in_memory_backtest_repo import MemoryBacktestRepository
from tests.in_memory.in_memory_task_dispatcher import MemoryTaskDispatcher


def make_backtest_request(
    *,
    strategy_name: str = "bollinger_reversion",
    symbols: list[str] | None = None,
    parameters: dict | None = None,
    start_date: date = date(2024, 1, 1),
    end_date: date = date(2024, 6, 30),
) -> BacktestCreateRequest:
    """Build a valid BacktestCreateRequest with sensible defaults."""
    return BacktestCreateRequest(
        strategy_name=strategy_name,
        symbols=symbols or ["AAPL"],
        parameters=parameters or {},
        start_date=start_date,
        end_date=end_date,
    )


def build_service(
    repo: MemoryBacktestRepository,
    dispatcher: MemoryTaskDispatcher,
) -> BacktestService:
    """Build a BacktestService using the provided in-memory repo and dispatcher."""
    return BacktestService(
        backtest_repository=repo,
        task_dispatcher=dispatcher,
    )
