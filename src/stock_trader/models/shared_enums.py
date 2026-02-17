"""Shared enums for the stock trader application."""

from enum import StrEnum


class BacktestStatusEnum(StrEnum):
    """Enumeration for backtest job statuses."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IntervalEnum(StrEnum):
    """Enumeration for market data intervals."""

    ONE_MINUTE = "1min"
    FIVE_MINUTE = "5min"
    FIFTEEN_MINUTE = "15min"
    THIRTY_MINUTE = "30min"
    ONE_HOUR = "1h"
    DAILY = "1d"
