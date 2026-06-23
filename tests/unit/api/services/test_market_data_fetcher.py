"""Unit tests for MarketDataFetcher (range validation + dispatch/await)."""

from datetime import date
from unittest.mock import MagicMock

import pytest
from celery.exceptions import TimeoutError as CeleryTimeoutError

from stock_trader.api.services import market_data_fetcher as fetcher_module
from stock_trader.api.services.market_data_fetcher import MarketDataFetcher
from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.models.exceptions import RangeValidationError
from stock_trader.models.shared_enums import IntervalEnum
from tests.helpers import make_ohlcv_series

# asyncio_mode = "auto" (pyproject) auto-marks the async tests; no module-level
# pytest.mark.asyncio so the one sync test (test_every_interval_has_a_cap) isn't
# falsely marked async.


def _patch_task(monkeypatch: pytest.MonkeyPatch, *, result: object = None, raises: Exception | None = None) -> MagicMock:
    """Patch ensure_market_data_for_symbol.delay to return a fake AsyncResult."""
    async_result = MagicMock()
    if raises is not None:
        async_result.get.side_effect = raises
    else:
        async_result.get.return_value = result
    task = MagicMock()
    task.delay.return_value = async_result
    monkeypatch.setattr(fetcher_module, "ensure_market_data_for_symbol", task)
    return task


class TestRangeValidation:
    """start_date/end_date and per-interval span caps."""

    async def test_start_after_end_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """start_date later than end_date is rejected before dispatch."""
        _patch_task(monkeypatch)
        fetcher = MarketDataFetcher(result_timeout=1.0)

        with pytest.raises(RangeValidationError):
            await fetcher.fetch(
                symbol="AAPL",
                interval=IntervalEnum.ONE_MINUTE,
                start_date=date(2024, 2, 1),
                end_date=date(2024, 1, 1),
            )

    async def test_span_over_cap_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A 1-minute span beyond the 30-day cap is rejected."""
        _patch_task(monkeypatch)
        fetcher = MarketDataFetcher(result_timeout=1.0)

        with pytest.raises(RangeValidationError):
            await fetcher.fetch(
                symbol="AAPL",
                interval=IntervalEnum.ONE_MINUTE,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 1),  # 60 days > 30
            )

    async def test_span_at_cap_is_allowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A span exactly equal to the cap dispatches and returns."""
        payload = make_ohlcv_series().model_dump(mode="json")
        task = _patch_task(monkeypatch, result=payload)
        fetcher = MarketDataFetcher(result_timeout=1.0)

        result = await fetcher.fetch(
            symbol="AAPL",
            interval=IntervalEnum.ONE_MINUTE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),  # 30 days == cap
        )

        assert isinstance(result, OHLCVSeries)
        task.delay.assert_called_once()

    def test_every_interval_has_a_cap(self) -> None:
        """Every IntervalEnum member must have a span cap (guards M1).

        Without this, a future enum member would hit a KeyError that the global
        handler maps to a misleading 404 instead of a server 500.
        """
        missing = set(IntervalEnum) - set(fetcher_module._MAX_SPAN_DAYS)
        assert not missing, f"IntervalEnum members missing a _MAX_SPAN_DAYS cap: {missing}"


class TestSymbolValidation:
    """Symbol normalization and emptiness."""

    async def test_empty_symbol_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A blank/whitespace symbol is rejected before dispatch."""
        task = _patch_task(monkeypatch)
        fetcher = MarketDataFetcher(result_timeout=1.0)

        with pytest.raises(RangeValidationError):
            await fetcher.fetch(
                symbol="   ",
                interval=IntervalEnum.ONE_MINUTE,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 2),
            )
        task.delay.assert_not_called()

    async def test_symbol_is_normalized(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Symbol is upper-cased and trimmed before dispatch (cache-key hygiene)."""
        task = _patch_task(monkeypatch, result=make_ohlcv_series().model_dump(mode="json"))
        fetcher = MarketDataFetcher(result_timeout=1.0)

        await fetcher.fetch(
            symbol="  aapl  ",
            interval=IntervalEnum.ONE_MINUTE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
        )

        task.delay.assert_called_once_with("AAPL", "1min", "2024-01-01", "2024-01-02")


class TestFetch:
    """Dispatch and await behaviour."""

    async def test_returns_series_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A successful task result is deserialized into an OHLCVSeries."""
        series = make_ohlcv_series()
        task = _patch_task(monkeypatch, result=series.model_dump(mode="json"))
        fetcher = MarketDataFetcher(result_timeout=5.0)

        result = await fetcher.fetch(
            symbol="AAPL",
            interval=IntervalEnum.ONE_MINUTE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
        )

        assert isinstance(result, OHLCVSeries)
        assert len(result) == len(series)
        task.delay.assert_called_once_with("AAPL", "1min", "2024-01-01", "2024-01-02")
        task.delay.return_value.get.assert_called_once_with(timeout=5.0)

    async def test_empty_series_passes_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A no-data (empty) result is returned as an empty series, not an error."""
        empty = OHLCVSeries(symbol="AAPL", interval=IntervalEnum.ONE_MINUTE, bars=[])
        _patch_task(monkeypatch, result=empty.model_dump(mode="json"))
        fetcher = MarketDataFetcher(result_timeout=5.0)

        result = await fetcher.fetch(
            symbol="AAPL",
            interval=IntervalEnum.ONE_MINUTE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
        )

        assert len(result) == 0

    async def test_timeout_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A worker result timeout surfaces as CeleryTimeoutError (-> 504)."""
        _patch_task(monkeypatch, raises=CeleryTimeoutError("not ready"))
        fetcher = MarketDataFetcher(result_timeout=0.5)

        with pytest.raises(CeleryTimeoutError):
            await fetcher.fetch(
                symbol="AAPL",
                interval=IntervalEnum.ONE_MINUTE,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 2),
            )
