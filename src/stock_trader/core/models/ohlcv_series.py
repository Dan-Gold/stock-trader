"""OHLCV (Open-High-Low-Close-Volume) data models for a series of bars for a single symbol and interval."""

from datetime import datetime

import pandas as pd
from pydantic import BaseModel

from stock_trader.models.shared_enums import IntervalEnum


class OHLCV(BaseModel):
    """One OHLCV bar for a specific symbol, timestamp, and interval."""

    timestamp: datetime

    open: float
    high: float
    low: float
    close: float
    volume: int

    # Extras
    vwap: float | None = None
    transactions: int | None = None


class OHLCVSeries(BaseModel):
    """An ordered collection of OHLCV bars for a single symbol and interval."""

    symbol: str
    interval: IntervalEnum
    bars: list[OHLCV]

    def __bool__(self) -> bool:
        """True if there is at least one bar in the series."""
        return len(self.bars) > 0

    def __len__(self) -> int:
        """Number of bars in the series."""
        return len(self.bars)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to a pandas DataFrame indexed by timestamp.

        Symbol and interval are omitted from columns since they are
        constant across the series and accessible via the parent object.

        Returns:
            DataFrame with columns: open, high, low, close, volume,
            and optionally vwap, transactions.
        """
        df = pd.DataFrame([bar.model_dump() for bar in self.bars])
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)

        # Drop optional columns if they're entirely null
        for col in ("vwap", "transactions"):
            if col in df.columns and df[col].isna().all():
                df.drop(columns=col, inplace=True)

        return df
