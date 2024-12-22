"""Real-Time Monitoring with RSI strategy."""

from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

# Configuration
API_KEY = "YOUR_API_KEY"  # Replace with your Alpha Vantage API key
SYMBOL = "SPY"
RSI_PERIOD = 9
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
AVERAGE_DOWN_RSI = 20
TRADE_SIZE = 1000  # $1000 per trade
TIMEFRAME = "1min"  # Time interval for live data
TRADE_LOG = []


# Fetch Real-Time Data
def fetch_data(symbol, interval, api_key):
    """Fetch real-time intraday data from Alpha Vantage."""
    url = "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY"
    params = {
        "symbol": symbol,
        "interval": interval,
        "apikey": api_key,
        "datatype": "json",
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "Time Series" in data:
        return data[f"Time Series ({interval})"]
    else:
        raise ValueError(f"Error fetching data: {data}")


# Compute RSI
def compute_rsi(df, period):
    """Calculate RSI for the given dataframe and period."""
    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(window=period, min_periods=1).mean()
    avg_loss = pd.Series(loss).rolling(window=period, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    df["RSI"] = rsi
    return df


# Trade Logic with Averaging Down
def trade_logic(df, trade_log, position):
    """Executes the trading logic: entry, averaging down, and exit."""
    current_price = df["close"].iloc[-1]
    current_rsi = df["RSI"].iloc[-1]
    print(f"Current Price: {current_price}, RSI: {current_rsi:.2f}")

    # Entry Logic
    if position["contracts"] == 0 and current_rsi < RSI_OVERSOLD:
        contracts = TRADE_SIZE / current_price
        position["entry_price"] = current_price
        position["contracts"] = contracts
        position["average_price"] = current_price
        print("RSI Oversold. Entering a call position.")
        trade_log.append({"timestamp": datetime.now(), "action": "BUY_CALL", "price": current_price, "contracts": contracts})

    # Averaging Down Logic
    elif position["contracts"] > 0 and current_rsi < AVERAGE_DOWN_RSI:
        additional_contracts = TRADE_SIZE / current_price
        new_total_contracts = position["contracts"] + additional_contracts
        position["average_price"] = (
            position["contracts"] * position["average_price"] + additional_contracts * current_price
        ) / new_total_contracts
        position["contracts"] = new_total_contracts
        print("RSI Deeply Oversold. Averaging down on the call position.")
        trade_log.append(
            {"timestamp": datetime.now(), "action": "AVERAGE_DOWN", "price": current_price, "contracts": additional_contracts}
        )

    # Exit Logic
    elif position["contracts"] > 0 and current_rsi > RSI_OVERBOUGHT:
        exit_value = position["contracts"] * current_price
        print("RSI Overbought. Selling the call position.")
        trade_log.append(
            {
                "timestamp": datetime.now(),
                "action": "SELL_CALL",
                "price": current_price,
                "contracts": position["contracts"],
                "exit_value": exit_value,
            }
        )
        position["entry_price"] = None
        position["contracts"] = 0
        position["average_price"] = None

    return trade_log, position


# Main Execution
def main():
    """Main function to execute the real-time monitoring."""
    try:
        # Fetch Real-Time Data
        raw_data = fetch_data(SYMBOL, TIMEFRAME, API_KEY)
        df = pd.DataFrame.from_dict(raw_data, orient="index", dtype=float)
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)

        # Calculate RSI
        df = compute_rsi(df, RSI_PERIOD)

        # Initialize Position
        position = {"entry_price": None, "contracts": 0, "average_price": None}

        # Run Trade Logic
        trade_log, position = trade_logic(df, TRADE_LOG, position)

        # Plot Data
        plt.figure(figsize=(10, 5))
        plt.plot(df.index, df["close"], label="Price")
        plt.plot(df.index, df["RSI"], label="RSI", color="orange")
        plt.axhline(y=RSI_OVERSOLD, color="green", linestyle="--", label="RSI Oversold")
        plt.axhline(y=RSI_OVERBOUGHT, color="red", linestyle="--", label="RSI Overbought")
        plt.legend()
        plt.show()

        # Print Trade Log
        print("Trade Log:", trade_log)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
