"""Massive (formerly Polygon.io) API → OHLCV domain model mapper."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from massive.rest.models import Agg

from stock_trader.core.models.ohlcv_series import OHLCV, OHLCVSeries
from stock_trader.models.shared_enums import IntervalEnum

_INTERVAL_MAP: dict[tuple[int, str], IntervalEnum] = {
    (1, "minute"): IntervalEnum.ONE_MINUTE,
    (5, "minute"): IntervalEnum.FIVE_MINUTE,
    (15, "minute"): IntervalEnum.FIFTEEN_MINUTE,
    (30, "minute"): IntervalEnum.THIRTY_MINUTE,
    (1, "hour"): IntervalEnum.ONE_HOUR,
    (1, "day"): IntervalEnum.DAILY,
}


def resolve_interval(multiplier: int, timespan: str) -> IntervalEnum:
    """Map Massive API parameters to an IntervalEnum.

    Args:
        multiplier: The timespan multiplier (e.g. 1 for 1-minute).
        timespan: The timespan unit (e.g. ``"minute"``).

    Raises:
        ValueError: If the combination is not supported.
    """
    interval = _INTERVAL_MAP.get((multiplier, timespan))
    if interval is None:
        raise ValueError(f"Unsupported Massive interval: ({multiplier}, '{timespan}'). Supported: {list(_INTERVAL_MAP.keys())}")
    return interval


def agg_to_ohlcv(agg: Agg, symbol: str, interval: IntervalEnum) -> OHLCV:
    """Convert a single Massive ``Agg`` object to an OHLCV domain model.

    Args:
        agg: A Massive ``Agg`` object with attributes: timestamp, open, high, low, close, volume, vwap, transactions.
        symbol: Ticker symbol, e.g. ``"AAPL"``.
        interval: The resolved IntervalEnum value.
    """
    return OHLCV(
        symbol=symbol,
        timestamp=datetime.fromtimestamp(agg.timestamp / 1000, tz=timezone.utc),
        interval=interval,
        open=agg.open,
        high=agg.high,
        low=agg.low,
        close=agg.close,
        volume=int(agg.volume),
        vwap=agg.vwap if agg.vwap is not None else None,
        transactions=agg.transactions if agg.transactions is not None else None,
    )


def aggs_to_ohlcv_series(
    aggs: Iterable[Agg],
    symbol: str,
    multiplier: int,
    timespan: str,
) -> OHLCVSeries:
    """Convert Massive ``list_aggs`` results into an OHLCVSeries.

    Args:
        aggs: Iterable of Massive ``Agg`` objects (consumed once).
        symbol: Ticker symbol, e.g. ``"AAPL"``.
        multiplier: The timespan multiplier (e.g. 1 for 1-minute).
        timespan: The timespan unit (e.g. ``"minute"``).

    Raises:
        ValueError: If the (multiplier, timespan) combination is not
            mapped to a known IntervalEnum value.
    """
    interval = resolve_interval(multiplier, timespan)
    bars = [agg_to_ohlcv(a, symbol, interval) for a in aggs]
    return OHLCVSeries(symbol=symbol, interval=interval, bars=bars)
