"""Route-level tests for GET /market-data/{symbol}.

Drives the real route through ``add_exception_handlers`` with the fetcher
dependency overridden, pinning the HTTP status mapping end-to-end (200 / empty
200 / 400 / 504) — the proof for the H1 fix and the 400/504 wiring that the
fetcher/task unit tests don't exercise. Builds a minimal app rather than
importing ``api_server`` (which reads full config at import).
"""

from datetime import date

from celery.exceptions import TimeoutError as CeleryTimeoutError
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stock_trader.api.dependencies import get_market_data_fetcher
from stock_trader.api.exception_handlers import add_exception_handlers
from stock_trader.api.routes.market_data import router as market_data_router
from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.models.exceptions import RangeValidationError
from stock_trader.models.shared_enums import IntervalEnum
from tests.helpers import make_ohlcv_series

_QUERY = {"start_date": "2026-06-15", "end_date": "2026-06-16", "interval": "1min"}


class _FakeFetcher:
    """Stand-in for MarketDataFetcher: returns a result or raises an exception."""

    def __init__(self, *, result: OHLCVSeries | None = None, exc: Exception | None = None) -> None:
        self._result = result
        self._exc = exc

    async def fetch(self, *, symbol: str, interval: IntervalEnum, start_date: date, end_date: date) -> OHLCVSeries:
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


def _client(*, result: OHLCVSeries | None = None, exc: Exception | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(market_data_router)
    add_exception_handlers(app)
    app.dependency_overrides[get_market_data_fetcher] = lambda: _FakeFetcher(result=result, exc=exc)
    return TestClient(app)


class TestMarketDataRoute:
    """HTTP status mapping for the market-data endpoint."""

    def test_returns_200_with_series(self) -> None:
        """A populated series serializes to 200 with bars."""
        series = make_ohlcv_series()
        resp = _client(result=series).get("/market-data/AAPL", params=_QUERY)

        assert resp.status_code == 200
        body = resp.json()
        assert body["symbol"] == series.symbol
        assert len(body["bars"]) == len(series)

    def test_no_data_returns_200_empty(self) -> None:
        """No data is a valid 200 with an empty bars list, not an error."""
        empty = OHLCVSeries(symbol="AAPL", interval=IntervalEnum.ONE_MINUTE, bars=[])
        resp = _client(result=empty).get("/market-data/AAPL", params=_QUERY)

        assert resp.status_code == 200
        assert resp.json()["bars"] == []

    def test_range_validation_returns_400(self) -> None:
        """RangeValidationError maps to 400 via add_exception_handlers."""
        resp = _client(exc=RangeValidationError("start_date must be <= end_date")).get(
            "/market-data/AAPL", params=_QUERY
        )

        assert resp.status_code == 400
        assert "start_date" in resp.json()["detail"]

    def test_result_timeout_returns_504(self) -> None:
        """celery.exceptions.TimeoutError maps to 504 (not the generic 500)."""
        resp = _client(exc=CeleryTimeoutError("worker result not ready")).get("/market-data/AAPL", params=_QUERY)

        assert resp.status_code == 504
