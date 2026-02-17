"""Base protocol for market data providers."""

from datetime import date
from typing import Protocol

from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.models.shared_enums import IntervalEnum


class IMarketDataProvider(Protocol):
    """Protocol that all market data providers must satisfy.

    Each provider adapts a single external API (Massive, Alpha Vantage, etc.)
    into the canonical OHLCVSeries domain model. Providers are responsible for:
        - Translating IntervalEnum into the API's native interval format
        - Handling HTTP transport and response parsing
        - Raising ProviderError on any failure (network, auth, rate-limit, etc.)

    Providers should NOT handle:
        - Caching (that's CachedMarketDataRepository)
        - Persistence (that's MarketDataRepositorySync)
        - Rate limiting (that's the service layer)
    """

    name: str

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: IntervalEnum,
        start_date: date,
        end_date: date,
    ) -> OHLCVSeries:
        """Fetch OHLCV bars from the external API.

        Args:
            symbol: Ticker symbol, e.g. "AAPL".
            interval: Canonical interval enum value.
            start_date: Start date inclusive.
            end_date: End date inclusive.

        Returns:
            OHLCVSeries with bars sorted by timestamp ascending.

        Raises:
            ProviderError: On any failure from the external API.
        """
        ...


class ProviderError(Exception):
    """Raised when a market data provider fails.

    Wraps any provider-specific error (network, auth, rate-limit, bad response)
    into a single exception type so callers don't need to know which provider
    was used.
    """

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")

    def __reduce__(self) -> tuple:
        """Make ProviderError picklable for Celery serialization."""
        return (self.__class__, (self.provider, self.message))
