"""Shared utility functions for the stock trader application."""

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

import numpy as np
import numpy.typing as npt
import pandas as pd

# US equity regular trading session, defined in market-local time. zoneinfo
# resolves DST automatically; market holidays and early-close days are not modelled.
_MARKET_TZ = ZoneInfo("America/New_York")
_MARKET_OPEN = time(9, 30)
_MARKET_CLOSE = time(16, 0)


def get_utc_now() -> datetime:
    """Get the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=UTC)


def is_regular_session(ts: datetime) -> bool:
    """Return whether a timestamp falls within the regular US trading session.

    The regular session is 09:30 (inclusive) to 16:00 (exclusive) ET. Holidays
    and early-close days are not considered.

    Args:
        ts: A timezone-aware datetime.

    Returns:
        True if ``ts`` is within the regular session.

    Raises:
        ValueError: If ``ts`` is tz-naive. A naive value would be interpreted as
            system-local time and silently mis-gate on a non-UTC host.
    """
    if ts.tzinfo is None:
        raise ValueError("is_regular_session requires a tz-aware datetime")
    local_time = ts.astimezone(_MARKET_TZ).time()
    return _MARKET_OPEN <= local_time < _MARKET_CLOSE


def regular_session_mask(index: pd.DatetimeIndex) -> npt.NDArray[np.bool_]:
    """Build a boolean mask marking which timestamps are in the regular session.

    Vectorized counterpart to :func:`is_regular_session`, so a strategy can gate
    a whole DataFrame in one pass. See that function for the session definition
    and DST handling.

    Args:
        index: A timezone-aware DatetimeIndex.

    Returns:
        A boolean array, aligned positionally with ``index``, True where the
        timestamp falls within the regular session.

    Raises:
        ValueError: If ``index`` is tz-naive.
    """
    if index.tz is None:
        raise ValueError("regular_session_mask requires a tz-aware DatetimeIndex")
    local_times = index.tz_convert(_MARKET_TZ).time
    return np.asarray((local_times >= _MARKET_OPEN) & (local_times < _MARKET_CLOSE), dtype=bool)
