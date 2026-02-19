"""Unit tests for calculate_metrics and strategy models."""

import json

import pytest

from stock_trader.core.strategies.models import BacktestMetrics, calculate_metrics
from tests.helpers import make_backtest_result, make_buy_trade, make_sell_trade


class TestCalculateMetrics:
    """Tests for calculate_metrics."""

    def test_empty_trades_returns_defaults(self) -> None:
        """No trades should return zeroed-out metrics."""
        result = calculate_metrics(trades=[], initial_capital=10000)

        assert result == BacktestMetrics()
        assert result.num_trades == 0
        assert result.total_return_pct == 0.0

    def test_single_winning_trade(self) -> None:
        """Buy at 100, sell at 120 -> 20% return, 100% win rate."""
        trades = [make_buy_trade(100.0, day=1), make_sell_trade(120.0, day=2)]

        result = calculate_metrics(trades=trades, initial_capital=10000)

        assert result.num_trades == 1
        assert result.win_rate == 100.0
        assert result.total_return_pct == pytest.approx(20.0)
        assert result.ending_capital == pytest.approx(12000.0)
        assert result.max_drawdown_pct == 0.0

    def test_single_losing_trade(self) -> None:
        """Buy at 100, sell at 80 -> -20% return, 0% win rate."""
        trades = [make_buy_trade(100.0, day=1), make_sell_trade(80.0, day=2)]

        result = calculate_metrics(trades=trades, initial_capital=10000)

        assert result.num_trades == 1
        assert result.win_rate == 0.0
        assert result.total_return_pct == pytest.approx(-20.0)
        assert result.ending_capital == pytest.approx(8000.0)

    def test_multiple_trades_mixed(self) -> None:
        """Two trades: one win, one loss -> 50% win rate."""
        trades = [
            make_buy_trade(100.0, day=1),
            make_sell_trade(120.0, day=2),  # win
            make_buy_trade(110.0, day=3),
            make_sell_trade(100.0, day=4),  # loss
        ]

        result = calculate_metrics(trades=trades, initial_capital=10000)

        assert result.num_trades == 2
        assert result.win_rate == 50.0

    def test_drawdown_calculated(self) -> None:
        """A win followed by a loss should produce a nonzero drawdown."""
        trades = [
            make_buy_trade(100.0, day=1),
            make_sell_trade(150.0, day=2),  # big win -> equity peaks
            make_buy_trade(140.0, day=3),
            make_sell_trade(100.0, day=4),  # loss from peak
        ]

        result = calculate_metrics(trades=trades, initial_capital=10000)

        assert result.max_drawdown_pct > 0

    def test_odd_number_of_trades_ignores_unpaired(self) -> None:
        """An odd-count list with a trailing BUY should pair only the complete round-trips."""
        trades = [
            make_buy_trade(100.0, day=1),
            make_sell_trade(110.0, day=2),  # paired
            make_buy_trade(105.0, day=3),  # unpaired trailing BUY
        ]

        result = calculate_metrics(trades=trades, initial_capital=10000)

        assert result.num_trades == 1

    def test_mismatched_signals_skipped(self) -> None:
        """Trades where pair[0] is SELL (not BUY) should not be counted."""
        trades = [make_sell_trade(100.0, day=1), make_buy_trade(90.0, day=2)]

        result = calculate_metrics(trades=trades, initial_capital=10000)

        # Pairing logic expects BUY first, this pair is skipped
        assert result == BacktestMetrics()


class TestBacktestResultSerialization:
    """Tests for BacktestResult.to_summary() and to_raw()."""

    def test_to_summary_keys(self) -> None:
        """to_summary() should include strategy, params, dates, and metrics."""
        result = make_backtest_result()
        summary = result.to_summary()

        assert set(summary.keys()) == {"strategy", "params", "start_date", "end_date", "metrics"}
        assert summary["strategy"] == "bollinger_reversion"

    def test_to_summary_excludes_trades(self) -> None:
        """to_summary() should NOT include trades or chart_data."""
        summary = make_backtest_result().to_summary()

        assert "trades" not in summary
        assert "chart_data" not in summary

    def test_to_raw_contains_chart_and_trades(self) -> None:
        """to_raw() should contain 'columns', 'data', 'index', and 'trades'."""
        raw = make_backtest_result().to_raw()

        assert "columns" in raw
        assert "data" in raw
        assert "index" in raw
        assert "trades" in raw

    def test_to_raw_only_includes_close_and_indicators(self) -> None:
        """to_raw() chart columns should be close + indicator_columns only."""
        raw = make_backtest_result().to_raw()

        assert set(raw["columns"]) == {"close", "bb_lower", "bb_middle", "bb_upper"}

    def test_to_raw_index_is_strings(self) -> None:
        """to_raw() index should be string-ified timestamps."""
        raw = make_backtest_result().to_raw()

        for entry in raw["index"]:
            assert isinstance(entry, str)

    def test_to_raw_is_json_serializable(self) -> None:
        """to_raw() must be fully JSON-serializable for JSONB storage."""
        raw = make_backtest_result().to_raw()

        # Will raise TypeError if any value is not serializable
        json.dumps(raw)

    def test_to_summary_is_json_serializable(self) -> None:
        """to_summary() must be fully JSON-serializable for JSONB storage."""
        summary = make_backtest_result().to_summary()

        json.dumps(summary)
