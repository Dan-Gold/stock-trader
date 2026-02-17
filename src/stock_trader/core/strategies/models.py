"""Base classes and utilities for trading strategies."""

from enum import Enum

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class SignalType(str, Enum):
    """Enumeration of possible trade signals."""

    BUY = "BUY"
    SELL = "SELL"


class Trade(BaseModel):
    """A single executed trade in the backtest."""

    model_config = ConfigDict(frozen=True)

    timestamp: str
    signal: SignalType
    price: float = Field(gt=0)
    reason: str


class BacktestMetrics(BaseModel):
    """Performance metrics from a backtest run."""

    model_config = ConfigDict(frozen=True)

    total_return_pct: float = Field(default=0.0)
    num_trades: int = Field(default=0, ge=0)
    win_rate: float = Field(default=0.0, ge=0, le=100)
    max_drawdown_pct: float = Field(default=0.0, ge=0)
    ending_capital: float = Field(default=0.0, ge=0)


class BacktestResult(BaseModel):
    """Output of a strategy backtest run.

    Designed to map directly to BacktestResultTableSchema:
        - to_summary() -> summary JSONB column
        - to_raw()     -> raw JSONB column
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    strategy: str
    params: dict
    start_date: str
    end_date: str

    trades: list[Trade]
    metrics: BacktestMetrics
    chart_data: pd.DataFrame = Field(exclude=True)  # Excluded from model_dump()
    indicator_columns: list[str] = Field(default_factory=list, exclude=True)

    def to_summary(self) -> dict:
        """Build the summary JSONB payload for BacktestResultTableSchema.summary."""
        return self.model_dump(include={"strategy", "params", "start_date", "end_date", "metrics"})

    def to_raw(self) -> dict:
        """Build the raw JSONB payload for BacktestResultTableSchema.raw."""
        columns_to_store = ["close", *self.indicator_columns]
        chart_df = self.chart_data[columns_to_store].dropna()

        raw = chart_df.to_dict(orient="split")

        # Convert index timestamps to strings for JSON serialization
        raw["index"] = [str(ts) for ts in raw["index"]]

        raw["trades"] = [trade.model_dump() for trade in self.trades]

        return raw


def calculate_metrics(trades: list[Trade], initial_capital: float) -> BacktestMetrics:
    """Calculate performance metrics from a list of trades."""
    if not trades:
        return BacktestMetrics()

    # Pair up BUY/SELL trades
    completed_trades: list[tuple[Trade, Trade]] = []
    for i in range(0, len(trades) - 1, 2):
        if trades[i].signal == SignalType.BUY and trades[i + 1].signal == SignalType.SELL:
            completed_trades.append((trades[i], trades[i + 1]))

    if not completed_trades:
        return BacktestMetrics()

    wins = sum(1 for buy, sell in completed_trades if sell.price > buy.price)

    # Cumulative equity curve for drawdown
    equity = initial_capital
    peak = equity
    max_drawdown = 0.0

    for buy, sell in completed_trades:
        pnl = (sell.price - buy.price) / buy.price
        equity *= 1 + pnl
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak
        max_drawdown = max(max_drawdown, drawdown)

    total_return_pct = ((equity - initial_capital) / initial_capital) * 100

    return BacktestMetrics(
        total_return_pct=round(total_return_pct, 2),
        num_trades=len(completed_trades),
        win_rate=round(wins / len(completed_trades) * 100, 2),
        max_drawdown_pct=round(max_drawdown * 100, 2),
        ending_capital=round(equity, 2),
    )
