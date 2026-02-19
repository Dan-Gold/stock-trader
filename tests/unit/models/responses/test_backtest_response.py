"""Unit tests for BacktestResponse.from_job()."""

from datetime import datetime, timezone

from stock_trader.models.responses.backtest_response import BacktestResponse
from stock_trader.models.shared_enums import BacktestStatusEnum
from tests.helpers import make_job_schema


class TestBacktestResponseFromJob:
    """Tests for BacktestResponse.from_job() classmethod."""

    def test_maps_all_fields(self) -> None:
        """All fields from the job schema should be mapped to the response, except timestamps and error."""
        job = make_job_schema()

        response = BacktestResponse.from_job(job)

        assert response.uuid == job.uuid
        assert response.status == job.status
        assert response.strategy_name == job.strategy_name
        assert response.symbols == job.symbols
        assert response.parameters == job.parameters
        assert response.create_time == job.create_time

    def test_maps_error_field(self) -> None:
        """The error field from the job schema should be mapped to the response."""
        job = make_job_schema(status=BacktestStatusEnum.FAILED, error="something broke")

        response = BacktestResponse.from_job(job)

        assert response.error == "something broke"

    def test_maps_timestamps(self) -> None:
        """The start_time and end_time from the job schema should be mapped to the response, even if they are None."""
        now = datetime.now(timezone.utc)
        job = make_job_schema(
            status=BacktestStatusEnum.COMPLETED,
            start_time=now,
            end_time=now,
        )

        response = BacktestResponse.from_job(job)

        assert response.start_time == now
        assert response.end_time == now

    def test_none_timestamps_when_not_started(self) -> None:
        """If the job has not started, start_time and end_time should be None."""
        job = make_job_schema()

        response = BacktestResponse.from_job(job)

        assert response.start_time is None
        assert response.end_time is None
        assert response.error is None
