from sqlalchemy.orm import DeclarativeBase


class DatabaseModelBase(DeclarativeBase):
    """Base class for all database models."""

    pass


from . import backtest_jobs, backtest_results, job_events
