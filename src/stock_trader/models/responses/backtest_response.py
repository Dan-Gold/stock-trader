"""Backtest response model."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from stock_trader.models.shared_enums import BacktestStatusEnum


class BacktestResponse(BaseModel):
    """Response body for a backtest job."""

    uuid: UUID
    status: BacktestStatusEnum
    strategy_name: str
    symbols: list[str]
    parameters: dict[str, str | int | float | bool]
    error: str | None = None
    create_time: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
