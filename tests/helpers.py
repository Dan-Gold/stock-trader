"""Helpers for unit tests."""

from datetime import date, datetime, timezone
from uuid import uuid4

import numpy as np
import pandas as pd
from massive.rest.models import Agg

from stock_trader.api.services.backtest_service import BacktestService
from stock_trader.core.models.ohlcv_series import OHLCV, OHLCVSeries
from stock_trader.core.strategies.models import (
    BacktestResult,
    SignalType,
    Trade,
    calculate_metrics,
)
from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.db.models.market_data import MarketDataTableSchema
from stock_trader.models.backtest_create_request import BacktestCreateRequest
from stock_trader.models.shared_enums import BacktestStatusEnum, IntervalEnum
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


def make_ohlcv_df(
    close_prices: list[float],
    *,
    start: str = "2024-01-02 09:30",
    tz: str = "America/New_York",
    freq: str = "min",
) -> pd.DataFrame:
    """Build a minimal intraday OHLCV DataFrame from a list of close prices.

    Produces tz-aware 1-minute bars starting at the regular-session open, matching
    the production data shape (the strategy is intraday and gates on market hours,
    so bars must be tz-aware and within the session to be tradeable).
    High/low/open are set equal to close for simplicity, the strategy only uses
    the close column.
    """
    dates = pd.date_range(start, periods=len(close_prices), freq=freq, tz=tz)
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
    """Create a price series: flat -> dip below lower band -> revert to middle.

    With default std_dev=2.0 and a flat series at 100, the lower band collapses
    to 100 (zero volatility). So we need initial volatility, we use a small
    oscillation then inject the dip.
    """
    # Build with minor oscillation so bands have width
    rng = np.random.default_rng(42)
    flat = flat_price + rng.normal(0, 1.5, n_flat)
    flat = flat.tolist()
    return flat + [dip_price] * n_dip + [revert_price] * n_revert


def make_trade(signal: SignalType, price: float, day: int = 1) -> Trade:
    """Build a Trade with minimal boilerplate."""
    return Trade(
        timestamp=datetime(2024, 1, day, tzinfo=timezone.utc),
        signal=signal,
        price=price,
        reason="test",
    )


def make_buy_trade(price: float, *, day: int) -> Trade:
    """Build a BUY Trade. ``day`` is required to avoid implicit timestamp mismatches."""
    return make_trade(SignalType.BUY, price, day)


def make_sell_trade(price: float, *, day: int) -> Trade:
    """Build a SELL Trade. ``day`` is required to avoid implicit timestamp mismatches."""
    return make_trade(SignalType.SELL, price, day)


def make_backtest_result() -> BacktestResult:
    """Build a BacktestResult with one winning trade and chart data."""
    trades = [make_buy_trade(100.0, day=1), make_sell_trade(110.0, day=2)]
    metrics = calculate_metrics(trades, initial_capital=10000)

    index = pd.date_range("2024-01-01", periods=3, freq="D")
    chart_data = pd.DataFrame(
        {
            "close": [100.0, 105.0, 110.0],
            "bb_lower": [95.0, 96.0, 97.0],
            "bb_middle": [100.0, 101.0, 102.0],
            "bb_upper": [105.0, 106.0, 107.0],
        },
        index=index,
    )

    return BacktestResult(
        strategy="bollinger_reversion",
        params={"length": 20},
        start_date="2024-01-01",
        end_date="2024-01-03",
        trades=trades,
        metrics=metrics,
        chart_data=chart_data,
        indicator_columns=["bb_lower", "bb_middle", "bb_upper"],
    )


def make_ohlcv_bar(
    ts: datetime,
    close: float = 100.0,
    *,
    vwap: float | None = None,
    transactions: int | None = None,
) -> OHLCV:
    """Build an OHLCV bar with open/high/low derived from close."""
    return OHLCV(
        timestamp=ts,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1000,
        vwap=vwap,
        transactions=transactions,
    )


def make_ohlcv_series(bars: list[OHLCV] | None = None) -> OHLCVSeries:
    """Build an OHLCVSeries with sensible defaults (3 one-minute AAPL bars)."""
    if bars is None:
        bars = [
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), close=100.0),
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 1, tzinfo=timezone.utc), close=101.0),
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 2, tzinfo=timezone.utc), close=102.0),
        ]
    return OHLCVSeries(symbol="AAPL", interval=IntervalEnum.ONE_MINUTE, bars=bars)


def make_job_schema(**overrides: object) -> BacktestJobTableSchema:
    """Build a BacktestJobTableSchema with sensible defaults."""
    defaults: dict[str, object] = {
        "uuid": uuid4(),
        "status": BacktestStatusEnum.CREATED,
        "strategy_name": "bollinger_reversion",
        "symbols": ["AAPL", "TSLA"],
        "parameters": {"length": 20},
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 6, 30),
        "create_time": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        "start_time": None,
        "end_time": None,
        "error": None,
    }
    defaults.update(overrides)
    return BacktestJobTableSchema(**defaults)


def make_agg(
    *,
    timestamp: int = 1_704_067_200_000,  # 2024-01-01 00:00:00 UTC in ms
    open: float = 100.0,
    high: float = 105.0,
    low: float = 95.0,
    close: float = 102.0,
    volume: float = 50000.0,
    vwap: float | None = 101.0,
    transactions: int | None = 1200,
) -> Agg:
    """Build a Massive Agg with sensible defaults."""
    return Agg(
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        vwap=vwap,
        timestamp=timestamp,
        transactions=transactions,
    )


def make_ohlcv(
    *,
    ts: datetime = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
    close: float = 100.0,
) -> OHLCV:
    """Build a simple OHLCV with the given timestamp and close price. High/low/open are derived from close for simplicity."""
    return OHLCV(
        timestamp=ts,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1000,
    )


def make_row(
    *,
    symbol: str = "AAPL",
    interval: IntervalEnum = IntervalEnum.ONE_MINUTE,
    ts: datetime = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
    close: float = 100.0,
) -> MarketDataTableSchema:
    """Build a simple MarketDataTableSchema row with the given timestamp and close price."""
    return MarketDataTableSchema(
        symbol=symbol,
        interval=interval,
        timestamp=ts,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1000,
    )
