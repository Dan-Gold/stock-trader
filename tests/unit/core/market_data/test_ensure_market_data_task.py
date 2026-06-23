"""Unit tests for the ensure_market_data_for_symbol Celery task."""

from unittest.mock import MagicMock

import pytest
from redis.exceptions import RedisError

from stock_trader.core.market_data import market_data_tasks as task_module
from stock_trader.core.market_data.market_data_service import NoDataError
from stock_trader.core.market_data.market_data_tasks import ensure_market_data_for_symbol
from tests.helpers import make_ohlcv_series


def _patch_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ensure_data_return: object = None,
    ensure_data_raises: Exception | None = None,
) -> MagicMock:
    """Patch _build_market_data_service to return a fake service."""
    service = MagicMock()
    if ensure_data_raises is not None:
        service.ensure_data.side_effect = ensure_data_raises
    else:
        service.ensure_data.return_value = ensure_data_return
    monkeypatch.setattr(task_module, "_build_market_data_service", lambda: service)
    return service


class TestEnsureMarketDataTask:
    """Behaviour of the symbol-scoped fetch task."""

    def test_serializes_series(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A successful fetch returns the series as JSON-serializable dict."""
        series = make_ohlcv_series()
        _patch_service(monkeypatch, ensure_data_return=series)

        result = ensure_market_data_for_symbol("AAPL", "1min", "2024-01-01", "2024-01-02")

        assert result == series.model_dump(mode="json")

    def test_no_data_returns_empty_series(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NoDataError yields an empty series, not a raised error."""
        _patch_service(monkeypatch, ensure_data_raises=NoDataError("no data"))

        result = ensure_market_data_for_symbol("AAPL", "1min", "2024-01-01", "2024-01-02")

        assert result["bars"] == []
        assert result["symbol"] == "AAPL"

    def test_non_nodata_valueerror_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A plain ValueError (e.g. a provider ValidationError) is NOT swallowed (H1)."""
        _patch_service(monkeypatch, ensure_data_raises=ValueError("malformed provider payload"))

        with pytest.raises(ValueError, match="malformed provider payload"):
            ensure_market_data_for_symbol("AAPL", "1min", "2024-01-01", "2024-01-02")

    def test_malformed_interval_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A bad interval is a real input error, parsed before the no-data try (SE-4)."""
        service = _patch_service(monkeypatch, ensure_data_return=make_ohlcv_series())

        with pytest.raises(ValueError):
            ensure_market_data_for_symbol("AAPL", "bogus-interval", "2024-01-01", "2024-01-02")

        service.ensure_data.assert_not_called()

    def test_malformed_date_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A bad date string is a real input error, not 'no data' (SE-4)."""
        service = _patch_service(monkeypatch, ensure_data_return=make_ohlcv_series())

        with pytest.raises(ValueError):
            ensure_market_data_for_symbol("AAPL", "1min", "not-a-date", "2024-01-02")

        service.ensure_data.assert_not_called()

    def test_autoretry_includes_redis_error(self) -> None:
        """The task retries on RedisError, mirroring ensure_market_data_for_job (SE-1)."""
        assert RedisError in ensure_market_data_for_symbol.autoretry_for
