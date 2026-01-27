"""Exceptions for stock trader models."""


class JobNotFoundException(Exception):
    """Exception raised when a backtest job is not found in the database."""

    pass
