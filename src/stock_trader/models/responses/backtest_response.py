"""Backtest response model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from stock_trader.models.shared_enums import BacktestStatusEnum

if TYPE_CHECKING:
    from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema


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

    @classmethod
    def from_job(cls, job: BacktestJobTableSchema) -> BacktestResponse:
        """Create a BacktestResponse from a BacktestJobTableSchema."""
        return cls(
            uuid=job.uuid,
            status=job.status,
            strategy_name=job.strategy_name,
            symbols=job.symbols,
            parameters=job.parameters,
            error=job.error,
            create_time=job.create_time,
            start_time=job.start_time,
            end_time=job.end_time,
        )
