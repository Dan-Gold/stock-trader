"""Unit tests for shared utility functions."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from stock_trader.core.utils import is_regular_session, regular_session_mask

ET = ZoneInfo("America/New_York")


class TestIsRegularSession:
    """Tests for is_regular_session (scalar session rule)."""

    @pytest.mark.parametrize(
        ("ts", "expected"),
        [
            (datetime(2024, 1, 2, 9, 0, tzinfo=ET), False),  # pre-market
            (datetime(2024, 1, 2, 9, 30, tzinfo=ET), True),  # open (inclusive)
            (datetime(2024, 1, 2, 12, 0, tzinfo=ET), True),  # mid-session
            (datetime(2024, 1, 2, 15, 59, tzinfo=ET), True),  # last minute
            (datetime(2024, 1, 2, 16, 0, tzinfo=ET), False),  # close (exclusive)
            (datetime(2024, 1, 2, 18, 0, tzinfo=ET), False),  # after-hours
        ],
    )
    def test_session_boundaries(self, ts: datetime, expected: bool) -> None:
        """The session is 09:30 inclusive to 16:00 exclusive, ET."""
        assert is_regular_session(ts) is expected

    def test_dst_winter_open_from_utc(self) -> None:
        """In winter (EST, UTC-5), 14:30 UTC is 09:30 ET -> in session."""
        assert is_regular_session(datetime(2024, 1, 2, 14, 30, tzinfo=UTC)) is True
        assert is_regular_session(datetime(2024, 1, 2, 14, 29, tzinfo=UTC)) is False

    def test_dst_summer_open_from_utc(self) -> None:
        """In summer (EDT, UTC-4), 13:30 UTC is 09:30 ET -> in session."""
        assert is_regular_session(datetime(2024, 7, 2, 13, 30, tzinfo=UTC)) is True
        assert is_regular_session(datetime(2024, 7, 2, 13, 29, tzinfo=UTC)) is False

    def test_naive_datetime_raises(self) -> None:
        """A tz-naive datetime must raise rather than silently mis-gate."""
        with pytest.raises(ValueError, match="tz-aware"):
            is_regular_session(datetime(2024, 1, 2, 10, 0))


class TestRegularSessionMask:
    """Tests for regular_session_mask (vectorized session rule)."""

    def test_mask_marks_in_session_bars(self) -> None:
        """The mask is True only for timestamps inside the regular session."""
        index = pd.DatetimeIndex(
            [
                datetime(2024, 1, 2, 14, 0, tzinfo=UTC),  # 09:00 ET pre-market
                datetime(2024, 1, 2, 14, 30, tzinfo=UTC),  # 09:30 ET open
                datetime(2024, 1, 2, 18, 0, tzinfo=UTC),  # 13:00 ET mid
                datetime(2024, 1, 2, 21, 0, tzinfo=UTC),  # 16:00 ET close
                datetime(2024, 1, 2, 22, 0, tzinfo=UTC),  # 17:00 ET after-hours
            ]
        )

        assert list(regular_session_mask(index)) == [False, True, True, False, False]

    def test_mask_aligns_and_matches_scalar(self) -> None:
        """The vectorized mask agrees with the scalar helper, position by position."""
        index = pd.date_range("2024-01-02 04:00", periods=24, freq="h", tz=ET)

        mask = regular_session_mask(index)

        assert len(mask) == len(index)
        assert list(mask) == [is_regular_session(ts) for ts in index]

    def test_naive_index_raises(self) -> None:
        """A tz-naive index must raise rather than silently mis-gate."""
        index = pd.DatetimeIndex([datetime(2024, 1, 2, 14, 30)])

        with pytest.raises(ValueError, match="tz-aware"):
            regular_session_mask(index)
