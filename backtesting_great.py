"""Simple back testing script for a RSI trading strategy."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional, Tuple

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

# Market Timing
TRADING_START_TIME: time = time(9, 30)  # Market open
TRADING_END_TIME: time = time(16, 0)  # Market close


@dataclass
class Trade:
    """Trade data class to store trade information."""

    action: str
    timestamp: datetime
    price: Optional[float] = None
    contracts: Optional[float] = None
    capital: Optional[float] = None
    gain_loss: Optional[float] = None


# Define types for clarity
TradeLog = list[Trade]


# Load Historical Data
def load_data(file_path: str) -> pd.DataFrame:
    """Load historical data from a CSV file."""
    df: pd.DataFrame = pd.read_csv(file_path, parse_dates=["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df


# Compute RSI
def calculate_rsi(data: pd.DataFrame, period: int) -> pd.DataFrame:
    """Calculate RSI for the given DataFrame."""
    delta = data["close"].diff()
    data["gain"] = np.where(delta > 0, delta, 0)
    data["loss"] = np.where(delta < 0, -delta, 0)
    data["avg_gain"] = data["gain"].rolling(window=period, min_periods=1).mean()
    data["avg_loss"] = data["loss"].rolling(window=period, min_periods=1).mean()
    data["rs"] = data["avg_gain"] / data["avg_loss"]
    data["RSI"] = 100 - (100 / (1 + data["rs"]))
    return data


# Filter for Market Hours
def is_market_open(timestamp: pd.Timestamp) -> bool:
    """Check if a given timestamp is within market hours."""
    return TRADING_START_TIME <= timestamp.time() <= TRADING_END_TIME


# Multi-Timeframe Confirmation
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


# Backtesting Logic
def backtest(df: pd.DataFrame, initial_capital: float) -> Tuple[float, TradeLog]:
    """Back testing logic to simulate trading strategy."""
    capital: float = initial_capital
    trade_log: TradeLog = []
    position = {"entry_price": None, "contracts": 0, "average_price": None, "highest_price": None}
    last_date: Optional[datetime] = None  # Track the date of the previous row

    for i in range(len(df)):
        row: pd.Series = df.iloc[i]
        current_price: float = row["close"]
        current_rsi: float = row["RSI"]
        current_time: pd.Timestamp = row.name
        current_date: datetime = current_time.date()

        # Check if it's the start of a new market day
        if current_date != last_date:
            trade_log.append(
                Trade(
                    action="START_DAY",
                    timestamp=current_time,
                    capital=capital,
                )
            )
            last_date = current_date

        # Skip rows outside market hours
        if not is_market_open(current_time):
            continue

        # Calculate dynamic trade size if "all-in" option is enabled
        trade_size = TRADE_SIZE
        if USE_ALL_CAPITAL:
            reserved_capital: float = RESERVE_CAPITAL_RATIO * capital
            trade_size = max(0, capital - reserved_capital)

        # Entry Logic: Buy when RSI is oversold
        if position["contracts"] == 0 and current_rsi < RSI_OVERSOLD:
            contracts: float = trade_size / current_price
            position["entry_price"] = current_price
            position["contracts"] = contracts
            position["average_price"] = current_price
            position["highest_price"] = current_price
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

        # Update Highest Price for Trailing Stop Loss
        if position["contracts"] > 0:
            position["highest_price"] = max(position["highest_price"], current_price)

            # Trailing Stop Loss: Sell if price drops below the trailing stop
            if current_price < position["highest_price"] * (1 - TRAILING_STOP_PERCENT):
                exit_value: float = position["contracts"] * current_price
                capital += exit_value
                trade_log.append(
                    Trade(
                        action="SELL_TRAILING_STOP",
                        timestamp=current_time,
                        price=current_price,
                        contracts=position["contracts"],
                        capital=capital,
                        gain_loss=(current_price - position["entry_price"]) * position["contracts"],
                    )
                )
                position = {"entry_price": None, "contracts": 0, "average_price": None, "highest_price": None}
                continue

            # Exit Logic: Sell when RSI is overbought
            elif current_rsi > RSI_OVERBOUGHT and confirm_trend(df, i):
                exit_value: float = position["contracts"] * current_price
                capital += exit_value
                trade_log.append(
                    Trade(
                        action="SELL",
                        timestamp=current_time,
                        price=current_price,
                        contracts=position["contracts"],
                        capital=capital,
                        gain_loss=(current_price - position["entry_price"]) * position["contracts"],
                    )
                )
                position = {"entry_price": None, "contracts": 0, "average_price": None, "highest_price": None}

    # Final Liquidation at the End of Backtest
    if position["contracts"] > 0:
        final_price: float = df.iloc[-1]["close"]
        exit_value: float = position["contracts"] * final_price
        capital += exit_value
        trade_log.append(
            Trade(
                action="FINAL_SELL",
                timestamp=df.iloc[-1].name,
                price=final_price,
                contracts=position["contracts"],
                capital=capital,
                gain_loss=(final_price - position["entry_price"]) * position["contracts"],
            )
        )

    return capital, trade_log


# Main Backtest Execution
def main() -> None:
    """Main function to load data, calculate RSI, and run the backtest."""
    file_path: str = "./data/PLTR_data_1min_comb.csv"  # Update with the path to your CSV file

    print("Loading historical data...")
    df: pd.DataFrame = load_data(file_path)
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

    # Overall Plot
    print("Creating overall plot...")
    plt.figure(figsize=(14, 7))
    plt.plot(df.index, df["close"], label="Close Price", color="blue", linewidth=0.7)

    for trade in trade_log:
        trade_timestamp = trade.timestamp

        if trade.action == "BUY":
            plt.scatter(trade_timestamp, trade.price, marker="^", color="green", label="Buy", s=100)
        elif trade.action in ["SELL", "SELL_TRAILING_STOP", "FINAL_SELL"]:
            plt.scatter(trade_timestamp, trade.price, marker="v", color="red", label="Sell", s=100)
            gain_loss = trade.gain_loss
            plt.annotate(
                f"{gain_loss:.2f}",
                (trade_timestamp, trade.price),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                fontsize=8,
                color="red" if gain_loss < 0 else "green",
            )

    plt.title("Overall Stock Price with Buy and Sell Signals")
    plt.xlabel("Timestamp")
    plt.ylabel("Price")
    # plt.legend(loc="best")
    plt.savefig("overall_trade_signals.png")
    plt.close()

    # Daily Plots
    print("Creating daily plots...")
    daily_groups = df.groupby(df.index.date)

    for date, day_data in daily_groups:
        plt.figure(figsize=(14, 7))
        plt.plot(day_data.index, day_data["close"], label="Close Price", color="blue", linewidth=0.7)

        # Filter trades for the current day
        daily_trades = [trade for trade in trade_log if trade.timestamp.date() == date]

        for trade in daily_trades:
            trade_timestamp = trade.timestamp

            if trade.action == "BUY":
                plt.scatter(trade_timestamp, trade.price, marker="^", color="green", label="Buy", s=100)
            elif trade.action in ["SELL", "SELL_TRAILING_STOP", "FINAL_SELL"]:
                plt.scatter(trade_timestamp, trade.price, marker="v", color="red", label="Sell", s=100)
                gain_loss = trade.gain_loss
                plt.annotate(
                    f"{gain_loss:.2f}",
                    (trade_timestamp, trade.price),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha="center",
                    fontsize=8,
                    color="red" if gain_loss < 0 else "green",
                )

        plt.title(f"Daily Stock Price with Buy and Sell Signals ({date})")
        plt.xlabel("Timestamp")
        plt.ylabel("Price")
        plt.legend(loc="best")

        # Save each daily plot
        output_file = f"daily_trade_signals_{date}.png"
        plt.savefig(output_file)
        plt.close()

    # Weekly Plots
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
                trade_timestamp = trade.timestamp

                if trade.action == "BUY":
                    plt.scatter(trade_timestamp, trade.price, marker="^", color="green", label="Buy", s=100)
                elif trade.action in ["SELL", "SELL_TRAILING_STOP", "FINAL_SELL"]:
                    plt.scatter(trade_timestamp, trade.price, marker="v", color="red", label="Sell", s=100)
                    gain_loss = trade.gain_loss
                    plt.annotate(
                        f"{gain_loss:.2f}",
                        (trade_timestamp, trade.price),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha="center",
                        fontsize=8,
                        color="red" if gain_loss < 0 else "green",
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

    print("Plots created successfully.")


if __name__ == "__main__":
    main()
