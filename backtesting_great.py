"""Simple back testing script for a RSI trading strategy."""

from datetime import time
from typing import Optional, Tuple

import numpy as np
import pandas as pd

# Backtesting Configuration
RSI_PERIOD: int = 9  # Originally 9, should be 9-11
RSI_OVERSOLD: int = 30
RSI_OVERBOUGHT: int = 70
AVERAGE_DOWN_RSI: int = 15  # RSI to trigger averaging down
INITIAL_CAPITAL: float = 10000.0
RESERVE_CAPITAL_RATIO: float = 0.05  # Reserve only 5% for averaging down
USE_ALL_CAPITAL: bool = True  # Toggle for "all-in" trading logic
TRADE_SIZE: float = 1000.0

TRAILING_STOP_PERCENT = 0.05  # Increase to 3% formerly 1%

# Market Timing
TRADING_START_TIME: time = time(9, 30)  # Market open
TRADING_END_TIME: time = time(16, 0)  # Market close

# Define types for clarity
TradeLog = list[dict[str, float]]


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
    position: dict[str, Optional[float]] = {"entry_price": None, "contracts": 0, "average_price": None, "highest_price": None}
    last_date: Optional[pd.Timestamp] = None  # Track the date of the previous row

    for i in range(len(df)):
        row: pd.Series = df.iloc[i]
        current_price: float = row["close"]
        current_rsi: float = row["RSI"]
        current_time: pd.Timestamp = row.name
        current_date: pd.Timestamp = current_time.date()

        # Check if it's the start of a new market day
        if current_date != last_date:
            trade_log.append(
                {
                    "action": "START_DAY",
                    "date": str(current_date),
                    "time": str(current_time.time()),
                    "price": None,
                    "contracts": None,
                    "capital": capital,
                    "gain_loss": None,
                    "timestamp": str(current_time),
                }
            )
            last_date = current_date  # Update the last_date

        # Skip rows outside market hours
        if not is_market_open(current_time):
            continue

        # Calculate dynamic trade size if "all-in" option is enabled
        trade_size = TRADE_SIZE
        if USE_ALL_CAPITAL:
            reserved_capital: float = RESERVE_CAPITAL_RATIO * capital
            trade_size = max(0, capital - reserved_capital)

        # Entry Logic: Buy when RSI is oversold and trend is confirmed
        if position["contracts"] == 0 and current_rsi < RSI_OVERSOLD:  # and confirm_trend(df, i):
            contracts: float = trade_size / current_price
            position["entry_price"] = current_price
            position["contracts"] = contracts
            position["average_price"] = current_price
            position["highest_price"] = current_price
            capital -= trade_size
            trade_log.append(
                {
                    "action": "BUY",
                    "date": str(current_date),
                    "time": str(current_time.time()),
                    "price": current_price,
                    "contracts": contracts,
                    "capital": capital,
                    "gain_loss": 0,
                    "timestamp": str(current_time),
                }
            )

        # Update Highest Price for Trailing Stop Loss
        if position["contracts"] > 0:
            position["highest_price"] = max(position["highest_price"], current_price)

        # Trailing Stop Loss: Sell if price drops 1% from the highest price
        if position["contracts"] > 0 and current_price < position["highest_price"] * (1 - TRAILING_STOP_PERCENT):
            exit_value: float = position["contracts"] * current_price
            capital += exit_value
            trade_log.append(
                {
                    "action": "SELL_TRAILING_STOP",
                    "date": str(current_date),
                    "time": str(current_time.time()),
                    "price": current_price,
                    "contracts": position["contracts"],
                    "capital": capital,
                    "gain_loss": (current_price - position["entry_price"]) * position["contracts"],
                    "timestamp": str(current_time),
                }
            )
            position = {"entry_price": None, "contracts": 0, "average_price": None, "highest_price": None}
            continue

        # Exit Logic: Sell when RSI is overbought and trend is confirmed
        elif position["contracts"] > 0 and current_rsi > RSI_OVERBOUGHT and confirm_trend(df, i):
            exit_value: float = position["contracts"] * current_price
            capital += exit_value
            trade_log.append(
                {
                    "action": "SELL",
                    "date": str(current_date),
                    "time": str(current_time.time()),
                    "price": current_price,
                    "contracts": position["contracts"],
                    "capital": capital,
                    "gain_loss": (current_price - position["entry_price"]) * position["contracts"],
                    "timestamp": str(current_time),
                }
            )
            position = {"entry_price": None, "contracts": 0, "average_price": None, "highest_price": None}

    # Final Liquidation at the End of Backtest
    if position["contracts"] > 0:
        final_price: float = df.iloc[-1]["close"]
        exit_value: float = position["contracts"] * final_price
        capital += exit_value
        trade_log.append(
            {
                "action": "FINAL_SELL",
                "date": str(df.iloc[-1].name.date()),
                "time": str(df.iloc[-1].name.time()),
                "price": final_price,
                "contracts": position["contracts"],
                "capital": capital,
                "gain_loss": (final_price - position["entry_price"]) * position["contracts"],
                "timestamp": str(df.iloc[-1].name),
            }
        )

    return capital, trade_log


# Main Backtest Execution
def main() -> None:
    """Main function to load data, calculate RSI, and run the backtest."""
    # TODO: Want to test it out while monitoring multiple stocks at the same time
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
            f"Action: {trade['action']}, Date: {trade['date']}, Time: {trade['time']}, Price: {trade['price']}, Contracts: {trade['contracts']}, Capital: {trade['capital']}, Gain/Loss: {trade['gain_loss']}"
        )

    print(f"Final Capital: ${final_capital:.2f}")

    # # Plotting the data
    # plt.figure(figsize=(14, 7))
    # plt.plot(df.index, df["close"], label="Close Price")

    # # Marking buy and sell points
    # for trade in trade_log:
    #     if trade["action"] == "BUY":
    #         plt.scatter(trade["date"], trade["price"], marker="^", color="g", label="Buy")
    #     elif trade["action"] == "SELL":
    #         plt.scatter(trade["date"], trade["price"], marker="v", color="r", label="Sell")

    # plt.title("Stock Price with Buy and Sell Signals")
    # plt.xlabel("Date")
    # plt.ylabel("Price")
    # plt.legend()

    # # Save the plot as an image
    # plt.savefig("trade_signals.png")


if __name__ == "__main__":
    main()
