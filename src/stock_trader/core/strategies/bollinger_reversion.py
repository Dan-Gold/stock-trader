"""Bollinger Band mean reversion strategy implementation."""

from typing import Literal, cast

import numpy as np
import pandas as pd
import pandas_ta as ta
from pydantic import BaseModel, ConfigDict, Field

from stock_trader.core.strategies.models import BacktestResult, SignalType, Trade, calculate_metrics
from stock_trader.core.utils import regular_session_mask


class BollingerParams(BaseModel):
    """Validated parameters for the Bollinger Reversion strategy."""

    model_config = ConfigDict(extra="forbid")

    length: int = Field(default=20, ge=5, le=200, description="Bollinger Band lookback period")
    std_dev: float = Field(default=2.0, gt=0, le=5.0, description="Number of standard deviations for bands")
    exit_at: Literal["middle", "upper"] = Field(default="middle", description="Which band to exit at")
    initial_capital: float = Field(default=10000.0, gt=0, description="Starting capital for return calculations")


class BollingerReversionStrategy:
    """Intraday mean reversion using Bollinger Bands.

    Logic:
        - BUY when price closes below the lower band (oversold)
        - SELL when price reverts to the middle band (SMA) or hits upper band
        - Only one position at a time (no pyramiding)
    """

    name: str = "bollinger_reversion"
    params_model = BollingerParams

    def __init__(self, params: BollingerParams | None = None, **kwargs: object) -> None:
        if params is None:
            params = BollingerParams(**kwargs)

        self.length = params.length
        self.std_dev = params.std_dev
        self.exit_at = params.exit_at
        self.initial_capital = params.initial_capital

        self._params = params.model_dump()

    def _apply_bands(self, df: pd.DataFrame) -> list[str]:
        """Add bb_lower/bb_middle/bb_upper columns to ``df`` and return their names.

        Raises:
            ValueError: If pandas-ta cannot produce bands (e.g. too few rows) or
                an expected band column is missing from its output.
        """
        bbands = ta.bbands(df["close"], length=self.length, std=self.std_dev)  # type: ignore[arg-type]
        if bbands is None:
            raise ValueError(f"pandas-ta returned None for bbands. Check that df has at least {self.length} rows.")

        # pandas-ta column names vary by version (e.g. BBL_20_2.0 or BBL_20_2.0_2.0).
        # Look up by prefix to avoid hard-coding the suffix format.
        col_map: dict[str, str] = {}
        for prefix in ("BBL", "BBM", "BBU"):
            matches = [c for c in bbands.columns if c.startswith(prefix)]
            if not matches:
                raise ValueError(f"Expected a '{prefix}_*' column in bbands output, got: {list(bbands.columns)}")
            col_map[prefix] = matches[0]

        df["bb_lower"] = bbands[col_map["BBL"]]
        df["bb_middle"] = bbands[col_map["BBM"]]
        df["bb_upper"] = bbands[col_map["BBU"]]

        return ["bb_lower", "bb_middle", "bb_upper"]

    def run(self, df: pd.DataFrame) -> BacktestResult:
        """Run Bollinger Band mean reversion against price data."""
        df = df.copy()

        # --- Step 1: Calculate Bollinger Bands via pandas-ta ---
        indicator_columns = self._apply_bands(df)

        # --- Step 2: Generate signals ---
        trades: list[Trade] = []
        in_position = False

        # Only emit trades during the regular session. Bands are still computed
        # over the full df above, so extended-hours bars inform the indicators
        # without being tradeable. Computed once and reused by the forced exit.
        session_mask = regular_session_mask(cast(pd.DatetimeIndex, df.index))

        # Determine which band to use for exit
        exit_col = "bb_middle" if self.exit_at == "middle" else "bb_upper"

        for i in range(self.length, len(df)):
            if not session_mask[i]:
                continue

            row = df.iloc[i]
            close = row["close"]
            timestamp = df.index[i]

            if not in_position:
                # BUY signal: close below lower band
                if close < row["bb_lower"]:
                    in_position = True
                    trades.append(
                        Trade(
                            timestamp=timestamp,
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
                            timestamp=timestamp,
                            signal=SignalType.SELL,
                            price=close,
                            reason=f"Close ({close:.2f}) >= {self.exit_at.title()} Band ({row[exit_col]:.2f})",
                        )
                    )

        # Force sell at end of data if still in position. Exit on the last
        # in-session bar so the position is never closed at an extended-hours price.
        if in_position:
            session_positions = np.flatnonzero(session_mask)
            if session_positions.size > 0:
                exit_i = int(session_positions[-1])
                exit_row = df.iloc[exit_i]
                trades.append(
                    Trade(
                        timestamp=df.index[exit_i],
                        signal=SignalType.SELL,
                        price=exit_row["close"],
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
