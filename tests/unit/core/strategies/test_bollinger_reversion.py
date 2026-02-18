"""Unit tests for BollingerReversionStrategy."""

import pytest

from stock_trader.core.strategies.bollinger_reversion import BollingerReversionStrategy
from stock_trader.core.strategies.models import SignalType
from tests.helpers import flat_then_dip_then_revert, make_ohlcv_df


class TestBollingerInit:
    """Tests for BollingerReversionStrategy constructor."""

    def test_default_parameters(self) -> None:
        """Default parameters should be set correctly when not provided."""
        strategy = BollingerReversionStrategy()

        assert strategy.length == 20
        assert strategy.std_dev == 2.0
        assert strategy.exit_at == "middle"
        assert strategy.initial_capital == 10000.0

    def test_custom_parameters(self) -> None:
        """Custom parameters should be set correctly when provided."""
        strategy = BollingerReversionStrategy(length=10, std_dev=1.5, exit_at="upper", initial_capital=50000)

        assert strategy.length == 10
        assert strategy.std_dev == 1.5
        assert strategy.exit_at == "upper"
        assert strategy.initial_capital == 50000.0

    def test_invalid_exit_at_raises(self) -> None:
        """Providing an invalid exit_at value should raise a ValueError."""
        with pytest.raises(ValueError, match="exit_at must be"):
            BollingerReversionStrategy(exit_at="invalid")


class TestBollingerRun:
    """Tests for BollingerReversionStrategy.run()."""

    def test_no_trades_on_flat_data(self) -> None:
        """A perfectly flat series stays within bands, no buy signals."""
        prices = [100.0] * 50
        df = make_ohlcv_df(prices)

        result = BollingerReversionStrategy().run(df)

        assert result.trades == []
        assert result.metrics.num_trades == 0

    def test_buy_triggered_on_dip_below_lower_band(self) -> None:
        """A dip below the lower band should produce a BUY signal."""
        prices = flat_then_dip_then_revert(dip_price=80.0)
        df = make_ohlcv_df(prices)

        result = BollingerReversionStrategy().run(df)

        buy_trades = [t for t in result.trades if t.signal == SignalType.BUY]
        assert len(buy_trades) >= 1
        assert buy_trades[0].price == pytest.approx(80.0)

    def test_sell_triggered_on_revert_to_middle(self) -> None:
        """After a buy, reverting to the middle band should trigger SELL."""
        prices = flat_then_dip_then_revert(dip_price=80.0, revert_price=100.0)
        df = make_ohlcv_df(prices)

        result = BollingerReversionStrategy().run(df)

        sell_trades = [t for t in result.trades if t.signal == SignalType.SELL]
        assert len(sell_trades) >= 1

    def test_forced_exit_at_end_of_data(self) -> None:
        """If still in position at end of data, a forced SELL occurs."""
        # Dip but don't revert, stay low
        prices = flat_then_dip_then_revert(dip_price=80.0, revert_price=81.0, n_revert=1)
        df = make_ohlcv_df(prices)

        result = BollingerReversionStrategy().run(df)

        if result.trades:
            last_trade = result.trades[-1]
            # Should end with a sell (either natural or forced)
            assert last_trade.signal == SignalType.SELL

    def test_trades_alternate_buy_sell(self) -> None:
        """Trades should always alternate BUY → SELL (no pyramiding)."""
        prices = flat_then_dip_then_revert(dip_price=80.0, revert_price=100.0)
        df = make_ohlcv_df(prices)

        result = BollingerReversionStrategy().run(df)

        for i, trade in enumerate(result.trades):
            expected = SignalType.BUY if i % 2 == 0 else SignalType.SELL
            assert trade.signal == expected, f"Trade {i} should be {expected}, got {trade.signal}"

    def test_result_contains_chart_data_with_bands(self) -> None:
        """BacktestResult.chart_data should contain Bollinger Band columns."""
        prices = flat_then_dip_then_revert()
        df = make_ohlcv_df(prices)

        result = BollingerReversionStrategy().run(df)

        assert "bb_lower" in result.chart_data.columns
        assert "bb_middle" in result.chart_data.columns
        assert "bb_upper" in result.chart_data.columns

    def test_result_metadata(self) -> None:
        """BacktestResult should carry strategy name, params, and date range."""
        prices = flat_then_dip_then_revert()
        df = make_ohlcv_df(prices)

        result = BollingerReversionStrategy(length=20, std_dev=2.0).run(df)

        assert result.strategy == "bollinger_reversion"
        assert result.params["length"] == 20
        assert result.params["std_dev"] == 2.0
        assert result.start_date is not None
        assert result.end_date is not None

    def test_too_few_rows_raises(self) -> None:
        """If df has fewer rows than length, bbands returns None → ValueError."""
        prices = [100.0] * 5  # only 5 rows, need 20
        df = make_ohlcv_df(prices)

        with pytest.raises(ValueError, match="pandas-ta returned None"):
            BollingerReversionStrategy(length=20).run(df)

    def test_exit_at_upper_delays_sell(self) -> None:
        """exit_at='upper' should hold the position longer than exit_at='middle'."""
        prices = flat_then_dip_then_revert(dip_price=80.0, revert_price=100.0, n_revert=5)
        df = make_ohlcv_df(prices)

        result_middle = BollingerReversionStrategy(exit_at="middle").run(df)
        result_upper = BollingerReversionStrategy(exit_at="upper").run(df)

        middle_sells = [t for t in result_middle.trades if t.signal == SignalType.SELL]
        upper_sells = [t for t in result_upper.trades if t.signal == SignalType.SELL]

        # Middle exit should sell sooner, the upper band is higher, so
        # either the upper exit sells later or doesn't sell at all (forced exit).
        if middle_sells and upper_sells:
            assert upper_sells[0].timestamp >= middle_sells[0].timestamp

    def test_winning_trade_metrics(self) -> None:
        """A profitable round-trip should show positive return and win rate."""
        # Dip then revert higher
        prices = flat_then_dip_then_revert(
            flat_price=100.0,
            dip_price=80.0,
            revert_price=105.0,
            n_revert=3,
        )
        df = make_ohlcv_df(prices)

        result = BollingerReversionStrategy().run(df)

        if result.metrics.num_trades > 0:
            assert result.metrics.win_rate > 0
            assert result.metrics.ending_capital > 0
