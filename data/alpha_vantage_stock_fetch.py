"""Fetch stock data from Alpha Vantage API and save to CSV."""

import os

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
SYMBOL = "PLTR"
INTERVAL = "1min"

url = "https://www.alphavantage.co/query"
params = {
    "function": "TIME_SERIES_INTRADAY",
    "symbol": SYMBOL,
    "interval": INTERVAL,
    "apikey": API_KEY,
    "outputsize": "full",  # Fetch maximum data available
    "datatype": "csv",
}
response = requests.get(url, params=params)

file_name = f"{SYMBOL}_data_{INTERVAL}_extra_3.csv"

# Save to CSV
with open(file_name, "w") as file:
    file.write(response.text)

# Load into DataFrame
df = pd.read_csv(file_name)
print(df.head())
