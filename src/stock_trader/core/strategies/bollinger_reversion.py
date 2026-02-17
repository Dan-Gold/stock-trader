"""Bollinger Band mean reversion strategy implementation."""

import pandas as pd
import pandas_ta as ta

from stock_trader.core.strategies.models import BacktestResult, SignalType, Trade, calculate_metrics


class BollingerReversionStrategy:
    """Intraday mean reversion using Bollinger Bands.

    Logic:
        - BUY when price closes below the lower band (oversold)
        - SELL when price reverts to the middle band (SMA) or hits upper band
        - Only one position at a time (no pyramiding)

    Parameters:
        length: Bollinger Band lookback period (default 20)
        std_dev: Number of standard deviations for bands (default 2.0)
        exit_at: Where to exit — "middle" (SMA) or "upper" (upper band)
        initial_capital: Starting capital for return calculations
    """

    name: str = "bollinger_reversion"

    def __init__(
        self,
        length: int = 20,
        std_dev: float = 2.0,
        exit_at: str = "middle",
        initial_capital: float = 10000.0,
    ) -> None:
        if exit_at not in ("middle", "upper"):
            raise ValueError(f"exit_at must be 'middle' or 'upper', got '{exit_at}'")

        self.length = length
        self.std_dev = std_dev
        self.exit_at = exit_at
        self.initial_capital = initial_capital

        # Store parameters in a dict for easy access in results
        self._params = {
            "initial_capital": self.initial_capital,
            "length": self.length,
            "std_dev": self.std_dev,
            "exit_at": self.exit_at,
        }

    def run(self, df: pd.DataFrame) -> BacktestResult:
        """Run Bollinger Band mean reversion against price data."""
        df = df.copy()

        # --- Step 1: Calculate Bollinger Bands via pandas-ta ---
        bbands = ta.bbands(df["close"], length=self.length, std=self.std_dev)  # Type: ignore
        if bbands is None:
            raise ValueError(f"pandas-ta returned None for bbands. Check that df has at least {self.length} rows.")

        # pandas-ta names columns like: BBL_20_2.0_2.0, BBM_20_2.0_2.0, BBU_20_2.0_2.0
        suffix = f"{self.length}_{self.std_dev}_{self.std_dev}"
        df["bb_lower"] = bbands[f"BBL_{suffix}"]
        df["bb_middle"] = bbands[f"BBM_{suffix}"]
        df["bb_upper"] = bbands[f"BBU_{suffix}"]

        indicator_columns = ["bb_lower", "bb_middle", "bb_upper"]

        # --- Step 2: Generate signals ---
        trades: list[Trade] = []
        in_position = False

        # Determine which band to use for exit
        exit_col = "bb_middle" if self.exit_at == "middle" else "bb_upper"

        for i in range(self.length, len(df)):
            row = df.iloc[i]
            close = row["close"]
            timestamp = df.index[i]

            if not in_position:
                # BUY signal: close below lower band
                if close < row["bb_lower"]:
                    in_position = True
                    trades.append(
                        Trade(
                            timestamp=str(timestamp),
                            signal=SignalType.BUY,
                            price=close,
                            reason=f"Close ({close:.2f}) < Lower Band ({row['bb_lower']:.2f})",
                        )
                    )
            else:
                # SELL signal: close reaches exit band
                if close >= row[exit_col]:
                    in_position = False
                    trades.append(
                        Trade(
                            timestamp=str(timestamp),
                            signal=SignalType.SELL,
                            price=close,
                            reason=f"Close ({close:.2f}) >= {self.exit_at.title()} Band ({row[exit_col]:.2f})",
                        )
                    )

        # Force sell at end of data if still in position
        if in_position:
            last_row = df.iloc[-1]
            trades.append(
                Trade(
                    timestamp=str(df.index[-1]),
                    signal=SignalType.SELL,
                    price=last_row["close"],
                    reason="End of data, forced exit",
                )
            )

        # --- Step 3: Calculate metrics ---
        metrics = calculate_metrics(trades=trades, initial_capital=self.initial_capital)

        return BacktestResult(
            strategy=self.name,
            params=self._params,
            start_date=str(df.index[0]),
            end_date=str(df.index[-1]),
            trades=trades,
            metrics=metrics,
            chart_data=df,
            indicator_columns=indicator_columns,
        )
