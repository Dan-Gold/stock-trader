"""Strategy registry and lookup function."""

from stock_trader.core.interfaces.strategy_interface import IStrategy
from stock_trader.core.strategies.bollinger_reversion import BollingerReversionStrategy

STRATEGY_REGISTRY: dict[str, type[IStrategy]] = {
    "bollinger_reversion": BollingerReversionStrategy,
    # "rsi_oversold": RsiOversoldStrategy,  # future
}


def get_strategy(name: str) -> type[IStrategy]:
    """Look up a strategy class by name.

    This is what the Celery task calls:
        strategy_cls = get_strategy(job.strategy_name)
        strategy = strategy_cls(**job.parameters)
        result = strategy.run(df)

    Raises:
        ValueError: If the strategy name isn't registered.
    """
    if name not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")

    return STRATEGY_REGISTRY[name]
