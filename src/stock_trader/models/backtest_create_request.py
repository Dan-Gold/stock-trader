"""Backtest create request model."""

from pydantic import BaseModel, Field


class BacktestCreateRequest(BaseModel):
    """Request body for creating a new backtest job."""

    strategy_name: str = Field(..., max_length=50, description="Name of the trading strategy to run")
    symbols: list[str] = Field(..., min_length=1, description="List of stock symbols to backtest")
    parameters: dict = Field(default_factory=dict, description="Strategy-specific parameters")
