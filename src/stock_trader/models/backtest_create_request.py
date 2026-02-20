"""Backtest create request model."""

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from stock_trader.core.strategies.registry import STRATEGY_REGISTRY


class BacktestCreateRequest(BaseModel):
    """Request body for creating a new backtest job."""

    strategy_name: str = Field(..., max_length=50, description="Name of the trading strategy to run")
    symbols: list[str] = Field(..., min_length=1, description="List of stock symbols to backtest")
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict, description="Strategy-specific parameters")
    start_date: date = Field(..., description="Start date inclusive, ISO format YYYY-MM-DD")
    end_date: date = Field(..., description="End date inclusive, ISO format YYYY-MM-DD")

    @model_validator(mode="after")
    def validate_date_range(self) -> "BacktestCreateRequest":
        """Ensure end_date is not before start_date."""
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Ensure the strategy name is valid and exists in the registry."""
        if v not in STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy '{v}'. Available: {list(STRATEGY_REGISTRY.keys())}")
        return v

    @model_validator(mode="after")
    def validate_parameters(self) -> "BacktestCreateRequest":
        """Validate parameters against the strategy's params model.

        This catches invalid/unknown params at request time instead of
        letting them fail inside the Celery worker.
        """
        entry = STRATEGY_REGISTRY.get(self.strategy_name)
        if entry is not None:
            entry.params_model(**self.parameters)
        return self
