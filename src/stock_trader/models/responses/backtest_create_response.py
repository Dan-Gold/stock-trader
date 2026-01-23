"""Backtest create response model."""

from uuid import UUID

from pydantic import BaseModel

from stock_trader.models.shared_enums import BacktestStatusEnum


class BacktestCreateResponse(BaseModel):
    """Response body after creating a backtest job."""

    uuid: UUID
    status: BacktestStatusEnum
