"""Job events model."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from stock_trader.db.models import DatabaseModelBase


class JobEventTableSchema(DatabaseModelBase):
    """Job events table."""

    __tablename__ = "job_events"
    __table_args__ = (
        Index("ix_job_events_job_id_created", "job_id", "create_time"),
        {"schema": "stock_trader"},
    )

    uuid: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("stock_trader.backtest_jobs.uuid", ondelete="CASCADE"), nullable=False)

    event: Mapped[str] = mapped_column(postgresql.TEXT, nullable=False)
    payload: Mapped[dict] = mapped_column(MutableDict.as_mutable(postgresql.JSONB), nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        postgresql.TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
