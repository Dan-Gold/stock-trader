"""Unit tests for strategy registry."""

import pytest
from pydantic import BaseModel

from stock_trader.core.strategies.bollinger_reversion import BollingerParams, BollingerReversionStrategy
from stock_trader.core.strategies.registry import STRATEGY_REGISTRY, get_params_model, get_strategy


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


class TestGetParamsModel:
    """Tests for get_params_model lookup."""

    def test_returns_bollinger_params(self) -> None:
        model = get_params_model("bollinger_reversion")

        assert model is BollingerParams

    def test_raises_for_unknown_strategy(self) -> None:
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_params_model("nonexistent")

    def test_all_entries_have_base_model_params(self) -> None:
        """Every registry entry should have a params_model subclassing BaseModel."""
        for name, entry in STRATEGY_REGISTRY.items():
            assert issubclass(entry.params_model, BaseModel), f"'{name}' params_model should subclass BaseModel"
