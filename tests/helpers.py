"""Helpers for unit tests."""

from datetime import date

import numpy as np
import pandas as pd

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


def make_ohlcv_df(close_prices: list[float], *, start: str = "2024-01-01") -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from a list of close prices.

    High/low/open are set equal to close for simplicity — the strategy
    only uses the close column.
    """
    dates = pd.date_range(start, periods=len(close_prices), freq="D")
    df = pd.DataFrame(
        {
            "open": close_prices,
            "high": close_prices,
            "low": close_prices,
            "close": close_prices,
            "volume": [1000] * len(close_prices),
        },
        index=dates,
    )
    return df


def flat_then_dip_then_revert(
    n_flat: int = 25,
    flat_price: float = 100.0,
    dip_price: float = 80.0,
    n_dip: int = 1,
    revert_price: float = 100.0,
    n_revert: int = 1,
) -> list[float]:
    """Create a price series: flat → dip below lower band → revert to middle.

    With default std_dev=2.0 and a flat series at 100, the lower band collapses
    to 100 (zero volatility). So we need initial volatility — we use a small
    oscillation then inject the dip.
    """
    # Build with minor oscillation so bands have width
    rng = np.random.default_rng(42)
    flat = flat_price + rng.normal(0, 1.5, n_flat)
    flat = flat.tolist()
    return flat + [dip_price] * n_dip + [revert_price] * n_revert
