"""Unit tests for OHLCVSeries and OHLCV models."""

from datetime import datetime, timezone

import pandas as pd

from tests.helpers import make_ohlcv_bar, make_ohlcv_series


class TestOHLCVSeriesDunders:
    """Tests for __bool__ and __len__."""

    def test_bool_true_with_bars(self) -> None:
        """An OHLCVSeries with bars should evaluate to True in a boolean context."""
        assert bool(make_ohlcv_series()) is True

    def test_bool_false_when_empty(self) -> None:
        """An empty OHLCVSeries should evaluate to False in a boolean context."""
        assert bool(make_ohlcv_series(bars=[])) is False

    def test_len_matches_bar_count(self) -> None:
        """The length of the OHLCVSeries should match the number of bars it contains."""
        assert len(make_ohlcv_series()) == 3

    def test_len_zero_when_empty(self) -> None:
        """An empty OHLCVSeries should have a length of zero."""
        assert len(make_ohlcv_series(bars=[])) == 0


class TestToDataframe:
    """Tests for OHLCVSeries.to_dataframe()."""

    def test_returns_expected_columns(self) -> None:
        """Core OHLCV columns should always be present."""
        df = make_ohlcv_series().to_dataframe()

        for col in ("open", "high", "low", "close", "volume"):
            assert col in df.columns

    def test_index_is_timestamp(self) -> None:
        """The index of the dataframe should be the timestamp."""
        df = make_ohlcv_series().to_dataframe()

        assert df.index.name == "timestamp"

    def test_index_is_tz_aware(self) -> None:
        """The index must stay tz-aware so downstream market-hours gating is correct.

        A tz-naive index would be misread as system-local time by the session
        gate (see core.utils.regular_session_mask).
        """
        df = make_ohlcv_series().to_dataframe()

        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.tz is not None

    def test_rows_match_bar_count(self) -> None:
        """The number of rows in the dataframe should match the number of bars."""
        df = make_ohlcv_series().to_dataframe()

        assert len(df) == 3

    def test_sorted_by_timestamp(self) -> None:
        """Bars should be sorted ascending by timestamp regardless of input order."""
        bars = [
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 2, tzinfo=timezone.utc), close=102.0),
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), close=100.0),
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 1, tzinfo=timezone.utc), close=101.0),
        ]
        df = make_ohlcv_series(bars).to_dataframe()

        assert list(df["close"]) == [100.0, 101.0, 102.0]

    def test_drops_vwap_when_all_null(self) -> None:
        """If every bar has vwap=None, the column should be dropped."""
        df = make_ohlcv_series().to_dataframe()

        assert "vwap" not in df.columns

    def test_keeps_vwap_when_present(self) -> None:
        """If any bar has a vwap value, the column should remain."""
        bars = [
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), vwap=99.5),
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 1, tzinfo=timezone.utc), vwap=None),
        ]
        df = make_ohlcv_series(bars).to_dataframe()

        assert "vwap" in df.columns

    def test_drops_transactions_when_all_null(self) -> None:
        """If every bar has transactions=None, the column should be dropped."""
        df = make_ohlcv_series().to_dataframe()

        assert "transactions" not in df.columns

    def test_keeps_transactions_when_present(self) -> None:
        """If any bar has a transactions value, the column should remain."""
        bars = [
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), transactions=50),
            make_ohlcv_bar(datetime(2024, 1, 1, 10, 1, tzinfo=timezone.utc), transactions=None),
        ]
        df = make_ohlcv_series(bars).to_dataframe()

        assert "transactions" in df.columns
