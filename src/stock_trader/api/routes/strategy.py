"""API routes for strategy-related operations, including retrieving available strategies and their parameter schemas."""

import logging

from fastapi import APIRouter

from stock_trader.core.strategies.registry import (
    get_strategies,
    get_strategy_schema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategy"])


@router.get(
    "/available",
    operation_id="get_available_strategies",
    response_model=list[str],
    summary="Get available strategy names",
)
async def get_available_strategies() -> list[str]:
    """Get the list of available strategy names.

    Returns:
        A list of strategy names that can be backtested.
    """
    return get_strategies()


@router.get(
    "/{strategy_name}/schema",
    operation_id="get_strategy_parameter_schema",
    summary="Get full parameter schema with constraints",
)
async def get_strategy_parameter_schema(strategy_name: str) -> dict:
    """Get the full JSON Schema for a strategy's parameters.

    Includes types, constraints (min/max/enum), defaults, and descriptions.

    Args:
        strategy_name: The registered strategy name.

    Returns:
        The JSON Schema for the strategy's parameter model.
    """
    return get_strategy_schema(strategy_name)


@router.get(
    "/all_strategies_all_parameters",
    operation_id="get_all_strategies_and_parameters",
    summary="Get parameter schemas for all strategies",
)
async def get_all_strategies_and_parameters() -> dict[str, dict]:
    """Get the parameter schemas for all registered strategies.

    Returns:
        A dictionary mapping strategy names to their parameter schemas.
    """
    strategies = get_strategies()
    return {name: get_strategy_schema(name) for name in strategies}
