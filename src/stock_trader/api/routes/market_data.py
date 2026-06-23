"""API route for fetching raw OHLCV market data for a symbol."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query

from stock_trader.api.dependencies import get_market_data_fetcher
from stock_trader.api.services.market_data_fetcher import MarketDataFetcher
from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.models.shared_enums import IntervalEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get(
    "/{symbol}",
    operation_id="get_market_data",
    summary="Fetch OHLCV market data for a symbol",
    response_model=OHLCVSeries,
)
async def get_market_data(
    symbol: str,
    start_date: date = Query(..., description="Inclusive start date (UTC)."),  # noqa: B008
    end_date: date = Query(..., description="Inclusive end date (UTC)."),  # noqa: B008
    interval: IntervalEnum = Query(IntervalEnum.ONE_MINUTE, description="Bar interval."),  # noqa: B008
    fetcher: MarketDataFetcher = Depends(get_market_data_fetcher),  # noqa: B008
) -> OHLCVSeries:
    """Return OHLCV bars for symbol. Fetch-on-miss via the fetch worker.

    Args:
        symbol: The ticker symbol.
        start_date: Inclusive start date.
        end_date: Inclusive end date.
        interval: Bar interval (defaults to 1-minute).
        fetcher: The market-data fetcher dependency.

    Returns:
        The OHLCV series; an empty series (200) if the range has no data.
    """
    return await fetcher.fetch(symbol=symbol, interval=interval, start_date=start_date, end_date=end_date)
