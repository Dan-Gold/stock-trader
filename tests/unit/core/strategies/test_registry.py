"""Unit tests for strategy registry."""

import pytest

from stock_trader.core.strategies.bollinger_reversion import BollingerReversionStrategy
from stock_trader.core.strategies.registry import STRATEGY_REGISTRY, get_strategy


class TestGetStrategy:
    """Tests for get_strategy lookup."""

    def test_returns_registered_strategy(self) -> None:
        """Registered strategy names should return the correct class."""
        cls = get_strategy("bollinger_reversion")

        assert cls is BollingerReversionStrategy

    def test_raises_for_unknown_strategy(self) -> None:
        """Unknown strategy names should raise a ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("nonexistent_strategy")

    def test_registry_contains_bollinger(self) -> None:
        """The 'bollinger_reversion' strategy should be registered."""
        assert "bollinger_reversion" in STRATEGY_REGISTRY

    def test_registry_values_are_types(self) -> None:
        """All registry values should be classes."""
        for name, cls in STRATEGY_REGISTRY.items():
            assert isinstance(cls, type), f"Registry value for '{name}' should be a class"
