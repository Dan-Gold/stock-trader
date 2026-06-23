"""Unit tests for BollingerReversionStrategy."""

from datetime import time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from stock_trader.core.strategies.bollinger_reversion import BollingerParams, BollingerReversionStrategy
from stock_trader.core.strategies.models import SignalType
from tests.helpers import flat_then_dip_then_revert, make_ohlcv_df

ET = ZoneInfo("America/New_York")


class TestBollingerParams:
    """Tests for BollingerParams validation."""

    def test_defaults(self) -> None:
        """Default values should be set correctly when no args are provided."""
        params = BollingerParams()

        assert params.length == 20
        assert params.std_dev == 2.0
        assert params.exit_at == "middle"
        assert params.initial_capital == 10000.0

    def test_custom_values(self) -> None:
        """Custom values should be accepted and set correctly."""
        params = BollingerParams(length=10, std_dev=1.5, exit_at="upper", initial_capital=50000)

        assert params.length == 10
        assert params.std_dev == 1.5
        assert params.exit_at == "upper"
        assert params.initial_capital == 50000.0

    def test_invalid_exit_at_raises(self) -> None:
        """Invalid exit_at values should raise a ValidationError."""
        with pytest.raises(ValidationError, match="Input should be 'middle' or 'upper'"):
            BollingerParams(exit_at="invalid")

    def test_length_below_minimum_raises(self) -> None:
        """Length values below the minimum should raise a ValidationError."""
        with pytest.raises(ValidationError, match="greater than or equal to 5"):
            BollingerParams(length=2)

    def test_std_dev_zero_raises(self) -> None:
        """Standard deviation of zero should raise a ValidationError."""
        with pytest.raises(ValidationError, match="greater than 0"):
            BollingerParams(std_dev=0)

    def test_negative_capital_raises(self) -> None:
        """Negative initial capital should raise a ValidationError."""
        with pytest.raises(ValidationError, match="greater than 0"):
            BollingerParams(initial_capital=-100)

    def test_unknown_param_raises(self) -> None:
        """Extra keys should be rejected."""
        with pytest.raises(ValidationError, match="Extra inputs"):
            BollingerParams(length=20, unknown_key="oops")  # type: ignore[call-arg]

    def test_coerces_float_length_to_int(self) -> None:
        """JSON round-trips may produce float for int fields; Pydantic should coerce."""
        params = BollingerParams(length=20.0)

        assert params.length == 20
        assert isinstance(params.length, int)


class TestBollingerInit:
    """Tests for BollingerReversionStrategy constructor."""

    def test_accepts_params_model(self) -> None:
        """Constructor should accept a BollingerParams instance."""
        params = BollingerParams(length=10, std_dev=1.5, exit_at="upper")
        strategy = BollingerReversionStrategy(params=params)

        assert strategy.length == 10
        assert strategy.std_dev == 1.5

    def test_accepts_kwargs(self) -> None:
        """Constructor should still accept bare kwargs for convenience."""
        strategy = BollingerReversionStrategy(length=15)

        assert strategy.length == 15

    def test_defaults_without_args(self) -> None:
        """Constructor with no args should use all default parameter values."""
        strategy = BollingerReversionStrategy()

        assert strategy.length == 20
        assert strategy.std_dev == 2.0


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

        assert len(result.trades) >= 2, "Expected at least one BUY/SELL pair"
        last_trade = result.trades[-1]
        assert last_trade.signal == SignalType.SELL

    def test_trades_alternate_buy_sell(self) -> None:
        """Trades should always alternate BUY -> SELL (no pyramiding)."""
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
        """If df has fewer rows than length, bbands returns None -> ValueError."""
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

        assert middle_sells, "Expected at least one SELL with exit_at='middle'"
        assert upper_sells, "Expected at least one SELL with exit_at='upper'"
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

        assert result.metrics.num_trades > 0, "Expected at least one round-trip trade"
        assert result.metrics.win_rate > 0
        assert result.metrics.ending_capital > 0


class TestBollingerMarketHours:
    """Tests that trading is restricted to the regular session (09:30-16:00 ET)."""

    @staticmethod
    def _oscillating(n: int, *, seed: int = 42) -> list[float]:
        """Flat-ish prices with enough width that the Bollinger bands are non-trivial."""
        rng = np.random.default_rng(seed)
        return (100.0 + rng.normal(0, 1.5, n)).tolist()

    def test_no_trades_on_after_hours_signal(self) -> None:
        """A dip below the lower band that occurs after 16:00 ET must not trade."""
        # 30 in-session warmup bars (15:30-15:59 ET), then a dip during after-hours.
        prices = [*self._oscillating(30), 80.0, 80.0, 80.0]
        df = make_ohlcv_df(prices, start="2024-01-02 15:30")

        result = BollingerReversionStrategy(length=20).run(df)

        assert result.trades == [], "Signals outside the regular session must be ignored"

    def test_indicators_computed_on_extended_hours_rows(self) -> None:
        """Bands are still computed over extended-hours bars, even though they don't trade."""
        prices = [*self._oscillating(30), 80.0, 80.0, 80.0]
        df = make_ohlcv_df(prices, start="2024-01-02 15:30")

        result = BollingerReversionStrategy(length=20).run(df)

        index = result.chart_data.index
        assert isinstance(index, pd.DatetimeIndex)
        after_hours = index.tz_convert(ET).time >= time(16, 0)
        assert after_hours.any(), "Test fixture should include after-hours rows"
        assert result.chart_data.loc[after_hours, "bb_middle"].notna().any()

    def test_forced_exit_uses_last_in_session_bar(self) -> None:
        """A position held into after-hours is force-closed on the last in-session bar."""
        # BUY fires in-session, price stays low (no revert) through after-hours.
        prices = [*self._oscillating(21), *([80.0] * 14)]
        df = make_ohlcv_df(prices, start="2024-01-02 15:30")

        result = BollingerReversionStrategy(length=20).run(df)

        assert len(result.trades) >= 2, "Expected a BUY then a forced SELL"
        last_trade = result.trades[-1]
        assert last_trade.signal == SignalType.SELL
        exit_et = last_trade.timestamp.astimezone(ET).time()
        assert exit_et == time(15, 59), "Forced exit should land on the last regular-session bar"

    def test_all_trades_fall_inside_regular_session(self) -> None:
        """Every emitted trade timestamp is within 09:30-16:00 ET."""
        prices = flat_then_dip_then_revert(dip_price=80.0, revert_price=100.0)
        df = make_ohlcv_df(prices)

        result = BollingerReversionStrategy().run(df)

        assert result.trades, "Expected at least one in-session trade"
        for trade in result.trades:
            et = trade.timestamp.astimezone(ET).time()
            assert time(9, 30) <= et < time(16, 0)
