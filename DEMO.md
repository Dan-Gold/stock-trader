
## Services Up and Running

![services](assets/demo_images/services_up.png)


## Example Create Backtest Arguments
```
{
  "strategy_name": "bollinger_reversion",
  "symbols": [
    "NVDA",
    "AAPL",
    "MSFT",
    "GOOG",
    "AMZN",
    "META",
    "TSLA"
  ],
  "parameters": {
    "length": 15,
    "std_dev": 3,
    "exit_at": "upper"
  },
  "start_date": "2026-01-20",
  "end_date": "2026-02-20"
}
```

## API Endpoints working

![endpoints](assets/demo_images/api_endpoints_working.png)

## Job Created in DB

![created](assets/demo_images/created_in_db.png)

## Fetch Rate Limited

![rate](assets/demo_images/rate_limiter_active.png)

## Market Data in DB

![market](assets/demo_images/market_data_table.png)

## Workers Working

![workers](assets/demo_images/workers_working_tasks.png)

## Backtest Results

![results](assets/demo_images/backtest_db_results.png)