"""Service layer for the market-data fetch endpoint.

Validates the requested range, dispatches the symbol-scoped
``ensure_market_data_for_symbol`` Celery task, and awaits the result. The
blocking ``AsyncResult.get`` is run off
the event loop with a bounded timeout; on timeout the task keeps running and the
caller gets a 504.
"""

import logging
import time
from datetime import date

from celery.exceptions import TimeoutError as CeleryTimeoutError
from fastapi.concurrency import run_in_threadpool

from stock_trader.core.market_data.market_data_tasks import ensure_market_data_for_symbol
from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.models.exceptions import RangeValidationError
from stock_trader.models.shared_enums import IntervalEnum

logger = logging.getLogger(__name__)

# Max span per interval, keeping each request well under the provider's
# single-page limit. Tunable starting values.
_MAX_SPAN_DAYS: dict[IntervalEnum, int] = {
    IntervalEnum.ONE_MINUTE: 30,
    IntervalEnum.FIVE_MINUTE: 60,
    IntervalEnum.FIFTEEN_MINUTE: 120,
    IntervalEnum.THIRTY_MINUTE: 180,
    IntervalEnum.ONE_HOUR: 365,
    IntervalEnum.DAILY: 1825,
}


class MarketDataFetcher:
    """Validate the request, dispatch the fetch task, await the series."""

    def __init__(self, result_timeout: float) -> None:
        self._timeout = result_timeout

    async def fetch(self, *, symbol: str, interval: IntervalEnum, start_date: date, end_date: date) -> OHLCVSeries:
        """Fetch OHLCV bars for symbol over the range, fetch-on-miss.

        Args:
            symbol: The ticker symbol.
            interval: The bar interval.
            start_date: Inclusive start date.
            end_date: Inclusive end date.

        Returns:
            The OHLCV series (possibly empty if the range has no data).

        Raises:
            RangeValidationError: If the symbol is empty or the range is invalid
                / exceeds the cap.
            celery.exceptions.TimeoutError: If the worker result is not ready
                within result_timeout.
        """
        symbol = symbol.strip().upper()
        if not symbol:
            raise RangeValidationError("symbol must not be empty")
        if start_date > end_date:
            raise RangeValidationError("start_date must be <= end_date")
        span = (end_date - start_date).days
        cap = _MAX_SPAN_DAYS.get(interval)
        if cap is None:
            # Server-side config gap: an IntervalEnum member without a cap entry.
            # Surface as a 500 (generic handler) rather than the misleading
            # KeyError -> 404. Guarded against by test_every_interval_has_a_cap.
            raise RuntimeError(f"No span cap configured for interval {interval.value}")
        if span > cap:
            raise RangeValidationError(f"Requested span {span}d exceeds max {cap}d for interval {interval.value}")

        async_result = ensure_market_data_for_symbol.delay(symbol, interval.value, start_date.isoformat(), end_date.isoformat())

        # AsyncResult.get blocks; run it off the event loop with a timeout.
        started = time.monotonic()
        try:
            payload = await run_in_threadpool(async_result.get, timeout=self._timeout)
        except CeleryTimeoutError:
            logger.warning(
                "market-data wait timed out after %.1fs: symbol=%s interval=%s span=%dd",
                time.monotonic() - started,
                symbol,
                interval.value,
                span,
            )
            raise

        logger.info(
            "market-data served in %.1fs: symbol=%s interval=%s bars=%d",
            time.monotonic() - started,
            symbol,
            interval.value,
            len(payload.get("bars", [])),
        )
        return OHLCVSeries.model_validate(payload)
