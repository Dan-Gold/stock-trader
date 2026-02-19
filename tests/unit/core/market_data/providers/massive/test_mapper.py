"""Unit tests for Massive API -> OHLCV mapper functions."""

import pytest

from stock_trader.core.market_data.providers.massive.mapper import (
    agg_to_ohlcv,
    aggs_to_ohlcv_series,
    resolve_interval,
)
from stock_trader.models.shared_enums import IntervalEnum
from tests.helpers import make_agg


class TestResolveInterval:
    """Tests for resolve_interval."""

    def test_one_minute(self) -> None:
        """(1, "minute") should resolve to IntervalEnum.ONE_MINUTE."""
        assert resolve_interval(1, "minute") == IntervalEnum.ONE_MINUTE

    def test_five_minute(self) -> None:
        """(5, "minute") should resolve to IntervalEnum.FIVE_MINUTE."""
        assert resolve_interval(5, "minute") == IntervalEnum.FIVE_MINUTE

    def test_daily(self) -> None:
        """(1, "day") should resolve to IntervalEnum.DAILY."""
        assert resolve_interval(1, "day") == IntervalEnum.DAILY

    def test_unsupported_raises(self) -> None:
        """Unsupported intervals should raise a ValueError."""
        with pytest.raises(ValueError, match="Unsupported Massive interval"):
            resolve_interval(3, "minute")

    def test_unknown_timespan_raises(self) -> None:
        """Unknown timespans should raise a ValueError."""
        with pytest.raises(ValueError, match="Unsupported Massive interval"):
            resolve_interval(1, "week")


class TestAggToOhlcv:
    """Tests for agg_to_ohlcv."""

    def test_maps_price_fields(self) -> None:
        """Agg open/high/low/close should map to OHLCV open/high/low/close."""
        agg = make_agg(open=100.0, high=105.0, low=95.0, close=102.0)

        ohlcv = agg_to_ohlcv(agg)

        assert ohlcv.open == 100.0
        assert ohlcv.high == 105.0
        assert ohlcv.low == 95.0
        assert ohlcv.close == 102.0

    def test_converts_timestamp_from_ms(self) -> None:
        """Massive timestamps are epoch milliseconds -> should become UTC datetime."""
        agg = make_agg(timestamp=1_704_067_200_000)  # 2024-01-01 00:00:00 UTC

        ohlcv = agg_to_ohlcv(agg)

        assert ohlcv.timestamp.year == 2024
        assert ohlcv.timestamp.month == 1
        assert ohlcv.timestamp.day == 1

    def test_volume_cast_to_int(self) -> None:
        """Massive volume is a float, mapper should cast to int."""
        agg = make_agg(volume=50000.0)

        ohlcv = agg_to_ohlcv(agg)

        assert isinstance(ohlcv.volume, int)
        assert ohlcv.volume == 50000

    def test_vwap_none_passthrough(self) -> None:
        """Massive vwap can be None, should stay None in OHLCV."""
        agg = make_agg(vwap=None)

        ohlcv = agg_to_ohlcv(agg)

        assert ohlcv.vwap is None

    def test_transactions_none_passthrough(self) -> None:
        """Massive transactions can be None, should stay None in OHLCV."""
        agg = make_agg(transactions=None)

        ohlcv = agg_to_ohlcv(agg)

        assert ohlcv.transactions is None


class TestAggsToOhlcvSeries:
    """Tests for aggs_to_ohlcv_series."""

    def test_creates_series_with_correct_symbol(self) -> None:
        """The resulting OHLCVSeries should have the symbol passed to the mapper."""
        aggs = [make_agg(), make_agg(timestamp=1_704_067_260_000)]

        series = aggs_to_ohlcv_series(aggs, symbol="PLTR", multiplier=1, timespan="minute")

        assert series.symbol == "PLTR"
        assert series.interval == IntervalEnum.ONE_MINUTE
        assert len(series.bars) == 2

    def test_empty_aggs_produces_empty_series(self) -> None:
        """An empty list of Aggs should produce an empty OHLCVSeries."""
        series = aggs_to_ohlcv_series([], symbol="AAPL", multiplier=1, timespan="day")

        assert len(series.bars) == 0
        assert series.interval == IntervalEnum.DAILY

    def test_unsupported_interval_raises(self) -> None:
        """An unsupported interval should raise a ValueError."""
        with pytest.raises(ValueError, match="Unsupported Massive interval"):
            aggs_to_ohlcv_series([make_agg()], symbol="AAPL", multiplier=2, timespan="hour")
