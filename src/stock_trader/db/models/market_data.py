"""Market data OHLCV table for historical price storage."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Index, Numeric, String, UniqueConstraint, func, types
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import Enum as SqlEnum

from stock_trader.core.models.ohlcv_series import OHLCV, OHLCVSeries
from stock_trader.db.models import DatabaseModelBase
from stock_trader.models.shared_enums import IntervalEnum

interval_enum: SqlEnum = types.Enum(
    IntervalEnum,
    name="interval_enum",
    inherit_schema=True,
)


class MarketDataTableSchema(DatabaseModelBase):
    """Market data OHLCV table.

    Stores normalized intraday and daily price bars. One row per
    (symbol, interval, timestamp) combination.

    Designed for the cache-aside pattern:
        Redis (hot cache) → Postgres (persistent store) → Alpha Vantage (source)

    Usage:
        - Bulk insert with ON CONFLICT DO NOTHING to skip duplicates.
        - Query by symbol + interval + time range for backtest data loading.
    """

    __tablename__ = "market_data"
    __table_args__ = (
        UniqueConstraint("symbol", "interval", "timestamp", name="uq_market_data_symbol_interval_timestamp"),
        Index("ix_market_data_symbol_interval_ts", "symbol", "interval", "timestamp"),
        {"schema": "stock_trader"},
    )

    uuid: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=func.gen_random_uuid(),
    )
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    interval: Mapped[IntervalEnum] = mapped_column(interval_enum, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(postgresql.TIMESTAMP(timezone=True), nullable=False)

    open: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(postgresql.BIGINT, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        postgresql.TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def from_record(self) -> OHLCV:
        """Convert to OHLCV Pydantic model."""
        return OHLCV(
            timestamp=self.timestamp,
            open=float(self.open),
            high=float(self.high),
            low=float(self.low),
            close=float(self.close),
            volume=int(self.volume),
        )

    @classmethod
    def to_record(cls, ohlcv: OHLCV, symbol: str, interval: IntervalEnum) -> "MarketDataTableSchema":
        """Convert from OHLCV Pydantic model to MarketDataTableSchema."""
        return cls(
            symbol=symbol,
            timestamp=ohlcv.timestamp,
            interval=interval,
            open=ohlcv.open,
            high=ohlcv.high,
            low=ohlcv.low,
            close=ohlcv.close,
            volume=ohlcv.volume,
        )

    @staticmethod
    def from_records(records: list["MarketDataTableSchema"]) -> OHLCVSeries:
        """Convert a list of MarketDataTableSchema records to a list of OHLCV models."""
        if not records:
            raise ValueError("No records to convert to OHLCVSeries")

        if not records[0].symbol or not records[0].interval:
            raise ValueError("Records must have symbol and interval to convert to OHLCVSeries")

        return OHLCVSeries(
            symbol=records[0].symbol,
            interval=records[0].interval,
            bars=[record.from_record() for record in records],
        )
