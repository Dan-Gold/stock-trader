"""Shared enums for the stock trader application."""

from enum import StrEnum


class BacktestStatusEnum(StrEnum):
    """Enumeration for backtest job statuses."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
