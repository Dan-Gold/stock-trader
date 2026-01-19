"""Backtest results model."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from stock_trader.db.models import DatabaseModelBase


class BacktestResultTableSchema(DatabaseModelBase):
    """Backtest results table."""

    __tablename__ = "backtest_results"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_backtest_results_job_id"),
        {"schema": "stock_trader"},
    )

    uuid: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("stock_trader.backtest_jobs.uuid", ondelete="CASCADE"), nullable=False)

    summary: Mapped[dict] = mapped_column(MutableDict.as_mutable(postgresql.JSONB), nullable=True)
    raw: Mapped[dict] = mapped_column(MutableDict.as_mutable(postgresql.JSONB), nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        postgresql.TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
