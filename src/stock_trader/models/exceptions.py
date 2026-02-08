"""Exceptions for stock trader models."""


class JobNotFoundError(Exception):
    """Exception raised when a backtest job is not found in the database."""

    pass
