"""Unit tests for MarketDataTableSchema converter methods."""

from datetime import datetime, timezone

import pytest

from stock_trader.db.models.market_data import MarketDataTableSchema
from stock_trader.models.shared_enums import IntervalEnum
from tests.helpers import make_ohlcv, make_row


class TestFromRecord:
    """Tests for MarketDataTableSchema.from_record()."""

    def test_maps_all_price_fields(self) -> None:
        """All price fields from the record should map to the OHLCV, and volume should map as well."""
        row = make_row(close=105.0)

        ohlcv = row.from_record()

        assert ohlcv.open == 105.0
        assert ohlcv.high == 106.0
        assert ohlcv.low == 104.0
        assert ohlcv.close == 105.0
        assert ohlcv.volume == 1000

    def test_maps_timestamp(self) -> None:
        """The timestamp from the record should map to the OHLCV."""
        ts = datetime(2024, 6, 15, 14, 30, tzinfo=timezone.utc)
        row = make_row(ts=ts)

        ohlcv = row.from_record()

        assert ohlcv.timestamp == ts


class TestToRecord:
    """Tests for MarketDataTableSchema.to_record()."""

    def test_maps_all_fields(self) -> None:
        """All fields from the OHLCV should map to the record, along with symbol and interval."""
        ohlcv = make_ohlcv(close=110.0)

        row = MarketDataTableSchema.to_record(ohlcv, symbol="TSLA", interval=IntervalEnum.DAILY)

        assert row.symbol == "TSLA"
        assert row.interval == IntervalEnum.DAILY
        assert row.open == 110.0
        assert row.high == 111.0
        assert row.low == 109.0
        assert row.close == 110.0
        assert row.volume == 1000

    def test_preserves_timestamp(self) -> None:
        """The timestamp from the OHLCV should map to the record."""
        ts = datetime(2024, 3, 1, 9, 30, tzinfo=timezone.utc)
        ohlcv = make_ohlcv(ts=ts)

        row = MarketDataTableSchema.to_record(ohlcv, symbol="AAPL", interval=IntervalEnum.ONE_MINUTE)

        assert row.timestamp == ts


class TestFromRecords:
    """Tests for MarketDataTableSchema.from_records()."""

    def test_converts_to_ohlcv_series(self) -> None:
        """Multiple records should be converted into an OHLCVSeries with the correct symbol, interval, and bars."""
        rows = [
            make_row(ts=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), close=100.0),
            make_row(ts=datetime(2024, 1, 1, 10, 1, tzinfo=timezone.utc), close=101.0),
        ]

        series = MarketDataTableSchema.from_records(rows)

        assert series.symbol == "AAPL"
        assert series.interval == IntervalEnum.ONE_MINUTE
        assert len(series.bars) == 2

    def test_empty_records_raises(self) -> None:
        """An empty list of records should raise a ValueError, since we can't infer symbol/interval and there's no data."""
        with pytest.raises(ValueError, match="No records"):
            MarketDataTableSchema.from_records([])

    def test_uses_first_record_symbol_and_interval(self) -> None:
        """Series symbol and interval should come from the first record."""
        rows = [
            make_row(symbol="PLTR", interval=IntervalEnum.DAILY),
        ]

        series = MarketDataTableSchema.from_records(rows)

        assert series.symbol == "PLTR"
        assert series.interval == IntervalEnum.DAILY
