"""Exceptions for stock trader models."""


class JobNotFoundError(Exception):
    """Exception raised when a backtest job is not found in the database."""

    pass


class JobAlreadyRunningError(Exception):
    """Exception raised when attempting to dispatch a job that is already running."""

    pass
