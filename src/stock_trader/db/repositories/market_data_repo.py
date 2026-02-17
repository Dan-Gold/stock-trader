"""Repository for market data access."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from stock_trader.core.models.ohlcv_series import OHLCVSeries
from stock_trader.db.models.market_data import MarketDataTableSchema
from stock_trader.models.shared_enums import IntervalEnum


class MarketDataRepositorySync:
    """Sync repository for Celery worker database access."""

    def __init__(self, session_maker: sessionmaker) -> None:
        self.database_session = session_maker

    def get_ohlcv_data(
        self, symbol: str, start_time: date, end_time: date, interval: IntervalEnum = IntervalEnum.ONE_MINUTE
    ) -> OHLCVSeries | None:
        """Get OHLCV market data for a symbol and time range."""
        with self.database_session() as session:
            query = (
                select(MarketDataTableSchema)
                .where(MarketDataTableSchema.symbol == symbol)
                .where(MarketDataTableSchema.interval == interval)
                .where(MarketDataTableSchema.timestamp >= start_time)
                .where(MarketDataTableSchema.timestamp <= end_time)
                .order_by(MarketDataTableSchema.timestamp.asc())
            )
            result = session.execute(query).scalars().all()

            if not result:
                return None

            return MarketDataTableSchema.from_records(result)

    def bulk_insert_market_data(self, data: OHLCVSeries) -> None:
        """Bulk insert market data rows, skipping duplicates."""
        with self.database_session() as session:
            records = [
                {
                    "symbol": data.symbol,
                    "interval": data.interval,
                    "timestamp": bar.timestamp,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in data.bars
            ]

            stmt = (
                insert(MarketDataTableSchema)
                .values(records)
                .on_conflict_do_nothing(constraint="uq_market_data_symbol_interval_timestamp")
            )
            session.execute(stmt)
            session.commit()
