"""Backtest jobs model."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Index, String, func, types
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import Enum as SqlEnum

from stock_trader.db.models import DatabaseModelBase
from stock_trader.models.shared_enums import BacktestStatusEnum

backtest_job_status: SqlEnum = types.Enum(
    BacktestStatusEnum,
    name="backtest_job_status",
    inherit_schema=True,
)


class BacktestJobTableSchema(DatabaseModelBase):
    """Backtest job table."""

    __tablename__ = "backtest_jobs"
    __table_args__ = (
        Index("ix_backtest_jobs_status", "status"),
        Index("ix_backtest_jobs_created", "create_time"),
        {"schema": "stock_trader"},
    )

    uuid: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)
    status = mapped_column(backtest_job_status, nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbols: Mapped[list[str]] = mapped_column(postgresql.JSONB, nullable=False)
    parameters = mapped_column(MutableDict.as_mutable(postgresql.JSONB))
    error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        postgresql.TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    start_time: Mapped[datetime] = mapped_column(postgresql.TIMESTAMP(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(postgresql.TIMESTAMP(timezone=True), nullable=True)
