"""Massive (formerly Polygon.io) market data provider."""

import logging
from datetime import date

from massive import RESTClient

from stock_trader.core.market_data.providers.market_data_provider_interface import ProviderError
from stock_trader.core.market_data.providers.massive.mapper import aggs_to_ohlcv_series
from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.models.shared_enums import IntervalEnum

logger = logging.getLogger(__name__)

# Maps our canonical IntervalEnum -> Massive API (multiplier, timespan) params
_INTERVAL_MAP: dict[IntervalEnum, tuple[int, str]] = {
    IntervalEnum.ONE_MINUTE: (1, "minute"),
    IntervalEnum.FIVE_MINUTE: (5, "minute"),
    IntervalEnum.FIFTEEN_MINUTE: (15, "minute"),
    IntervalEnum.THIRTY_MINUTE: (30, "minute"),
    IntervalEnum.ONE_HOUR: (1, "hour"),
    IntervalEnum.DAILY: (1, "day"),
}

# Massive free-tier max results per page
_DEFAULT_LIMIT = 50_000


class MassiveProvider:
    """Fetches OHLCV bars from the Massive (formerly Polygon.io) REST API.

    Uses the official ``massive`` Python client to call the Aggregates (Bars)
    endpoint. The client handles pagination automatically.

    Args:
        api_key: Massive API key.
    """

    name: str = "massive"

    def __init__(self, api_key: str) -> None:
        self._client = RESTClient(api_key=api_key)

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: IntervalEnum,
        start_date: date,
        end_date: date,
    ) -> OHLCVSeries:
        """Fetch OHLCV bars from Massive.

        Args:
            symbol: Ticker symbol, e.g. "AAPL".
            interval: Canonical interval enum value.
            start_date: Start date inclusive.
            end_date: End date inclusive.

        Returns:
            OHLCVSeries with bars sorted by timestamp ascending.

        Raises:
            ProviderError: On any failure from the Massive API.
        """
        multiplier, timespan = self._resolve_interval(interval)

        logger.info("Fetching %s %s bars for %s (%s to %s)", interval.value, symbol, symbol, start_date, end_date)

        try:
            aggs = self._client.list_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_=start_date.isoformat(),
                to=end_date.isoformat(),
                limit=_DEFAULT_LIMIT,
            )

            series = aggs_to_ohlcv_series(aggs, symbol, multiplier, timespan)

        except Exception as exc:
            raise ProviderError(self.name, f"Failed to fetch {symbol}: {exc}") from exc

        logger.info("Fetched %d bars for %s", len(series), symbol)
        return series

    @staticmethod
    def _resolve_interval(interval: IntervalEnum) -> tuple[int, str]:
        """Convert IntervalEnum to Massive (multiplier, timespan) tuple."""
        result = _INTERVAL_MAP.get(interval)
        if result is None:
            raise ProviderError("massive", f"Unsupported interval: {interval}")
        return result
