"""Unit tests for BacktestCreateRequest validators."""

from datetime import date

import pytest
from pydantic import ValidationError

from stock_trader.models.backtest_create_request import BacktestCreateRequest


class TestBacktestCreateRequestValidation:
    """Tests for BacktestCreateRequest field and model validators."""

    def test_valid_request(self) -> None:
        """A valid request should pass all validations and create an instance."""
        req = BacktestCreateRequest(
            strategy_name="bollinger_reversion",
            symbols=["AAPL"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert req.strategy_name == "bollinger_reversion"

    def test_end_date_before_start_date_raises(self) -> None:
        """An end_date before start_date should raise a ValidationError."""
        with pytest.raises(ValidationError, match="end_date cannot be before start_date"):
            BacktestCreateRequest(
                strategy_name="bollinger_reversion",
                symbols=["AAPL"],
                start_date=date(2024, 6, 30),
                end_date=date(2024, 1, 1),
            )

    def test_same_start_and_end_date_is_valid(self) -> None:
        """A request with the same start_date and end_date should be valid."""
        req = BacktestCreateRequest(
            strategy_name="bollinger_reversion",
            symbols=["AAPL"],
            start_date=date(2024, 3, 15),
            end_date=date(2024, 3, 15),
        )

        assert req.start_date == req.end_date

    def test_unknown_strategy_raises(self) -> None:
        """An unknown strategy should raise a ValidationError."""
        with pytest.raises(ValidationError, match="Unknown strategy"):
            BacktestCreateRequest(
                strategy_name="nonexistent_strategy",
                symbols=["AAPL"],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

    def test_empty_symbols_raises(self) -> None:
        """An empty symbols list should raise a ValidationError."""
        with pytest.raises(ValidationError):
            BacktestCreateRequest(
                strategy_name="bollinger_reversion",
                symbols=[],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

    def test_strategy_name_exceeds_max_length_raises(self) -> None:
        """A strategy_name longer than 50 chars should raise a ValidationError."""
        with pytest.raises(ValidationError, match="String should have at most 50 characters"):
            BacktestCreateRequest(
                strategy_name="a" * 51,
                symbols=["AAPL"],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

    def test_parameters_rejects_nested_dict(self) -> None:
        """Nested dicts are not valid parameter values."""
        with pytest.raises(ValidationError):
            BacktestCreateRequest(
                strategy_name="bollinger_reversion",
                symbols=["AAPL"],
                parameters={"nested": {"inner": 1}},
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

    def test_parameters_rejects_list_value(self) -> None:
        """Lists are not valid parameter values."""
        with pytest.raises(ValidationError):
            BacktestCreateRequest(
                strategy_name="bollinger_reversion",
                symbols=["AAPL"],
                parameters={"some_list": [1, 2, 3]},
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

    def test_parameters_accepts_valid_types(self) -> None:
        """str, int, float, and bool parameter values should all be accepted."""
        req = BacktestCreateRequest(
            strategy_name="bollinger_reversion",
            symbols=["AAPL"],
            parameters={"length": 20, "std_dev": 2.0, "exit_at": "middle"},
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert req.parameters["length"] == 20


class TestParameterValidation:
    """Tests for strategy-specific parameter validation at request time."""

    def test_unknown_param_key_raises(self) -> None:
        """A parameter key unknown to the strategy should raise ValidationError."""
        with pytest.raises(ValidationError, match="Extra inputs"):
            BacktestCreateRequest(
                strategy_name="bollinger_reversion",
                symbols=["AAPL"],
                parameters={"length": 20, "unknown_key": 42},
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

    def test_out_of_range_length_raises(self) -> None:
        """A length below the minimum should fail validation."""
        with pytest.raises(ValidationError, match="greater than or equal to 5"):
            BacktestCreateRequest(
                strategy_name="bollinger_reversion",
                symbols=["AAPL"],
                parameters={"length": 2},
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

    def test_invalid_exit_at_raises(self) -> None:
        with pytest.raises(ValidationError, match="Input should be 'middle' or 'upper'"):
            BacktestCreateRequest(
                strategy_name="bollinger_reversion",
                symbols=["AAPL"],
                parameters={"exit_at": "invalid"},
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

    def test_empty_params_uses_defaults(self) -> None:
        """Empty params dict should be accepted (strategy uses defaults)."""
        req = BacktestCreateRequest(
            strategy_name="bollinger_reversion",
            symbols=["AAPL"],
            parameters={},
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert req.parameters == {}
