"""Strategy registry and lookup function."""

from typing import NamedTuple

from pydantic import BaseModel

from stock_trader.core.interfaces.strategy_interface import IStrategy
from stock_trader.core.strategies.bollinger_reversion import BollingerParams, BollingerReversionStrategy


class StrategyEntry(NamedTuple):
    """A registered strategy with its parameter schema."""

    strategy_cls: type[IStrategy]
    params_model: type[BaseModel]


STRATEGY_REGISTRY: dict[str, StrategyEntry] = {
    "bollinger_reversion": StrategyEntry(BollingerReversionStrategy, BollingerParams),
    # "rsi_oversold": StrategyEntry(RsiOversoldStrategy, RsiParams),
}


def get_strategy(name: str) -> type[IStrategy]:
    """Look up a strategy class by name.

    Raises:
        ValueError: If the strategy name isn't registered.
    """
    entry = STRATEGY_REGISTRY.get(name)
    if entry is None:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return entry.strategy_cls


def get_params_model(name: str) -> type[BaseModel]:
    """Look up a strategy's params model by name.

    Raises:
        ValueError: If the strategy name isn't registered.
    """
    entry = STRATEGY_REGISTRY.get(name)
    if entry is None:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return entry.params_model
