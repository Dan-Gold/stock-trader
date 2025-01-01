"""Simple back testing script for a RSI trading strategy."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple, cast

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Backtesting Configuration
RSI_PERIOD: int = 9  # Originally 9, should be 9-11
RSI_OVERSOLD: int = 30
RSI_OVERBOUGHT: int = 70
AVERAGE_DOWN_RSI: int = 15  # RSI to trigger averaging down
INITIAL_CAPITAL: float = 10000.0
RESERVE_CAPITAL_RATIO: float = 0.00  # Reserve only 5% for averaging down
USE_ALL_CAPITAL: bool = True  # Toggle for "all-in" trading logic
TRADE_SIZE: float = 1000.0

TRAILING_STOP_PERCENT = 0.05  # Increase to 3% formerly 1%

ALLOW_FRACTIONAL_SHARES: bool = False  # Toggle if buying fractional shares is allowed
GENERATE_PLOTS: dict[str, bool] = {
    "overall": False,
    "daily": False,
    "weekly": False,
}

# Market Timing
TRADING_START_TIME: time = time(9, 30)  # Market open
TRADING_END_TIME: time = time(16, 0)  # Market close

BUYING_START_TIME: time = time(9, 45)
BUYING_END_TIME: time = time(16, 0)

SELLING_START_TIME: time = time(9, 30)
SELLING_END_TIME: time = time(16, 0)


@dataclass
class Trade:
    """Trade data class to store trade information."""

    action: str
    timestamp: datetime
    price: Optional[float] = None
    contracts: Optional[float] = None
    capital: Optional[float] = None
    gain_loss: float = 0.0


@dataclass
class Position:
    """Position data class to store current position information."""

    entry_price: Optional[float] = None
    contracts: float = 0.0
    average_price: Optional[float] = None
    highest_price: Optional[float] = None


# Define types for clarity
TradeLog = list[Trade]


def load_data(file_path: str) -> pd.DataFrame:
    """Load historical data from a CSV file."""
    df: pd.DataFrame = pd.read_csv(file_path, parse_dates=["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df


def calculate_rsi(data: pd.DataFrame, period: int) -> pd.DataFrame:
    """Calculate RSI for the given DataFrame."""
    delta: pd.Series = data["close"].diff().astype(float)
    data["gain"] = np.where(delta > 0, delta, 0)
    data["loss"] = np.where(delta < 0, -delta, 0)
    data["avg_gain"] = data["gain"].rolling(window=period, min_periods=1).mean()
    data["avg_loss"] = data["loss"].rolling(window=period, min_periods=1).mean()
    data["rs"] = data["avg_gain"] / data["avg_loss"]
    data["RSI"] = 100 - (100 / (1 + data["rs"]))
    return data


def is_market_open(timestamp: pd.Timestamp) -> bool:
    """Check if a given timestamp is within market hours."""
    return TRADING_START_TIME <= timestamp.time() <= TRADING_END_TIME


def is_buying_time(timestamp: pd.Timestamp) -> bool:
    """Check if a given timestamp is within buying hours."""
    return BUYING_START_TIME <= timestamp.time() <= TRADING_END_TIME


def is_selling_time(timestamp: pd.Timestamp) -> bool:
    """Check if a given timestamp is within selling hours."""
    return SELLING_START_TIME <= timestamp.time() <= TRADING_END_TIME


def confirm_trend(df: pd.DataFrame, idx: int) -> bool:
    """Confirm trend using 5m, 10m, and 15m RSI values."""
    try:
        # Aggregate data for 5m, 10m, and 15m timeframes
        df_5m = df.iloc[max(0, idx - 4) : idx + 1]  # Last 5 rows for 5m
        df_10m = df.iloc[max(0, idx - 9) : idx + 1]  # Last 10 rows for 10m
        df_15m = df.iloc[max(0, idx - 14) : idx + 1]  # Last 15 rows for 15m

        rsi_5m = df_5m["RSI"].mean()
        rsi_10m = df_10m["RSI"].mean()
        rsi_15m = df_15m["RSI"].mean()

        # Confirm trend: RSI values are all in oversold/overbought range
        return (rsi_5m < RSI_OVERSOLD and rsi_10m < RSI_OVERSOLD and rsi_15m < RSI_OVERSOLD) or (
            rsi_5m > RSI_OVERBOUGHT and rsi_10m > RSI_OVERBOUGHT and rsi_15m > RSI_OVERBOUGHT
        )

    except IndexError:
        return False  # Not enough data to confirm trend


def start_new_day(
    trade_log: TradeLog, current_time: pd.Timestamp, capital: float, last_date: date | None, current_date: date
) -> date:
    """Log the start of a new trading day."""
    if current_date != last_date:
        trade_log.append(Trade(action="START_DAY", timestamp=current_time, capital=capital))
        return current_date
    return last_date


def calculate_trade_size(capital: float) -> float:
    """Calculate the size of the trade based on settings."""
    if USE_ALL_CAPITAL:
        reserved_capital = RESERVE_CAPITAL_RATIO * capital
        return max(0, capital - reserved_capital)
    return TRADE_SIZE


def buy_trade_strategy(
    position: Position,
    current_rsi: float,
    trade_size: float,
    current_price: float,
    capital: float,
    trade_log: TradeLog,
    current_time: pd.Timestamp,
) -> tuple[float, Position]:
    """Handle buying logic when RSI is oversold."""
    if is_buying_time(current_time):
        if position.contracts == 0 and current_rsi < RSI_OVERSOLD:
            capital, position = execute_buy(position, trade_size, current_price, capital, trade_log, current_time)

    return capital, position


def execute_buy(
    position: Position,
    trade_size: float,
    current_price: float,
    capital: float,
    trade_log: TradeLog,
    current_time: pd.Timestamp,
) -> tuple[float, Position]:
    """Execute buy."""
    if ALLOW_FRACTIONAL_SHARES:
        contracts = trade_size / current_price
    else:
        contracts = float(trade_size // current_price)

    position.entry_price = current_price
    position.contracts = contracts
    position.average_price = current_price
    position.highest_price = current_price
    capital -= trade_size
    trade_log.append(
        Trade(
            action="BUY",
            timestamp=current_time,
            price=current_price,
            contracts=contracts,
            capital=capital,
        )
    )
    return capital, position


def sell_trade_strategy(
    position: Position,
    current_rsi: float,
    current_price: float,
    capital: float,
    trade_log: TradeLog,
    current_time: pd.Timestamp,
    df: pd.DataFrame,
    i: int,
) -> tuple[float, Position]:
    """Handle selling logic when RSI is overbought or trailing stop loss is triggered."""
    if position.contracts > 0 and is_selling_time(current_time):
        if position.highest_price is None:
            raise ValueError("Highest price is not set for an open position")

        position.highest_price = max(position.highest_price, current_price)

        if position.entry_price is None:
            raise ValueError("Entry price is not set for an open position")

        entry_price: float = position.entry_price

        # Trailing Stop Loss: Sell if price drops below the trailing stop
        if current_price < position.highest_price * (1 - TRAILING_STOP_PERCENT):
            capital, position = execute_sell(
                "SELL_TRAILING_STOP", position, entry_price, current_price, capital, trade_log, current_time
            )

        # Exit Logic: Sell when RSI is overbought
        elif current_rsi > RSI_OVERBOUGHT and confirm_trend(df, i):
            capital, position = execute_sell("SELL", position, entry_price, current_price, capital, trade_log, current_time)

    return capital, position


def execute_sell(
    action: str,
    position: Position,
    entry_price: float,
    current_price: float,
    capital: float,
    trade_log: TradeLog,
    current_time: pd.Timestamp,
) -> tuple[float, Position]:
    """Execute sell."""
    exit_value_sell: float = position.contracts * current_price
    capital += exit_value_sell

    trade_log.append(
        Trade(
            action=action,
            timestamp=current_time,
            price=current_price,
            contracts=position.contracts,
            capital=capital,
            gain_loss=(current_price - entry_price) * position.contracts,
        )
    )

    return capital, Position()


def backtest(df: pd.DataFrame, initial_capital: float) -> Tuple[float, TradeLog]:
    """Back testing logic to simulate trading strategy."""
    capital: float = initial_capital
    trade_log: TradeLog = []
    position = Position()
    last_date: date | None = None

    for i in range(len(df)):
        row: pd.Series = df.iloc[i]
        current_price: float = row["close"]
        current_rsi: float = row["RSI"]
        current_time: pd.Timestamp = pd.Timestamp(str(row.name))
        current_date: date = current_time.date()

        # Check if it's the start of a new market day
        last_date = start_new_day(trade_log, current_time, capital, last_date, current_date)

        # Skip rows outside market hours
        if not is_market_open(current_time):
            continue

        # Calculate trade size
        trade_size = calculate_trade_size(capital)

        # Entry Logic: Buy when RSI is oversold
        capital, position = buy_trade_strategy(position, current_rsi, trade_size, current_price, capital, trade_log, current_time)

        # Update Highest Price for Trailing Stop Loss
        capital, position = sell_trade_strategy(position, current_rsi, current_price, capital, trade_log, current_time, df, i)

        assert True

    # Final Liquidation at the End of Backtest
    if position.contracts > 0:
        if position.entry_price is None:
            raise ValueError("Entry price is not set for an open position")

        final_price: float = df.iloc[-1]["close"]
        exit_value_final: float = position.contracts * final_price
        capital += exit_value_final

        trade_log.append(
            Trade(
                action="FINAL_SELL",
                timestamp=cast(datetime, df.iloc[-1].name),
                price=final_price,
                contracts=position.contracts,
                capital=capital,
                gain_loss=(final_price - position.entry_price) * position.contracts,
            )
        )

    return capital, trade_log


def overall_plot(df: pd.DataFrame, trade_log: TradeLog) -> None:
    """Generate an overall plot."""
    print("Creating overall plot...")
    plt.figure(figsize=(40, 20), dpi=600)
    plt.plot(df.index, df["close"], label="Close Price", color="blue", linewidth=0.7)

    for trade in trade_log:
        if trade.action == "START_DAY":
            continue

        if trade.price is None:
            raise ValueError("Trade price is not set")

        trade_timestamp = mdates.date2num(trade.timestamp)

        if trade.action == "BUY":
            plt.scatter(trade_timestamp, trade.price, marker="^", color="green", label="Buy", s=100)
        elif trade.action in ["SELL", "SELL_TRAILING_STOP", "FINAL_SELL"]:
            plt.scatter(trade_timestamp, trade.price, marker="v", color="red", label="Sell", s=100)

            plt.annotate(
                f"{trade.gain_loss:.2f}",
                (trade_timestamp, trade.price),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                fontsize=8,
                color="red" if trade.gain_loss < 0 else "green",
            )

    plt.title("Overall Stock Price with Buy and Sell Signals")
    plt.xlabel("Timestamp")
    plt.ylabel("Price")
    plt.savefig("overall_trade_signals.svg", format="svg")
    plt.close()

    print("Overall plot created successfully.")


def daily_plot(df: pd.DataFrame, trade_log: TradeLog) -> None:
    """Generate daily plots."""
    print("Creating daily plots...")

    # Group by date
    daily_groups = df.groupby(df.index.to_series().dt.date)

    for date_data, day_data in daily_groups:
        plt.figure(figsize=(14, 7))
        plt.plot(day_data.index, day_data["close"], label="Close Price", color="blue", linewidth=0.7)

        # Filter trades for the current day
        daily_trades = [trade for trade in trade_log if trade.timestamp.date() == date_data]

        for trade in daily_trades:
            if trade.action == "START_DAY":
                continue

            if trade.price is None:
                raise ValueError("Trade price is not set")

            trade_timestamp = mdates.date2num(trade.timestamp)

            if trade.action == "BUY":
                plt.scatter(trade_timestamp, trade.price, marker="^", color="green", label="Buy", s=100)
            elif trade.action in ["SELL", "SELL_TRAILING_STOP", "FINAL_SELL"]:
                plt.scatter(trade_timestamp, trade.price, marker="v", color="red", label="Sell", s=100)

                plt.annotate(
                    f"{trade.gain_loss:.2f}",
                    (trade_timestamp, trade.price),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha="center",
                    fontsize=8,
                    color="red" if trade.gain_loss < 0 else "green",
                )

        plt.title(f"Daily Stock Price with Buy and Sell Signals ({date_data})")
        plt.xlabel("Timestamp")
        plt.ylabel("Price")
        plt.legend(loc="best")

        # Save each daily plot
        output_file = f"daily_trade_signals_{date_data}.png"
        plt.savefig(output_file)
        plt.close()

    print("Daily plots created successfully.")


def weekly_plot(df: pd.DataFrame, trade_log: TradeLog) -> None:
    """Generate weekly plots."""
    print("Creating weekly plots...")
    start_date = df.index.min().date()
    end_date = df.index.max().date()

    # Adjust start_date to the previous Monday if it's not already a Monday
    if start_date.weekday() != 0:
        start_date -= timedelta(days=start_date.weekday())

    current_date = start_date

    while current_date <= end_date:
        week_start = current_date
        week_end = week_start + timedelta(days=4)  # Monday to Friday
        week_data = df.loc[week_start:week_end]

        if not week_data.empty:
            plt.figure(figsize=(14, 7))
            plt.plot(week_data.index, week_data["close"], label="Close Price", color="blue", linewidth=0.7)

            # Filter trades for the current week
            weekly_trades = [trade for trade in trade_log if week_start <= trade.timestamp.date() <= week_end]

            for trade in weekly_trades:
                if trade.action == "START_DAY":
                    continue

                if trade.price is None:
                    raise ValueError("Trade price is not set")

                trade_timestamp = mdates.date2num(trade.timestamp)

                if trade.action == "BUY":
                    plt.scatter(trade_timestamp, trade.price, marker="^", color="green", label="Buy", s=100)
                elif trade.action in ["SELL", "SELL_TRAILING_STOP", "FINAL_SELL"]:
                    plt.scatter(trade_timestamp, trade.price, marker="v", color="red", label="Sell", s=100)

                    plt.annotate(
                        f"{trade.gain_loss:.2f}",
                        (trade_timestamp, trade.price),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha="center",
                        fontsize=8,
                        color="red" if trade.gain_loss < 0 else "green",
                    )

            plt.title(f"Weekly Stock Price with Buy and Sell Signals ({week_start} to {week_end})")
            plt.xlabel("Timestamp")
            plt.ylabel("Price")
            # plt.legend(loc="best")

            # Save each weekly plot
            output_file = f"weekly_trade_signals_{week_start}_to_{week_end}.png"
            plt.savefig(output_file)
            plt.close()

        current_date = week_end + timedelta(days=3)  # Move to the next Monday

    print("Weekly plots created successfully.")


def generate_all_plots(df: pd.DataFrame, trade_log: TradeLog) -> None:
    """Generate all plots for the backtest."""
    if GENERATE_PLOTS["overall"]:
        overall_plot(df, trade_log)

    if GENERATE_PLOTS["daily"]:
        daily_plot(df, trade_log)

    if GENERATE_PLOTS["weekly"]:
        weekly_plot(df, trade_log)


def main() -> None:
    """Main function to load data, calculate RSI, and run the backtest."""
    file_path: str = "./data/PLTR_data_1min_comb.csv"  # Update with the path to your CSV file

    print("Loading historical data...")
    df: pd.DataFrame = load_data(file_path)
    # df.index = pd.to_datetime(df.index)
    df.sort_index(ascending=True, inplace=True)

    print("Calculating RSI...")
    df = calculate_rsi(df, RSI_PERIOD)

    print("Running backtest...")
    final_capital, trade_log = backtest(df, INITIAL_CAPITAL)

    print("Trade Log:")
    for trade in trade_log:
        print(
            f"Action: {trade.action}, Timestamp: {trade.timestamp}, Price: {trade.price}, Contracts: {trade.contracts}, Capital: {trade.capital}, Gain/Loss: {trade.gain_loss}"
        )

    print(f"Final Capital: ${final_capital:.2f}")

    generate_all_plots(df, trade_log)


if __name__ == "__main__":
    main()
