"""Repository for worker database access."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from stock_trader.core.utils import get_utc_now
from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.db.models.backtest_results import BacktestResultTableSchema
from stock_trader.models.exceptions import JobNotFoundError
from stock_trader.models.shared_enums import BacktestStatusEnum


class BacktestRepositorySync:
    """Sync repository for Celery worker database access."""

    def __init__(self, session_maker: sessionmaker) -> None:
        self.database_session = session_maker

    def save_job_result(self, job_id: UUID, symbol: str, summary: dict, raw: dict) -> None:
        """Create and save the result data of a completed backtest job.

        Args:
            job_id: The UUID of the backtest job.
            symbol: The stock ticker symbol.
            summary: The summary data to store.
            raw: The raw data to store.
        """
        with self.database_session() as session:
            job_result: BacktestResultTableSchema = BacktestResultTableSchema(
                job_id=job_id, symbol=symbol, summary=summary, raw=raw
            )
            session.add(job_result)
            session.commit()

    def get_backtest_job(self, job_id: UUID) -> BacktestJobTableSchema:
        """Get a backtest job by its UUID."""
        with self.database_session() as session:
            result = session.execute(select(BacktestJobTableSchema).where(BacktestJobTableSchema.uuid == job_id))
            job = result.scalar_one_or_none()

        if not job:
            raise JobNotFoundError(f"Backtest job with ID {job_id} not found")

        return job

    def update_job_status(
        self,
        job_id: UUID,
        status: BacktestStatusEnum,
        error: str | None = None,
    ) -> None:
        """Update a backtest job's status."""
        with self.database_session() as session:
            result = session.execute(select(BacktestJobTableSchema).where(BacktestJobTableSchema.uuid == job_id))
            job = result.scalar_one_or_none()

            if not job:
                raise JobNotFoundError(f"Backtest job with ID {job_id} not found")

            job.status = status
            job.error = error

            now = get_utc_now()
            if status == BacktestStatusEnum.RUNNING:
                job.start_time = now
            elif status in (BacktestStatusEnum.COMPLETED, BacktestStatusEnum.FAILED):
                job.end_time = now

            session.commit()
