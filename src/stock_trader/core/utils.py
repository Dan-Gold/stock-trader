"""Shared utility functions for the stock trader application."""

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def get_utc_now() -> datetime:
    """Get the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=UTC)


def load_csv_data(csv_path: Path) -> pd.DataFrame:
    """Load and validate historical price data from a CSV file.

    Expected CSV columns: timestamp, open, high, low, close, volume
    (standard OHLCV format from Yahoo Finance, Alpha Vantage, etc.)

    Args:
        csv_path: Path to the CSV file.

    Returns:
        A DataFrame with a DatetimeIndex and OHLCV columns.
    """
    df: pd.DataFrame = pd.read_csv(csv_path, parse_dates=["timestamp"], index_col="timestamp")
    df.sort_index(inplace=True)

    required_columns = {"open", "high", "low", "close", "volume"}
    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    return df
