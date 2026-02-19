"""Unit tests for BacktestJobTableSchema.from_request()."""

from datetime import date

from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.backtest_create_request import BacktestCreateRequest


class TestFromRequest:
    """Tests for BacktestJobTableSchema.from_request()."""

    def test_maps_all_request_fields(self) -> None:
        """from_request should copy strategy, symbols, parameters, and dates."""
        request = BacktestCreateRequest(
            strategy_name="bollinger_reversion",
            symbols=["AAPL", "TSLA"],
            parameters={"length": 20, "std_dev": 2.0},
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        job = BacktestJobTableSchema.from_request(request)

        assert job.strategy_name == "bollinger_reversion"
        assert job.symbols == ["AAPL", "TSLA"]
        assert job.parameters == {"length": 20, "std_dev": 2.0}
        assert job.start_date == date(2024, 1, 1)
        assert job.end_date == date(2024, 6, 30)

    def test_sets_default_status(self) -> None:
        """A newly created job from a request should not have a pre-set status.

        In production the repository layer sets the status; from_request
        only maps the user-supplied fields.
        """
        request = BacktestCreateRequest(
            strategy_name="bollinger_reversion",
            symbols=["AAPL"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        job = BacktestJobTableSchema.from_request(request)

        # status is not set by from_request, it's typically set by the repo
        # The column is non-nullable so it'll be None until persisted
        assert job.status is None

    def test_empty_parameters_default(self) -> None:
        """When no parameters are provided, the dict should be empty."""
        request = BacktestCreateRequest(
            strategy_name="bollinger_reversion",
            symbols=["AAPL"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        job = BacktestJobTableSchema.from_request(request)

        assert job.parameters == {}

    def test_timestamps_not_set(self) -> None:
        """from_request should not set start_time, end_time, or error."""
        request = BacktestCreateRequest(
            strategy_name="bollinger_reversion",
            symbols=["AAPL"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        job = BacktestJobTableSchema.from_request(request)

        assert job.start_time is None
        assert job.end_time is None
        assert job.error is None
