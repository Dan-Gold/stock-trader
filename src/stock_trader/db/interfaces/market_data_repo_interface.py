"""Repository for market data access."""

from datetime import date
from typing import Protocol

from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.models.shared_enums import IntervalEnum


class IMarketDataRepoSyncInterface(Protocol):
    """Sync repository for Celery worker database access."""

    def get_ohlcv_data(
        self, symbol: str, start_time: date, end_time: date, interval: IntervalEnum = IntervalEnum.ONE_MINUTE
    ) -> OHLCVSeries | None:
        """Get OHLCV market data for a symbol and time range."""
        ...

    def bulk_insert_market_data(self, data: OHLCVSeries) -> None:
        """Bulk insert market data rows."""
        ...
