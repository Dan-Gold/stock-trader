"""Backtest response model."""

from uuid import UUID

from pydantic import BaseModel

from stock_trader.models.shared_enums import BacktestStatusEnum


class BacktestResponse(BaseModel):
    """Response body for a backtest job."""

    uuid: UUID
    status: BacktestStatusEnum
    strategy_name: str
    symbols: list[str]
    parameters: dict
    error: str | None = None
