"""Service layer for fetching and storing market data."""

import logging
from datetime import date

from stock_trader.core.market_data.providers.market_data_provider_interface import IMarketDataProvider
from stock_trader.core.market_data.providers.rate_limiter_interface import IRateLimiter
from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.db.interfaces.market_data_repo_interface import IMarketDataRepoSyncInterface
from stock_trader.models.shared_enums import IntervalEnum

logger = logging.getLogger(__name__)


class MarketDataService:
    """Orchestrates market data retrieval: DB first, provider on miss.

    Flow:
        1. Check Postgres for existing data
        2. If missing -> fetch from the provider (Massive)
        3. Save to Postgres for future requests
        4. Return OHLCVSeries

    Rate limiting is enforced before each provider call to stay within
    API quotas. Caching (Redis) can be layered on later without
    changing callers.
    """

    def __init__(
        self,
        market_data_repository: IMarketDataRepoSyncInterface,
        provider: IMarketDataProvider,
        rate_limiter: IRateLimiter | None = None,
    ) -> None:
        self.repo = market_data_repository
        self.provider = provider
        self.rate_limiter = rate_limiter

    def ensure_data(
        self,
        symbol: str,
        interval: IntervalEnum,
        start_date: date,
        end_date: date,
    ) -> OHLCVSeries:
        """Ensure OHLCV data is available in the DB, fetching if needed.

        Args:
            symbol: Ticker symbol, e.g. "AAPL".
            interval: Canonical interval enum value.
            start_date: Start date inclusive.
            end_date: End date inclusive.

        Returns:
            OHLCVSeries with bars for the requested range.

        Raises:
            ProviderError: If the external API call fails.
            ValueError: If no data is returned from either DB or provider.
        """
        # 1. Check DB
        existing = self.repo.get_ohlcv_data(symbol=symbol, start_time=start_date, end_time=end_date, interval=interval)

        if existing and len(existing) > 0:
            logger.info("DB hit: %d bars for %s (%s to %s)", len(existing), symbol, start_date, end_date)
            return existing

        # 2. DB miss -> fetch from provider
        logger.info("DB miss for %s (%s to %s), fetching from %s", symbol, start_date, end_date, self.provider.name)

        if self.rate_limiter:
            self.rate_limiter.acquire()

        series = self.provider.fetch_ohlcv(symbol=symbol, interval=interval, start_date=start_date, end_date=end_date)

        if not series or len(series) == 0:
            raise ValueError(f"No data returned for {symbol} ({start_date} to {end_date})")

        # 3. Save to DB
        self.repo.bulk_insert_market_data(series)
        logger.info("Saved %d bars for %s to DB", len(series), symbol)

        return series
