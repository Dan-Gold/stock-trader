"""Interface for trading strategies."""

from typing import Protocol

import pandas as pd

from stock_trader.core.strategies.base import BacktestResult


class Strategy(Protocol):
    """Protocol that all strategies must satisfy."""

    name: str

    def run(self, df: pd.DataFrame) -> BacktestResult:
        """Run the strategy against historical price data.

        Args:
            df: Must have at minimum: open, high, low, close, volume columns.
                Index should be a DatetimeIndex.

        Returns:
            BacktestResult with trades, metrics, and chart data.
        """
        ...
